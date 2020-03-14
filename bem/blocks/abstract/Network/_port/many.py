from .. import Base

class Modificator(Base):
    pins = {
        'v_ref': True,
        'input': True,
        'input_n': True,
        'output': True,
        'gnd': True
    }

    def willMount(self, inputs=None):
        if inputs:
            self.inputs = inputs
        else:
            pins = self.get_pins()
            default_input = []
            for pin in pins.keys():
                if pin.find('input') != -1:
                    default_input.append(getattr(self, pin))

            self.inputs = default_input

        self.outputs = [self.output]

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
