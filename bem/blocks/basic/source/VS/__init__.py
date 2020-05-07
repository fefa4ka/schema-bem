from bem import Build, u_V

from bem.abstract import Physical
from skidl import Net, Part, TEMPLATE
from lcapy import log10
from copy import copy


class Base(Physical()):
    def willMount(self, V = 10 @ u_V, wire_gnd=True):
        if type(V) == slice:
            self.V_sweep = V

    def part_spice(self, *args, **kwargs):
        flow = self.mods['flow']
        part = flow[0] if type(flow) == list else flow
        kwargs['ref'] = self.ref = 'V' + part + self.props.get('ref', self.ref)
        block = Build(part).spice(*args, **kwargs)

        return block

    def circuit(self, *args, **kwargs):
        self.element = element = self.part(*args, **kwargs)

        # Ground problem fix

        if self.wire_gnd:
            gnd = Net.get('0')
            if not gnd:
                gnd = Net('0')

            gnd.fixed_name = True
            element['-'] & gnd

            # TODO: Probably bad idea, because you could mixing voltage sources
            self.output.fixed_name = True
            gnd & self.gnd

        self.v_ref & element['+'] & self.output
        self.gnd & element['-'] & self.input


    def __mod__(self, other):
        """Decibels

        Arguments:
            other {Signal} -- the signal compared with

        Returns:
            [float] -- Compared the relative amplitudes in dB of two Signals
        """
        return 20 * log10(other.amplitude / self.amplitude)


