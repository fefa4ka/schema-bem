from bem import Build
from bem.abstract import Electrical
from lcapy import log10
from copy import copy


class Base(Electrical()):
    def part_spice(self, *args, **kwargs):
        part = self.mods['flow'][0]
        kwargs['ref'] = self.ref = 'V' + part + self.props.get('ref', self.ref)
        block = Build(part).spice(*args, **kwargs)

        return block

    def __mod__(self, other):
        """Decibels

        Arguments:
            other {Signal} -- the signal compared with

        Returns:
            [float] -- Compared the relative amplitudes in dB of two Signals
        """
        return 20 * log10(other.amplitude / self.amplitude)


