from bem import Block, Resistor, Abstract_Virtual
from skidl import Net, subcircuit
from PySpice.Unit import u_Ohm, u_A, u_V

class Base(Block):
    """**Switch**
    
    Switch connected series to the signal.
    """

    mods = {
        'input': ['physical']
    }

    V_ref = 15 @ u_V
    V_input = 10 @ u_V

    load_block = None

    pins = {
        'v_ref': True,
        'input': 'ControlP',
        'input_n': 'ControllerN',
        'output': 'LoadP',
        'output_n': 'LoadN'
    }

    def willMount(self, V_ref=None):
        if not self.gnd:
            self.gnd = Net()
        
        self.load_block = Abstract_Virtual()(input=self.output, output=self.output_n)
        
        self.load(self.V_ref)
        
    def circuit(self):
        pass

    # @property
    # def part(self):
    #     if self.SIMULATION:
    #         return

    #     return Part('Switch', 'SW_DPST', footprint=self.footprint, dest=TEMPLATE)

        # self.output += self.load.input
        # self.output_n += self.load.output

        # attach_load = self.output & self.load & self.output_n & self.gnd

        # if not self.SIMULATION:
        #     switch = self.part()
            
        #     self.input += switch['1,3']
        #     self.output += switch['2,4']
   