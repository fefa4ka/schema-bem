from .. import Base, Build
from skidl import Net
from PySpice.Unit import u_Ohm

class Modificator(Base):
    R_gnd = 1 @ u_Ohm

    def willMount(self, R_gnd):
        pass

    def circuit(self):
        super().circuit()
        
        signal = None
        if not (self.input and self.output):
            signal = self.input = Net('RLCInput')
            self.output = Net('RLCOutput')
        else:
            signal = self.output
            self.output = Net('GndResistorOutput')

        R = Build('Resistor').block
        R_out = R(value=self.R_gnd, ref='R_g', **self.load_args)

        circuit = signal & self.output & R_out['+,-'] & self.gnd