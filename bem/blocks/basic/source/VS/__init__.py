from bem import Build
from bem.abstract import Physical
from skidl import Net, Part, TEMPLATE
from lcapy import log10
from copy import copy


class Base(Physical()):
    def part_spice(self, *args, **kwargs):
        flow = self.mods['flow']
        part = flow[0] if type(flow) == list else flow
        kwargs['ref'] = self.ref = 'V' + part + self.props.get('ref', self.ref)
        block = Build(part).spice(*args, **kwargs)

        return block

    def circuit(self, *args, **kwargs):
        self.element = element = self.part(*args, **kwargs)
        # Ground problem fix
        gnd = Net.get('0')
        if not gnd:
            gnd = Net('0')

        gnd.fixed_name = True
        element['-'] & gnd

        # TODO: Probably bad idea, because you could mixing voltage sources
        self.output.fixed_name = True

        self.v_ref & element['+'] & self.output
        gnd & self.gnd & element['-'] & self.input

    def __mod__(self, other):
        """Decibels

        Arguments:
            other {Signal} -- the signal compared with

        Returns:
            [float] -- Compared the relative amplitudes in dB of two Signals
        """
        return 20 * log10(other.amplitude / self.amplitude)


