from bem import Block, Stockman, Build
from bem.abstract import Electrical
from skidl import Part, Net, TEMPLATE
from skidl.utilities import get_unique_name
from collections import defaultdict
from copy import copy
import string
from PySpice.Unit import FrequencyValue, PeriodValue
from PySpice.Unit.Unit import UnitValue
from bem.model import Param
import sys
import builtins

from functools import lru_cache


@lru_cache(maxsize=100)
def PartCached(library, symbol, footprint, dest):
    return Part(library, symbol, footprint=footprint, dest=dest)

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
        """
            unit -- Unit in physical part for block abstraction
            units -- Available units in physical part
        """

        # Possible to pass custom part from Block props
        part = self.props.get('part', None)
        self.unit = 'A'

        if part:
            self.selected_part = part
            self.template = self.part_template()

    def mount(self, *args, **kwargs):
        # Stop profiler started in Block.__init__
        tracer = sys.getprofile()
        sys.setprofile(None)

        super().mount(*args, **kwargs)

        if not hasattr(self, 'selected_part'):
            selected_part = self.select_part()
            self.apply_part(selected_part)

        # Restart profiler
        sys.setprofile(tracer)

    def available_parts(self):
        from statistics import mean
        circuit = builtins.default_circuit
        circuits_units = circuit.units[self.name] if hasattr(circuit, 'units') else []
        stock = Stockman(self)
        parts = stock.suitable_parts(circuits_units)

        if len(parts) == 0:
            self.part_unavailable()

        # Sort by V, Power, I
        def cmp_param(part, param):
            avg = lambda values: mean([abs(float(value)) for value in values]) if len(values) else 0
            values = stock.get_param(part, param)
            return avg(values)

        cmp_V = lambda part: cmp_param(part, 'V')
        cmp_I = lambda part: cmp_param(part, 'I')
        cmp_P = lambda part: cmp_param(part, 'P')

        parts = sorted(parts, key=lambda x: (cmp_V, cmp_I, cmp_P))
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

        ref = self.get_ref()

        self.selected_part = part

        if self.selected_part.model != self.model:
            self.model = self.selected_part.model

        self.props['footprint'] = self.selected_part.footprint.replace('=', ':')

        if not self.SIMULATION:
            self.template = self.part_template()

        # Apply params
        stock = Stockman(self)
        for param in self.get_params():
            # TODO: Could be more that one param?
            # More that one param could be only in argument, 
            # for example `value` for Resistor
            if param in ['P', 'I', 'Z', 'units', 'unit']:
                continue

            values = stock.get_param(part, param)
            if len(values):
                value = unit_value = values[0]
                default = getattr(self, param)
                if type(default) in [UnitValue, PeriodValue, FrequencyValue]:
                    unit_value = default.clone()
                    unit_value._value = unit_value._convert_scalar_value(value)
                elif type(default) in [int, float]:
                    unit_value = float(value)

                setattr(self, param, unit_value)

        # Apply pins to proper unit in physical pat
        units = defaultdict(lambda: defaultdict(list))
        for pin in self.selected_part.pins:
            units[pin.unit][pin.block_pin].append(pin.pin)

        # If this instance is a child 
        # Parent have original part with needed unit
        if hasattr(part, 'instance'):
            self._part = part.instance._part
            self.unit = part.unit

            part.instance.element.ref += ref

            builtins.default_circuit.units[self.name].remove(part)

        if len(units.keys()) > 1 and not hasattr(part, 'instance'):
            part.instance = self
            del units['A']
            for free_unit in units.keys():
                free_unit_part = copy(part)
                free_unit_part.unit = free_unit
                builtins.default_circuit.units[self.name].append(free_unit_part)


    # Physical or Spice Part
    def part_template(self):
        """
            self.name or self.part should contains definition with ':', for example 'Device:R' 
            or part_template method should redefined
        """
        stock = self.selected_part
        if self.props.get('part', None):
            library, symbol = self.props['part'].split(':')
        else:
            library = stock.library
            symbol = stock.symbol

        # TODO: Very slow func. Speedup Part loading, Cache?
        part = PartCached(library, symbol, footprint=self.footprint, dest=TEMPLATE)

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

        for block_pin in units[self.unit].keys():
            for part_pin in units[self.unit][block_pin]:
                pin_number = int(part_pin.split('/')[1])
                device_name = self.name.replace('.', '')
                net_name =  device_name + ''.join([word.capitalize() for word in block_pin.split('_')]) + str(pin_number)
                pin_net = Net(net_name)
                pin_net += self._part[pin_number]

                setattr(self, block_pin, pin_net)

    def part_spice(self, *args, **kwargs):
        part = Build((self.selected_part.symbol or self.model) + ':' + self.model).spice

        return part(*args, **kwargs)

    def part(self, *args, **kwargs):

        is_mounted = True in [item[1] == self for item in self.scope]

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
            self._part.notes += self.notes

        part = self._part
        ref = self.ref or self.get_ref()
        part.ref = ref

        if is_mounted:
            self.part_aliases()

        if hasattr(self, 'unit') and hasattr(part, 'unit') and part.unit.get('u' + self.unit, False):
            part = getattr(part, 'u' + self.unit)
            part._ref = ref

        if is_mounted:
            self.scope.append((self, part))

        part.instance = self

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
