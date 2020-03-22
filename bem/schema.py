
# -*- coding: utf-8 -*-

"""
Handler for reading YOSYS libraries and generating netlists.
"""
import os
from collections import defaultdict
import json
from subprocess import PIPE, run
from bem import Block
import logging
from skidl import Part

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
log_handler = logging.FileHandler('bem.log')
log_handler.setFormatter(formatter)
log.addHandler(log_handler)

YOSYS = tool_name = 'schema'
lib_suffix = '_schema.py'

class Schematic:
    def __init__(self, circuit):
        self.pages = []
        self.skin = {}
        self.parts = {}
        self.nets = {}
        self.schema = circuit
        self.hierarchy = Block.hierarchy()
        self.blocks = Block.created()
        self.parts = Block.created(Part)
        circuit._merge_net_names()

        # Get connections Part[pin] for each Net

        for code, net in enumerate(
                sorted(self.schema.get_nets(), key=lambda net: str(net.name))):
            net.code = code
            self.nets[net.name] = self.net_connections(net)

        # Add basic parts: VCC, GND, LINE
        for lib, device in [('power', 'GNDPWR'), ('power', 'VBUS'), ('power', 'LINE')]:
            part = lib + ':' + device
            self.skin[part] = sch_symbol(lib, device)

        # Load symbols
        for ref, part in self.parts.items():
            part_type = part.lib + ':' + part.name
            self.parts[ref] = self.part_data(part)

            symbol = sch_symbol(part.lib, part.name, part.instance.unit)
            self.skin[ref] = symbol


    def net_connections(self, net):
        parts = defaultdict(list)
        for pin in net.get_pins():
            parts[pin.part.ref].append(pin.num)

        return parts

    def most_connected_parts(self):
        parts_connections = [(part.ref, len(part.get_pins())) for part in self.schema.parts]
        parts_top_sorted = sorted(parts_connections, key=lambda part: part[1], reverse=True)

        return parts_top_sorted

    def part_data(self, part):
        value = getattr(part, 'value', getattr(part, 'name', getattr(part, 'ref_prefix')))
        symbol = part.lib + ':' + part.name
        instance = {
            'processed': False,
            'ref': part.ref,
            'type': part.ref, #symbol,
            'attributes': {
                'value': str(value)
            },
            'connections': {},
            'port_directions': {},
            'instance': part
        }

        for pin in part.get_pins():
            # TODO: Why here duplicated nets in pin.nets?
            nets = pin.get_nets()
            net_name = str(nets[0].name) if len(nets) > 0 else ''
            instance['connections'][pin.num] = net_name

            pin_description = pin.notes[-1] if len(pin.notes) else ''
            port_direction = pin_description.split(':')[0] or 'input'

            log.info('Detect pin %s.%s as [%s] from description: %s', part.ref, pin.num, port_direction, '\n'.join(pin.notes))

            instance['port_directions'][pin.num] = port_direction
            instance['description'] = '\n'.join(pin.notes)

        instance['pins_count'] = len(part.pins)

        return instance

    def airwire(self, part_name, pin, line_type='LINE'):
        part = self.parts[part_name]
        current_net = part['connections'][pin]
        ref = '_'.join([current_net, part_name, pin])

        log.info('Airwire [%s] <- %s.%s [%s]', line_type, part_name, pin, current_net)

        self.nets[ref] = { part_name: [pin], ref: ['1'] }
        self.nets[current_net][part_name].remove(pin)

        airwire_orientation = 'output' if line_type in ['LINE', 'VBUS'] else 'input'
        airwire = {
            'processed': True,
            'ref': ref,
            'type': 'power:' + line_type,
            'attributes': {
                'value': str(current_net)
            },
            'connections': {
                '1': ref
            },
            'port_directions': {
                '1': airwire_orientation
            },
            'pin_count': 1
        }

        part['port_directions'][pin] = 'input' if airwire_orientation == 'output' else 'output'
        part['connections'][pin] = ref
        self.parts[ref] = airwire

    def change_pin_direction(self, net, direction, without=None):
        for part_name in self.nets[net].keys():
            if part_name != without:
                for pin in self.nets[net][part_name]:
                    log.info('Set pin direction [%s] -> %s.%s, %s', direction, part_name, pin, net)
                    self.parts[part_name]['port_directions'][pin] = direction

    def change_pin_orientation(self, part_ref, pin, orientation):
        # Get current orientation
        current_orientation = self.skin[part_ref]['port_orientation'][pin]

        # Calculate rotation
        rotation_matrix = {
            'D': {
                'L': 90,
                'R': -90,
                'U': 0,
                'D': 180
            },
            'U': {
                'L': -90,
                'R': 90,
                'U': 180,
                'D': 0
            },
            'L': {
                'L': 0,
                'R': 180,
                'U': 90,
                'D': -90
            },
            'R': {
                'L': 180,
                'R': 0,
                'U': -90,
                'D': 90
            }
        }
        rotation = rotation_matrix[orientation][current_orientation]

        log.info('Set pin orientation %s.%s %s -> %s %d °', part_ref, pin, current_orientation, orientation, rotation)
        # Rotate
        if rotation != 0:
            part = self.parts[part_ref]['instance']
            self.skin[part_ref] = sch_symbol(part.lib, part.name, part.instance.unit, rotation)

    def airwire_power(self):
        # Set pin direction for pins connected to VBUS = input, GND = output
        # Airwire all pins connected to VBUS and GND
        # Rotate (TODO: two pin) parts according to power line. For GND pin orientation is bottom, for VBUS is top

        is_two_pin = lambda part: part.get('pins_count', 0) == 2

        vcc_processed = []

        nets = list(self.nets.keys())
        for net in nets:
            is_vs = net[0:2] == 'VS'
            if is_vs:
                vs_parts = self.nets[net]
                for part_name in vs_parts:
                    part = self.parts[part_name]
                    for pin in vs_parts[part_name]:
                        log.info('Part pins %d %s', part.get('pins_count', 0), str(part['connections']))

                        # Maybe some unit doesn't present (for example VCC and GND for OpAmp)
                        if not part['port_directions'].get(pin, False):
                            continue

                        if part['port_directions'][pin] == 'v_inv':
                            if is_two_pin(part):
                                self.change_pin_orientation(part_name, pin, 'D')
                                vcc_processed.append(part_name)

                            part['port_directions'][pin] = 'output'
                            self.airwire(part_name, pin, 'GNDPWR')

                        else:
                            if is_two_pin(part):
                                self.change_pin_orientation(part_name, pin, 'U')
                                vcc_processed.append(part_name)

                            part['port_directions'][pin] = 'input'
                            self.airwire(part_name, pin, 'VBUS')


        gnd_parts = self.nets.get('0', [])
        for part_name in gnd_parts:
            if part_name in vcc_processed:
                continue

            part = self.parts[part_name]

            for pin in gnd_parts[part_name]:
                part['port_directions'][pin] = 'output'
                if is_two_pin(part):
                    self.change_pin_orientation(part_name, pin, 'D')
                self.airwire(part_name, pin, 'GNDPWR')

    def net_pin_orientations(self, net, without=None):
        orientations = defaultdict(int)
        parts = self.nets[net]
        for part in parts:
            if part == without:
                continue

            for pin in parts[part]:
                pin_orientation = self.skin[self.parts[part]['type']]['port_orientation'][pin]
                orientations[pin_orientation] += 1

        return orientations

    def horizontal(self):
        # Oriend two pin part horizontal if they doesn't connected to power lines
        # By default input placed to the left, output to the right
        # Three pin parts maybe using the same principle. But if there are gnd or vcc, they placed accordingly
        is_two_pin = lambda part: part.get('pins_count', 0) == 2
        is_ground = lambda part, pin: part['connections'][pin][0] == '0'
        is_vs = lambda part, pin: part['connections'][pin][:2] == 'VS'
        is_power = lambda part, pin: is_ground(part, pin) or is_vs(part, pin)
        opposites = {
            'L': 'R',
            'R': 'L',
            'U': 'D',
            'D': 'U'
        }

        parts = list(self.parts.keys())
        # Get two pin parts
        for part_name in parts: #self.parts.keys():
            part = self.parts[part_name]

            if is_two_pin(part):
                input_pin = None
                pins = list(part['port_directions'].keys())

                # Orient pin to side of connected part 
                for pin in pins:
                    if is_power(part, pin):
                        break
                else:
                    # Get sides of connected pins
                    # Choise most often side and make opposite
                    first_net = part['connections'][pins[0]]
                    second_net = part['connections'][pins[1]]
                    orientations_first = self.net_pin_orientations(first_net, part_name)
                    orientations_second = self.net_pin_orientations(second_net, part_name)

                    log.info('Orient [%s] %s - %s - %s [%s]', str(orientations_first), first_net, part_name, second_net, str(orientations_second))
                    # if orientations_first['U'] and orientations_second['D']:
                    # L R in one side and U or D in another - VERTICAL

                    if orientations_first['L'] and orientations_second['R']:
                        self.change_pin_orientation(part_name, pins[0], 'R')
                    elif orientations_first['R'] and orientations_second['L']:
                        self.change_pin_orientation(part_name, pins[0], 'R')
                    elif orientations_first['L']:
                        self.change_pin_orientation(part_name, pins[0], 'L')
                    elif orientations_first['R']:
                        self.change_pin_orientation(part_name, pins[0], 'R')
                    elif orientations_first['U'] and orientations_second['U']:
                        self.change_pin_orientation(part_name, pins[0], 'R')
                    elif orientations_first['D'] and orientations_second['D']:
                        self.change_pin_orientation(part_name, pins[0], 'R')
                    elif orientations_first['R'] and orientations_second['R']:
                        self.change_pin_orientation(part_name, pins[0], 'D')



        # Check is not power connected
        # Orient first input pin to LEFT

    def draw_part(self, part, connected_net=None, parent_side='T'):
        log.info('Draw part: ' + part.ref)

        def pin_from_net(net):
            connections = self.parts[part.ref]['connections']
            for pin in connections:
                if connections[pin] == net:
                    return pin

            return None

        def net_from_pin(pin):
            nets = pin.get_nets()
            net = nets[0].name

            return net

        skin_type = part.lib + ':' + part.name
        ref = part.ref
        symbol = self.skin[ref]
        symbol_pins_count = len(symbol['port_orientation'])

        pins = part.get_pins()
        orientation = symbol['orientation']
        port_orientation = symbol['port_orientation']

        def do_power():
            def check_pins(first, second):
                pin_num = str(first.num)
                net = net_from_pin(first)
                second_num = str(second.num)
                second_net = net_from_pin(second)

                is_gnd = net == '0'

                if is_gnd:
                    self.airwire(ref, pin_num, 'GNDPWR')
                    if port_orientation[pin_num] == 'D':
                        log.info('Part rotation 180 ° for GND pin: ' + ref)
                        self.skin[ref] = sch_symbol(part.lib, part.name, part.instance.unit, 180)

                        return True 

                is_vs = net[:2] == 'VS'
                if is_vs:
                    self.airwire(ref, pin_num, 'VBUS')

                    # Opposit pin directions is input
                    self.parts[ref]['port_directions'][pin_num] = 'output' 
                    self.change_pin_direction(second_net, 'input', without=ref)
                    if port_orientation[pin_num] == 'U':
                        log.info('Part rotation 180 ° for VBUS pin: ' + ref)
                        self.skin[ref] = sch_symbol(part.lib, part.name, part.instance.unit, 180)

                        return True

            if not check_pins(part[1], part[2]):
                if check_pins(part[2], part[1]):
                    return True
                else:
                    return False

        # Rotate small part orient to parent part pin
        symbol = self.skin[ref]
        symbol['svg'] = symbol['svg'].replace(skin_type, part.ref)
        self.skin[ref]['svg'] = symbol['svg']

        self.parts[part.ref]['processed'] = True

    def generate_skin_svg(self, filename=''):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" \
             xmlns:xlink="http://www.w3.org/1999/xlink" \
             xmlns:s="https://github.com/nturley/netlistsvg"> \
                <s:properties \
                        constants="false" \
                        splitsAndJoins="false" \
                        genericsLaterals="true"> \
                    <s:layoutEngine \
                        org.eclipse.elk.layered.spacing.edgeEdgeBetweenLayers="300" \
                        org.eclipse.elk.layered.spacing.edgeNodeBetweenLayers="0" \
                        org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers="0" \
                        org.eclipse.elk.spacing.edgeEdge="300" \
                        org.eclipse.elk.spacing.edgeNode="0" \
                        org.eclipse.elk.layered.nodePlacement.strategy="4" \
                        org.eclipse.elk.direction="3"/>\
                </s:properties>\
                <style>\
                svg { \
                    stroke: #000;\
                    fill: none;\
                }\
                </style>'

        for key in self.skin.keys():
            svg += self.skin[key]['svg']

        svg += '</svg>'

        if filename:
            svg_file = open(filename, 'w')
            svg_file.write(svg)
            svg_file.close()
        else:
            return svg

    def write(self):
        self.generate_skin_svg('skin.svg')

        self.convert_nets()

        netlist = open('netlist.json', 'w')
        result = {
            'modules': { 'test': { 'cells': self.parts } }
        }
        netlist.write(json.dumps(result, indent=4))
        netlist.close()

    def convert_nets(self):
        nets = list(self.nets.keys())
        for part_name, part in self.parts.items():
            del part['processed']
            del part['ref']

            direction = part['port_directions']
            for port, port_type in direction.items():
                port_type = 'input' if port_type.find('input') != -1 else 'output'
                direction[port] = port_type

            instance = part.get('instance', False)
            if instance:
                del self.parts[part_name]['instance']

            ports = list(part['connections'].keys())

            for pin in ports:
                net = part['connections'][pin]
                # If pin doesn't exists:
                if not net:
                    log.info('Delete pin %s.%s %s', part_name, pin, net)
                    del part['connections'][pin]

                if net:
                    part['connections'][pin] = [nets.index(net)]


    def generate(self):
        # If part doesn't have enought pins, create airwires
        self.airwire_power()
        self.horizontal()

        ranked_parts = self.most_connected_parts()
        for part, pins in ranked_parts:
            instance = self.parts[part].get('instance', False)
            if instance:
                self.draw_part(instance)

        self.write()

        from pathlib import Path
        module_path = Path(os.path.dirname(__file__)) / 'printer'
        command = ['netlistsvg', 'netlist.json', '--skin', 'skin.svg', '-o', 'schema.svg']
        result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)

        svg_file = open('schema.svg', 'r')
        svg = svg_file.readlines()
        svg_file.close()

        svg[0] = '<svg xmlns="http://www.w3.org/2000/svg" \
             xmlns:xlink="http://www.w3.org/1999/xlink" \
             xmlns:s="https://github.com/nturley/netlistsvg" viewBox="0 0 10000 10000">'


        return ''.join(svg)


def generate_schematics(circuit):
    # Generate schematics from SCOPE, use hierarchy for better layout
    # Because in circuit saved whole part not unit
    schema = Schematic(circuit)

    return schema.generate()

from functools import lru_cache
from pathlib import Path

def sch_symbol(library, device, unit=1, rotate=0):
    import string

    if type(unit) == str:
        unit = string.ascii_uppercase.index(unit.upper()) + 1

    symbol = json.loads(sch2svg(library, device, unit, rotate))
    port_orientation = symbol['port_orientation']
    orientation = 'N'
    symbol['port_orientation'] = port_orientation
    if len(port_orientation) == 2:
        if port_orientation['1'] in ('L', 'R'):
            orientation = 'H'
        else:
            orientation = 'V'

    symbol['orientation'] = orientation

    log.info('Load symbol %s / %s.%d %d °', library, device, unit, rotate)

    return symbol

@lru_cache(maxsize=100)
def sch2svg(library, device, unit, rotate):
    command = ['node', 'sch2svg.js', library, device,  str(unit), str(rotate)]
    module_path = Path(os.path.dirname(__file__)) / 'printer'
    result = run(command, cwd=module_path, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    return result.stdout

