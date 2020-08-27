
# -*- coding: utf-8 -*-

"""
Handler for reading YOSYS libraries and generating netlists.
"""
import json
import logging
import os
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from subprocess import PIPE, run

from skidl import Part, Net

from bem import Block
from bem.utils.structer import hierarchy


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
FORMAT = "%(levelname)s - [%(filename)10s:%(lineno)3s:%(funcName)20s() ] - %(message)10s"
formatter = logging.Formatter(FORMAT)# '%(name)s - %(levelname)s - %(message)s')
log_handler = logging.FileHandler('bem.log')
log_handler.setFormatter(formatter)
log.addHandler(log_handler)

YOSYS = tool_name = 'schema'
lib_suffix = '_schema.py'

class Schematic:
    def __init__(self, circuit, Instance=None):
        self.pages = []
        self.skin = {}
        self.parts = {}
        self.nets = defaultdict(lambda: defaultdict(list))
        self.airwire_nets = defaultdict(lambda: defaultdict(list))
        self.schema = circuit
        self.block = Instance
        self.hierarchy = hierarchy(Block)
        self.blocks = Block.created()
        self.parts = Block.created(Part)
        circuit._merge_net_names()

        # Get connections Part[pin] for each Net

        for code, net in enumerate(
                sorted(self.schema.get_nets(), key=lambda net: str(net.name))):
            self.nets[net.name] = self.net_connections(net)
        self.ports = {}


        # Add basic parts: VCC, GND, LINE
        for lib, device in [('power', 'GNDREF'), ('power', 'GNDA'), ('power', 'VBUS'), ('power', 'LINE')]:
            part = lib + ':' + device
            self.skin[part] = sch_symbol(lib, device)

        # Load symbols
        for ref, part in self.parts.items():
            part_type = part.lib + ':' + part.name
            self.parts[ref] = self.part_data(part)

            symbol = sch_symbol(part.lib, part.name, part.instance.unit, ref=part.ref, value=part.value)
            self.skin[ref] = symbol


    def get_ports(self):
        ports = {}

        nets = sorted(list(self.nets.keys()))
        if self.block and len(nets):
            circuit_name = self.block.name
            ports = {}

            for pin in self.block.get_pins():
                net = getattr(self.block, pin)
                # Net maybe doesn't connect to anything
                if not len(net.get_pins()):
                    continue
                direction = None
                if pin.find('output') == 0:
                    direction = 'output'

                if pin.find('input') == 0:
                    direction = 'input'

                if not direction:
                    continue

                ports[pin] = {
                    'direction': direction,
                    'bits': [nets.index(net.name)],
                    'net': net.name
                }

        return ports

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
            'name': part.name,
            'description': [entry.strip() for entry in part.description.split(',')] + part.notes,
            'attributes': {
                'value': str(value)
            },
            'connections': {},
            'port_directions': {},
            'port_description': {},
            'footprint': part.footprint,
            'instance': part
        }

        instance['description'].reverse()

        for pin in part.get_pins():
            # TODO: Why here duplicated nets in pin.nets?
            nets = pin.get_nets()
            net_name = str(nets[0].name) if len(nets) > 0 else ''
            instance['connections'][pin.num] = net_name

            pin_description = pin.notes[-1] if len(pin.notes) else ''
            port_direction = pin_description.split(':')[0] or 'input'

            log.info('%s.%s as [%s]: %s', part.ref, pin.num, port_direction, '; '.join(pin.notes))

            instance['port_directions'][pin.num] = port_direction
            instance['port_description'][pin.num] = [pin.name] + list(reversed(pin.notes))

        instance['pins_count'] = len(part.pins)

        return instance

    def airwire(self, part_name, pin, line_type='LINE'):
        if type(pin) is list:
            pins = pin
        else:
            pins = [pin]

        part = self.parts[part_name]
        airwire_orientation = 'output' if line_type in ['LINE', 'VBUS'] else 'input'

        for pin in pins:
            current_net = part['connections'][pin]
            ref = '_'.join([current_net, part_name])

            log.info('[%s] <- %s.%s [%s] over net %s', line_type, part_name, pin, current_net, ref)

            self.nets[ref][part_name].append(pin)
            self.nets[ref][ref] = ['1']

            self.nets[current_net][part_name].remove(pin)

            self.airwire_nets[current_net][ref] = ['1']
            self.airwire_nets[current_net][part_name].append(pin)

            part['port_directions'][pin] = 'input' if airwire_orientation == 'output' else 'output'
            part['connections'][pin] = ref

        airwire = {
            'processed': True,
            'ref': ref,
            'type': 'power:' + line_type,
            'attributes': {
                'value': '' if current_net == '0' else str(current_net)
            },
            'connections': {
                '1': ref
            },
            'port_directions': {
                '1': airwire_orientation
            },
            'pin_count': 1
        }
        self.skin[ref] = sch_symbol('power', 'LINE')

        self.parts[ref] = airwire


    def change_pin_direction(self, net, direction, without=None):
        for part_name in self.nets[net].keys():
            if part_name != without:
                for pin in self.nets[net][part_name]:
                    log.info('[%s] -> %s.%s, %s', direction, part_name, pin, net)
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
        rotation = rotation_matrix[current_orientation][orientation]

        log.info('%s.%s %s -> %s %d °', part_ref, pin, current_orientation, orientation, rotation)
        # Rotate
        if rotation != 0:
            part = self.parts[part_ref].get('instance', None)
            self.skin[part_ref] = sch_symbol(part.lib, part.name, part.instance.unit, rotation, part_ref, part.value)

    def connect_line(self, direction, net):
        ref = net + '_Ref'
        if direction == 'v_inv':
            line_type = 'GNDA'
            orientation = 0
            airwire_direction = 'input'
        else:
            line_type = 'LINE' if direction == 'output' else 'LINE'
            orientation = '-90' if direction == 'output' else '90'
            airwire_direction = 'output' if direction == 'input' else 'input'

        airwire = {
            'processed': True,
            'ref': ref,
            'type': ref,
            'attributes': {
                'value': net,
            },
            'connections': {
                '1': net
            },
            'port_directions': {
                '1': airwire_direction
            },
            'pin_count': 1
        }

        self.nets[net][ref] = ['1']
        self.parts[ref] = airwire

        self.skin[ref] = sch_symbol('power', line_type, rotate=orientation)
        symbol = self.skin[ref]
        symbol['svg'] = symbol['svg'].replace('power:' + line_type, ref)
        self.skin[ref]['svg'] = symbol['svg']

    def airwire_io(self):
        nets = list(self.nets.keys())
        for net in nets:
            is_input = net.find('InputLine') == 0
            is_output = net.find('OutputLine') == 0
            is_vinv = net.find('VInvLine') == 0

            if is_input:
                self.connect_line('input', net)
                # add airwire LINE with pin to right

            if is_output:
                self.connect_line('output', net)
                # add airwire LINE with pin to left

            if is_vinv:
                for part in self.nets[net]:
                    pin = self.nets[net][part][0]
                    self.change_pin_orientation(part, pin, 'D')
                    break
                self.connect_line('v_inv', net)


    def airwire_power(self):
        # Set pin direction for pins connected to VBUS = input, GND = output
        # Airwire all pins connected to VBUS and GND
        # Rotate (TODO: two pin) parts according to power line. For GND pin orientation is bottom, for VBUS is top

        is_two_pin = lambda part: part.get('pins_count', 0) <= 3

        vcc_processed = []

        nets = list(self.nets.keys())
        for net in nets:
            is_vs = net[0:2] == 'VS'
            if is_vs:
                vs_parts = self.nets[net]
                for part_name in vs_parts:
                    part = self.parts[part_name]
                    pins = vs_parts[part_name]
                    log.info(part_name + ' - ' + str(pins))
                    for pin in pins:
                        log.info('%s[%d]: %s', part_name, part.get('pins_count', 0), str(part['connections']))

                        # Maybe some unit doesn't present (for example VCC and GND for OpAmp)
                        if not part['port_directions'].get(pin, False):
                            continue

                        if part['port_directions'][pin] == 'v_inv':
                            if is_two_pin(part):
                                self.change_pin_orientation(part_name, pin, 'D')
                                vcc_processed.append(part_name)

                            part['port_directions'][pin] = 'input'
                            airwire_type = 'GNDA'
                            self.airwire(part_name, pin, 'GNDA')

                        else:
                            if is_two_pin(part):
                                self.change_pin_orientation(part_name, pin, 'U')
                                vcc_processed.append(part_name)

                            part['port_directions'][pin] = 'output'
                            self.airwire(part_name, pin, 'VBUS')

        gnd_parts = self.nets.get('0', [])
        for part_name in gnd_parts:
            part = self.parts[part_name]

            pins = list(gnd_parts[part_name])
            for pin in pins:
                part['port_directions'][pin] = 'input'
                if is_two_pin(part) and part_name not in vcc_processed:
                    self.change_pin_orientation(part_name, pin, 'D')

            self.airwire(part_name, pins, 'GNDREF')


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
                        log.info('%s if power connected' % part_name)
                        break
                else:
                    # Get sides of connected pins
                    # Choise most often side and make opposite
                    first = pins[0]
                    second = pins[1]
                    first_net = part['connections'][first]
                    second_net = part['connections'][second]

                    is_port_connected = False


                    orientations_first = self.net_pin_orientations(first_net, part_name)
                    orientations_second = self.net_pin_orientations(second_net, part_name)


                    # TODO: If there are ports, orient properly to port direction
                    for port in self.ports:
                        port = self.ports[port]

                        orientation = 'R' if port['direction'] == 'input' else 'L'
                        if port['net'] == first_net:
                            orientations_first[orientation] += 1
                            #self.change_pin_orientation(part_name, pins[0], orientation)
                            #is_port_connected = port
                            #break

                        if port['net'] == second_net:
                            orientations_second[orientation] += 1
                            #self.change_pin_orientation(part_name, pins[1], orientation)
                            #is_port_connected = port
                            #break

                    log.info('%s %s - %s - %s %s', str(dict(orientations_first)), first_net, part_name, second_net, str(dict(orientations_second)))

                    # if is_port_connected:
                    #    log.info('Port %s [%s] connected to %s ' % (port['net'], port['direction'], orientation))
                    #    continue

                    # if orientations_first['U'] and orientations_second['D']:
                    # L R in one side and U or D in another - VERTICAL

                    def prepare(first, second):
                        if type(first) != list:
                            fist = [first]

                        if second == None:
                            second = first

                        if type(second) != list:
                            second = [second]

                        return first, second

                    def no(first, second=None):
                        first, second = prepare(first, second)

                        for orientation in first:
                            if orientations_first[orientation]:
                                return False

                        for orientation in second:
                            if orientations_second[orientation]:
                                return False

                        return True

                    def yes(first, second=None):
                        first, second = prepare(first, second)

                        for orientation in first:
                            if not orientations_first[orientation]:
                                return False

                        for orientation in second:
                            if not orientations_second[orientation]:
                                return False

                        return True

                    def cn(first, second=[]):
                        first, second = prepare(first, second)

                        total_sum = 0
                        for orientation in first:
                            total_sum += orientations_first[orientation]

                        for orientation in second:
                            total_sum += orientations_second[orientation]

                        return total_sum

                    def gt(first, second=None):
                        first, second = prepare(first, second)

                        first_sum = 0
                        for orientation in first:
                            first_sum += orientations_first[orientation]

                        second_sum = 0
                        for orientation in second:
                            second_sum += orientations_second[orientation]

                        if first_sum > second_sum:
                            return True

                        return False

                    if no(['D', 'U']):
                        log.info('No D & U')
                        if cn('R', 'L') > cn('L', 'R'):
                            self.change_pin_orientation(part_name, first, 'L')
                        else:
                            self.change_pin_orientation(part_name, first, 'R')

                    elif no(['L', 'R']):
                        log.info('No L & R')

                        if cn('D', 'U') > cn('U', 'D'):
                            self.change_pin_orientation(part_name, first, 'U')
                        else:
                            self.change_pin_orientation(part_name, first, 'D')

                    elif no([], ['L', 'R']):
                        log.info('Second no L & R')
                        if cn('R') > cn('L'):
                            self.change_pin_orientation(part_name, first, 'L')
                        else:
                            self.change_pin_orientation(part_name, first, 'R')


                    elif no(['L', 'R'], []):
                        log.info('First no L & R')
                        if cn('R') > cn('L'):
                            self.change_pin_orientation(part_name, second, 'L')
                        else:
                            self.change_pin_orientation(part_name, second, 'R')

                    elif yes('R', 'L') and no('L', 'R'):
                        log.info('Yes R & L / No L & R')
                        self.change_pin_orientation(part_name, first, 'L')

                    elif no('R', 'L') and yes('L', 'R'):
                        log.info('No R & L / Yes L & R')
                        self.change_pin_orientation(part_name, first, 'R')
                    """
                    if orientations_first['L'] and orientations_second['R']:
                        if orientations_first['R'] and orientations_second['L']:
                            # Connections from every side
                            if orientations_first['R'] > orientations_first['L'] > orientations_second['L'] > orientations_second['R']:
                                # Most connections from right to first pin
                                log.info('1.R > 1.L > 2.L > 2.R -> 1L')
                                
                                self.change_pin_orientation(part_name, pins[0], 'L')
                            elif orientations_second['L'] > orientations_second['R']:
                                # Most connection to second pin from left
                                log.info('2.L > 2.R -> 1R')
                                self.change_pin_orientation(part_name, pins[0], 'R')
                        else:
                            # Most connection to first pin from left
                            log.info('1.L > -> 1R')
                            self.change_pin_orientation(part_name, pins[0], 'R')

                    elif orientations_first['R'] and orientations_second['L']:
                        if orientations_first['R'] > orientations_second['L']:
                            log.info('1.R & 2.L -> 1L')
                            self.change_pin_orientation(part_name, pins[0], 'L')
                        else:
                            log.info('1.R & 2.L -> 1R')
                            self.change_pin_orientation(part_name, pins[0], 'R')

                    elif orientations_first['U'] and orientations_second['D']:

                        self.change_pin_orientation(part_name, pins[0], 'D')

                    elif orientations_first['D'] and orientations_second['U']:

                        self.change_pin_orientation(part_name, pins[0], 'U')

                    elif orientations_first['U'] and orientations_second['U']:

                        if orientations_first['U'] >= orientations_second['U']:
                            self.change_pin_orientation(part_name, pins[0], 'D')
                        else:
                            self.change_pin_orientation(part_name, pins[0], 'U')

                    elif orientations_first['D'] and orientations_second['D']:

                        if orientations_first['D'] >= orientations_second['D']:
                            self.change_pin_orientation(part_name, pins[0], 'U')
                        else:
                            self.change_pin_orientation(part_name, pins[0], 'D')

                    elif orientations_first['L'] or orientations_second['R']:

                        self.change_pin_orientation(part_name, pins[0], 'R')

                    elif orientations_first['R'] or orientations_second['L']:

                        self.change_pin_orientation(part_name, pins[0], 'L')


#                    elif orientations_first['D'] and orientations_second['D']:
#                        self.change_pin_orientation(part_name, pins[0], 'R')
#                    elif orientations_first['R'] and orientations_second['R']:
#                        self.change_pin_orientation(part_name, pins[0], 'D')

"""

        # Check is not power connected
        # Orient first input pin to LEFT

    def draw_part(self, part, connected_net=None, parent_side='T'):
        log.info(part.ref + '.' + str(connected_net) + ' <- ' + parent_side)

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
                    self.airwire(ref, pin_num, 'GNDREF')
                    if port_orientation[pin_num] == 'D':
                        log.info('Rotation 180 ° for GND pin: ' + ref)
                        self.skin[ref] = sch_symbol(part.lib, part.name, part.instance.unit, 180, ref, part.value)

                        return True 

                is_vs = net[:2] == 'VS'
                if is_vs:
                    self.airwire(ref, pin_num, 'VBUS')

                    # Opposit pin directions is input
                    self.parts[ref]['port_directions'][pin_num] = 'output'
                    self.change_pin_direction(second_net, 'input', without=ref)
                    if port_orientation[pin_num] == 'U':
                        log.info('Rotation 180 ° for VBUS pin: ' + ref)
                        self.skin[ref] = sch_symbol(part.lib, part.name, part.instance.unit, 180, ref, part.value)

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
        # Warning: Sometimes schematic couldn't be generated with tight spacing
        svg = """
            <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:xlink="http://www.w3.org/1999/xlink"
             xmlns:s="https://github.com/nturley/netlistsvg">
                <s:properties
                        constants="false"
                        splitsAndJoins="false"
                        genericsLaterals="true">
          <s:layoutEngine
                org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers="5"
                org.eclipse.elk.layered.spacing.edgeEdgeBetweenLayers="35"
                org.eclipse.elk.layered.compaction.postCompaction.strategy="4"
                org.eclipse.elk.spacing.nodeNode="35"
                org.eclipse.elk.spacing.edgeEdge="20"
                org.eclipse.elk.direction="DOWN"/>
                </s:properties>
        """

        signal = """
        <!-- signal -->
        <g s:type="inputExt" s:width="30" s:height="20">
          <text x="15" y="-4" class="$cell_id" s:attribute="ref">input</text>
          <s:alias val="$_inputExt_"/>
          <path d="M0,0 V20 H15 L30,10 15,0 Z" class="$cell_id"/>
          <g s:x="30" s:y="10" s:pid="Y" s:position="right"/>
        </g>

        <g s:type="outputExt" s:width="30" s:height="20" transform="translate(60,70)">
          <text x="15" y="-4" class="$cell_id" s:attribute="ref">output</text>
          <s:alias val="$_outputExt_"/>
          <path d="M30,0 V20 H15 L0,10 15,0 Z" class="$cell_id"/>
          <g s:x="0" s:y="10" s:pid="A" s:position="left"/>
        </g>
        <!-- signal -->
        """
        generic = """
        <!-- builtin -->
        <g s:type="generic" s:width="30" s:height="40">
          <text x="15" y="-4" class="nodelabel $cell_id" s:attribute="ref">generic</text>
          <rect width="30" height="40" x="0" y="0" s:generic="body" class="$cell_id"/>
          <g transform="translate(30,10)"
             s:x="30" s:y="10" s:pid="out0" s:position="right">
            <text x="5" y="-4" class="$cell_id">out0</text>
          </g>
          <g transform="translate(30,30)"
             s:x="30" s:y="30" s:pid="out1" s:position="right">
            <text x="5" y="-4" class="$cell_id">out1</text>
          </g>
          <g transform="translate(0,10)"
             s:x="0" s:y="10" s:pid="in0" s:position="left">
              <text x="-3" y="-4" class="inputPortLabel $cell_id">in0</text>
          </g>
          <g transform="translate(0,30)"
             s:x="0" s:y="30" s:pid="in1" s:position="left">
            <text x="-3" y="-4" class="inputPortLabel $cell_id">in1</text>
          </g>
        </g>
        <!-- builtin -->
        """

        svg += signal
        svg += generic

        for key in self.skin.keys():
            svg += '\n\n<!-- ' + key + '-->'
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


        # TODO: Refactoring
        circuit_name = 'circuit'


        result = {
            'modules': {
                circuit_name: {
                    'ports': self.ports,
                    'cells': self.parts
                }
            }
        }
        netlist.write(json.dumps(result, indent=4))
        netlist.close()

    def convert_nets(self):
        nets = sorted(list(self.nets.keys()))

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
                    del part['connections'][pin]

                if net:
                    part['connections'][pin] = [nets.index(net)]


    def generate(self):
        # If part doesn't have enought pins, create airwires

        self.airwire_power()
        self.airwire_io()

        self.ports = self.get_ports()
        self.horizontal()

        # airwire big parts

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
        failed = False

        try:
            svg_file = open('schema.svg', 'r')
            svg = svg_file.readlines()
            svg_file.close()

            width = re.findall("<svg(?:\D+=\"\S*\")*\s+width=\"(\d*\.\d+|\d+)\"", svg[0])[0]
            height = re.findall("<svg(?:\D+=\"\S*\")*\s+height=\"(\d*\.\d+|\d+)\"", svg[0])[0]
            svg[0] = '<svg xmlns="http://www.w3.org/2000/svg" \
                 xmlns:xlink="http://www.w3.org/1999/xlink" \
                 xmlns:s="https://github.com/nturley/netlistsvg" viewBox="0 0 %s %s">' % (width, height)
        except:
            failed = True


        #if False or not failed:

            #os.remove('schema.svg')
            #os.remove('netlist.json')
            #os.remove('skin.svg')

        if not failed:
            return ''.join(svg)

        return '{ "error": "Schematic generation failed" }'


def generate_schematics(circuit):
    # Generate schematics from SCOPE, use hierarchy for better layout
    # Because in circuit saved whole part not unit
    schema = Schematic(circuit)

    return schema.generate()


def sch_symbol(library, device, unit=1, rotate=0, ref='', value=''):
    import string

    if type(unit) == str:
        unit = string.ascii_uppercase.index(unit.upper()) + 1

    log.info('%s / %s.%d %s ° -> %s (%s)', library, device, unit, rotate, ref, value)
    symbol = json.loads(sch2svg(library, device, unit, rotate)) #, ref, str(value)))
    port_orientation = symbol['port_orientation']
    orientation = 'N'
    symbol['port_orientation'] = port_orientation
    if len(port_orientation) == 2:
        if port_orientation['1'] in ('L', 'R'):
            orientation = 'H'
        else:
            orientation = 'V'

    symbol['orientation'] = orientation


    return symbol

@lru_cache(maxsize=100)
def sch2svg(library, device, unit, rotate):
    command = ['node', 'sch2svg.js', library, device,  str(unit), str(rotate)]
    module_path = Path(os.path.dirname(__file__)) / 'printer'
    result = run(command, cwd=module_path, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    return result.stdout
