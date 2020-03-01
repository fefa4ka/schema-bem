from .. import Base
from bem import Build, u, u_V, u_s
from lcapy import Vdc
from sympy import Float

class Modificator(Base):
    initial_value = 0 @ u_V
    pulsed_value = 0 @ u_V
    pulse_width = 0 @ u_s
    period = 0 @ u_s
    delay_time = 0 @ u_s

    def willMount(self, initial_value, pulse_width, period, delay_time):
        self.pulsed_value = self.V

    def get_spice_arguments(self):
        arguments = {}
        for arg in ['initial_value', 'pulsed_value', 'pulse_width', 'period', 'delay_time']:
            arguments[arg] = getattr(self, arg)

        return arguments

    def part(self):
        return super().part(**self.get_spice_arguments())

