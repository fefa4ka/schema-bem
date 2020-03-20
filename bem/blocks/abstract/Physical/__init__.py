from bem import Block, Stockman, Build
from bem.abstract import Electrical
from skidl import Part, Net, TEMPLATE
from skidl.utilities import get_unique_name
from collections import defaultdict
from copy import copy
import string
from bem.model import Param
import sys
import builtins

class Base(Electrical()):
    units = 1
    def __getitem__(self, *attrs_or_pins, **criteria):
        if hasattr(self, 'selected_part') and len(attrs_or_pins) == 1:
            attr = attrs_or_pins[0]
            if attr and type(attr) == str:
                attr_value = self.selected_part.spice_params.get(attr, None)
                if attr_value:
                    return attr_value
                else:
                    params = [entry.value for entry in self.selected_part.params.where(Param.name == attr)]
                    if len(params):
                        return params[0]

        return super().__getitem__(*attrs_or_pins, **criteria)

    def willMount(self, model=''):
        part = self.props.get('part', None)

        if part:
            self.selected_part = part
            self.template = self.part_template()

    def mount(self, *args, **kwargs):
        super().mount(*args, **kwargs)

        if not hasattr(self, 'selected_part'):
            selected_part = self.select_part()
            self.apply_part(selected_part)

    def available_parts(self):
        circuit = builtins.default_circuit
        circuits_units = circuit.units[self.name] if hasattr(circuit, 'units') else []
        parts = Stockman(self).suitable_parts(circuits_units)

        if len(parts) == 0:
            self.part_unavailable()

        return parts

    def select_part(self):
        # Select allready placed parts in circuit with unused units
        available = list(self.available_parts())

        model = self.model

        if model:
            for part in available:
                if part.model == model:
                    return part

        # TODO: Logic if no part with certain model. Why not raise lookup error? 
        part = available[0] if len(available) > 0 else None

        return part

    def apply_part(self, part):
        if part == None:
            self.part_unavailable()

        self.selected_part = part

        if self.selected_part.model != self.model:
            self.model = self.selected_part.model

        self.props['footprint'] = self.selected_part.footprint.replace('=', ':')

        if not self.SIMULATION:
            self.template = self.part_template()

        units = defaultdict(lambda: defaultdict(list))
        for pin in self.selected_part.pins:
            units[pin.unit][pin.block_pin].append(pin.pin)

        self.unit = 'A'
        if hasattr(part, 'instance'):
            self.part = part.instance.part
            self.unit = part.unit

            part.instance.element.ref += self.get_ref()

            builtins.default_circuit.units[self.name].remove(part)

        if len(units.keys()) > 1 and not hasattr(part, 'instance'):
            part.instance = self
            del units['A']
            for free_unit in units.keys():
                free_unit_part = copy(part)
                free_unit_part.unit = free_unit
                builtins.default_circuit.units[self.name].append(free_unit_part)

        self.part_aliases()

    # Physical or Spice Part
    def part_template(self):
        """
            self.name or self.part should contains definition with ':', for example 'Device:R' 
            or part_template method shoud redefined
        """
        stock = self.selected_part
        if self.props.get('part', None):
            library, symbol = self.props['part'].split(':')
        else:
            library = stock.library
            symbol = stock.symbol

        # TODO: Very slow func. Speedup Part loading, Cache?
        part = Part(library, symbol, footprint=self.footprint, dest=TEMPLATE)

        return part

    def part_aliases(self):
        if not hasattr(self.selected_part, 'pins'):
            return

        units = defaultdict(lambda: defaultdict(list))
        for pin in self.selected_part.pins:
            units[pin.unit][pin.block_pin].append(pin.pin)

        units = dict(units)
        if not units.get(self.unit, None):
            return

        part = self.part()

        for block_pin in units[self.unit].keys():
            for part_pin in units[self.unit][block_pin]:
                pin_number = int(part_pin.split('/')[1])
                device_name = self.name.replace('.', '')
                net_name =  device_name + ''.join([word.capitalize() for word in block_pin.split('_')]) + str(pin_number)
                pin_net = Net(net_name)
                pin_net += part[pin_number]

                setattr(self, block_pin, pin_net)

    def part_spice(self, *args, **kwargs):
        part = Build((self.selected_part.symbol or self.model) + ':' + self.model).spice

        return part(*args, **kwargs)

    def part(self, *args, **kwargs):
        tracer = sys.getprofile()
        sys.setprofile(None)

        # Only one instance of Part could be used in Block
        if not hasattr(self, '_part') or self._part == None:
            if self.SIMULATION:
                part = self.part_spice(*args, **kwargs)
            else:
                part = self.template(*args, **kwargs)

            if len(part.pins) == 2:
                part.set_pin_alias('p', 1)
                part.set_pin_alias('+', 1)
                part.set_pin_alias('n', 2)
                part.set_pin_alias('-', 2)

            self._part = part

            self.scope.append((self, part))

        part = self._part
        part.ref = self.ref or self.get_ref()

        sys.setprofile(tracer)

        return part

    @property
    def footprint(self):
        return self.props.get('footprint', None)

    def set_pins_aliases(self, pins):
        for pin in pins.keys():
            aliases = pins[pin]
            aliases = [aliases] if type(aliases) == str else aliases
            for alias in aliases:
                self.template.set_pin_alias(alias, pin)

            self.template[pin].aliases = { alias for alias in aliases }


    def part_unavailable(self):
        args = self.get_arguments()
        params = self.get_params()
        values = {
            **args,
            **params
        }
        description = ', '.join([ arg + ' = ' + str(values[arg].get('value', '')) + values[arg]['unit'].get('suffix', '') for arg in values.keys()])

        raise LookupError("Should be part in stock for %s block with suitable characteristics\n%s" % (self.name, description))
