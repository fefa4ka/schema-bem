from .. import Base

class Modificator(Base):
    inputs = []
    outputs = []

    pins = {
        'v_ref': True,
        'input_a': True,
        'input_b': True,
        'gnd': True
    }

    def willMount(self, inputs=None, outputs=[]):
        default_input = [self.input_a, self.input_b]

        self.inputs = inputs or default_input
        self.outputs = outputs 

    @property
    def input(self):
        return self.inputs[0]

    @property
    def output(self):
        return self.outputs[0]

    def __and__(self, instance):
        if type(instance) == list:
            inputs = instance
        else:
            inputs = [instance]

        if len(inputs) != len(self.outputs):
            raise Exception

        for index, output in enumerate(self.outputs):
            output += inputs[index]

    def __rand__(self, instance):
        if type(instance) == list:
            self.inputs += instance
        else:
            self.inputs.append(instance)
