from .. import Base
from bem import Build, u, u_V, u_Hz, u_V, u_s 
from lcapy import Vac, pi, f, t, sin, sqrt 
from sympy import Integer, Float
from numpy import linspace

class Modificator(Base):
    def willMount(self, frequency=1 @ u_Hz, dc_offset=0@ u_V, offset=0 @ u_V, delay=0 @ u_s, damping_factor=0):
        if type(frequency) == list:
            self.Frequency_range = frequency

        self.amplitude = self.V

    def get_spice_arguments(self):
        arguments = {}
        for arg in ['amplitude', 'frequency', 'dc_offset', 'offset', 'delay', 'damping_factor']:
            arguments[arg] = getattr(self, arg)

        return arguments

    def part(self):
        if self.SIMULATION:
            return super().part(**self.get_spice_arguments())
        else:
            return super().part(value='~ ' + str(self.V) + ' / ' + str(self.frequency))

    def network(self):
        return Vac(self.amplitude)

    def transfer(self, time=0 @ u_s):
        if time == 0:
            return self.amplitude * sin(2 * pi * self.frequency * t + self.phase())
        else:
            return self.amplitude * sin(2 * pi * f * time + self.phase())

    def phase(self):
        return Integer(0) if not self.delay else (2 * pi) / self.delay

    def phase_radian(self):
        return self.phase() / pi

    def period(self):
        return Integer(1) / self.frequency

    def angular_velocity(self):
        return 2 * pi * self.frequency

    def value(self, time=0 @ u_s):
        return self.transfer(time)

    def value_peak(self):
        return Float(self.amplitude)

    def value_rms(self):
        return self.value_peak() / sqrt(2)

    def value_avg(self):
        return 2 * self.value_peak() / pi


