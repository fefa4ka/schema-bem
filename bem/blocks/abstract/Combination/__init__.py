import inspect

import numpy as np
from PySpice import Spice
from PySpice.Unit import FrequencyValue, PeriodValue, SiUnits
from PySpice.Unit.Unit import UnitValue

from skidl import Net
from bem import Block, u
from bem.abstract import Physical
from bem.model import Param
from copy import copy

si_units = inspect.getmembers(SiUnits, lambda a: not (inspect.isroutine(a)))
prefixes = {prefix[1].__prefix__: prefix[1].__power__ for prefix in si_units if hasattr(prefix[1], '__prefix__')}
prefixes['u'] = prefixes['μ']
prefixes['0'] = 0


class Base(Physical()):
    increase = True

    def __init__(self, *args, **kwargs):
        arguments, defaults = self.get_default_arguments()

        default_value = value = defaults.get('value', None)

        if len(args) > 0 and 'value' not in kwargs.keys():
            value = args[0]
            args = args[1:]

        if kwargs.get('value', None):
            value = kwargs['value']

        if type(value) in [UnitValue, PeriodValue, FrequencyValue]:
            kwargs['value'] = value
        elif type(default_value) in [UnitValue, PeriodValue, FrequencyValue]:
            self.value = copy(default_value)
            self.value._value = u(value)
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

        error = 5
        max_error = u(self.value) * error / 100
        min_error = None
        min_error_part = None

        for part in available_parts:
            for value in self.part_values(part):
                if value == self.value:
                    suited_parts.append(part)

                error = abs(u(value) - u(self.value))
                if min_error == None or min_error > error:
                    min_error = error
                    min_error_part = part

        if len(suited_parts) == 0:
            if max_error > min_error and min_error_part:
                suited_parts.append(min_error_part)
            else:
                suited_parts = available_parts

        filtered_parts = []
        if self.model:
            for part in suited_parts:
                if part.model == self.model:
                    filtered_parts.append(part)

        return filtered_parts if len(filtered_parts) > 0 else suited_parts

    def values_optimal(self, desire, error=10, error_threshold=0):
        # TODO: make better
        closest = self.value_closest(desire)

        closest_value = u(closest)
        value = u(desire)

        max_error = value * error / 100
        diff = value - closest_value

        if not error_threshold:
            error_threshold = max_error

        # if available parts too far from desire
        if diff / error_threshold > 2:
            self.part_unavailable()

        values = []
        if max_error > abs(diff) or abs(diff) < error_threshold:
            values = [closest]
        else:
            if (diff > 0 and self.increase) or (diff < 0 and not self.increase):
                values = [closest]

                diff_closest = self.values_optimal(abs(diff), error_threshold=error_threshold)

                values += diff_closest
            else:
                first_closest = self.value_closest(diff * 2)
                first_value = u(first_closest)
                second_value = first_value * diff / (diff - first_value)
                second_closest = self.value_closest(abs(second_value))

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

        return closest

    def part_aliases(self):
        # TODO: Possibility to apply resistors array
        return

    def circuit(self):
        value = self.value.canonise()
        value._value = round(value._value)
        return super().circuit(value=value)

        # TODO: Wrong implementation

        if self.SIMULATION:
            Builder = self.part_spice
        else:
            Builder = self.template

        # TODO: error from settings
        values = self.values_optimal(self.value, error=15) #if not self.SIMULATION else [self.value]
        elements = []
        # print(f'{self.value} by {values}')

        total_value = 0
        for index, value in enumerate(values):
            if type(value) == list:
                parallel_in = Net('CombinationArrayIn_' + str(index))
                parallel_out = Net('CombinationArrayOut_' + str(index))

                for part in value:
                    part = u(part)
                    unit = self.value.clone()
                    unit._value = part
                    unit = unit.canonise()

                    r = Builder(value=unit)
                    total_value += part / 2 if self.increase else part

                    r[1] += parallel_in
                    r[2] += parallel_out

                if index:
                    previous_r = elements[-1]
                    previous_r[2] += parallel_in

                elements.append((None, parallel_in, parallel_out))

            else:
                value = u(value)
                unit = self.value.clone()
                unit._value = value
                unit = unit.canonise()
                r = Builder(value=unit)
                total_value += value if self.increase else value / 2

                self.element = r

                if index:
                    previous_r = elements[-1]
                    previous_r[2] += r[1]

                elements.append(r)

        self.value._value = total_value

        self.input += elements[0][1]
        self.output += elements[-1][2]

    def parallel_sum(self, values):
        return (1 / sum(1 / np.array(values))) if self.increase else sum(values)

    def series_sum(self, values):
        return sum(values) if self.increase else 1 / sum(1 / np.array(values))

