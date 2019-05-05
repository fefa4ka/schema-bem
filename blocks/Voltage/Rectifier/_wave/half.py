from bem import Block, Diode
from skidl import Net, subcircuit


class Modificator(Block):
    """
    **Half-Wave Rectifier**

    For a sinewave input that is much larger than the forward drop (about 0.6 V for silicon diodes, the usual type). This circuit is called a half-wave rectifier, because only half of the input waveform is used.
    """

    def create_bridge(self):
        D = Diode(type='generic')
    
        circuit = self.input & D(V=self.V_out, Load=self.Load, ref='D_in_out')['A,K'] & self.output

    def circuit(self, **kwargs):
        super().circuit(**kwargs)

        self.output_n = self.input_n = self.gnd
