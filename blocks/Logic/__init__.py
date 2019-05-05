from bem import Block, Build
from skidl import Net, subcircuit


class Base(Block):
    inputs = []
    outputs = []

    pins = {
        'v_ref': True,
        'gnd': True
    }

    def willMount(self, inputs=None):
        default_input = [Net()]
        if self.SIMULATION:
            self.input_b = Net()
            default_input = [Net(), self.input_b]

        self.inputs = self.outputs = inputs or default_input

    @property
    def input(self):
        return self.inputs[0]

    @property
    def output(self):
        return self.outputs[0]
