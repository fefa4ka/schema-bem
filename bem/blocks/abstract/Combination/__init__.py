import inspect

import numpy as np
from PySpice import Spice
from PySpice.Unit import FrequencyValue, PeriodValue, SiUnits
from PySpice.Unit.Unit import UnitValue

from bem import Block, u
from bem.abstract import Physical
from bem.model import Param

si_units = inspect.getmembers(SiUnits, lambda a: not (inspect.isroutine(a)))
prefixes = {prefix[1].__prefix__: prefix[1].__power__ for prefix in si_units if hasattr(prefix[1], '__prefix__')}
prefixes['u'] = prefixes['μ']
prefixes['0'] = 0


class Base(Physical()):
    #inherited = [Physical]
    increase = True
    value = 0

    def __init__(self, *args, **kwargs):
        value = self.value

        if len(args) > 0 and 'value' not in kwargs.keys():
            value = args[0]
            args = args[1:]

        if kwargs.get('value', None):
            value = kwargs['value']

        if type(value) in [UnitValue, PeriodValue, FrequencyValue]:
            kwargs['value'] = value
        elif type(self.value) in [UnitValue, PeriodValue, FrequencyValue]:
            self.value._value = float(value)
            kwargs['value'] = self.value
        else:
            kwargs['value'] = value

        super().__init__(*args, **kwargs)

    def willMount(self, value):
        pass

    # def unit_value(self):
    #     if type(self.value) in [str, int, float]:
    #         self.value._value = float(self.value)

    def values(self):
        values = []
        
        for part in self.available_parts():
            values += self.part_values(part)

        return values
    
    def part_values(self, part):
        values = []

        part_params = [entry.value for entry in part.params.where(Param.name == 'value')]
        for value in part_params:
            values_range = value.split('/')
            if len(values_range) > 1:
                scales, exponenta = values_range
                for exp in exponenta.strip().split(' '):
                    exp_unit = self.value.clone().convert_to_power(0)
                    exp_unit._value = pow(10, prefixes.get(exp, None) or int(exp))

                    scale = np.array(scales.strip().split(' ')).astype(float)
                    
                    values += list(scale * exp_unit)
            else:
                values += value.split(' ')

        return values
                
    def available_parts(self):
        available_parts = super().available_parts()
        suited_parts = []

        # self.unit_value()
        for part in available_parts:
            for value in self.part_values(part):
                if value == self.value:
                    suited_parts.append(part)
        
        if len(suited_parts) == 0:
            suited_parts = [available_parts[0]]

        filtered_parts = []
        if self.model:
            for part in suited_parts:
                if part.model == self.model:
                    filtered_parts.append(part)

        return filtered_parts if len(filtered_parts) > 0 else suited_parts

    def values_optimal(self, desire, error=10):
        # return [desire]
        # TODO: make better
        closest = self.value_closest(desire)

        closest_value = u(closest)
        value = u(desire)
        
        max_error = value * error / 100
        diff = value - closest_value

        values = []
        if max_error > abs(diff):
            values = [closest]
        else:
            diff_unit = desire.clone()

            if (diff > 0 and self.increase) or (diff < 0 and not self.increase):
                values = [closest]

                diff_unit._value = diff

                diff_closest = self.values_optimal(diff_unit)

                values += diff_closest
            else:
                diff_unit._value = diff * 2
                first_closest = self.value_closest(diff_unit)
                first_value = u(first_closest)
                second_value = diff * first_value / (diff - first_value)
                diff_unit._value = abs(second_value)
                second_closest = self.value_closest(diff_unit)

                values.append([first_closest, second_closest])

        return values
    
    def value_closest(self, value):
        absolute_value = u(value)

        closest = None
        for unit in self.values():            
            if not closest:
                closest = unit

            unit_value = u(unit)
            closest_value = u(closest)
            
            diff_unit = abs(absolute_value - unit_value)
            diff_closest = abs(absolute_value - closest_value)

            if diff_closest > diff_unit:
                closest = unit
        
        if not closest or abs(u(closest) - u(value)) > u(value) * 0.1 :
            closest = value
        
        closest = closest.canonise()
        # closest._value = round(closest._value, 2)

        return closest
