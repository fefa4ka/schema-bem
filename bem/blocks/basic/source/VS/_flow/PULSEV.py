from bem import u, u_V, u_s, u_Hz
from lcapy import Vdc
from sympy import Float


class Modificator:
    def willMount(self, initial_value=0 @ u_V, pulse_width=0 @ u_s, period=0 @ u_s, delay_time=0 @ u_s, Frequency = 0 @ u_Hz):
        self.pulsed_value = self.V

        if self.Frequency:
            self.pulse_width = 1 / self.Frequency
            self.period = self.pulse_width * 2

    def get_spice_arguments(self):
        arguments = {}

        for arg in ['initial_value', 'pulsed_value', 'pulse_width', 'period', 'delay_time']:
            arguments[arg] = getattr(self, arg)

        return arguments

    def part(self):
        if SIMULATION:
            return super().part(**self.get_spice_arguments())
        else:
            return super().part(value='_| ' + str(self.V))

