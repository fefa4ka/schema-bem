from .. import Base

class Modificator(Base):
    pins = {
        'input': True,
        'output': True,
        'input_n': True,
        'output_n': True,
        'v_ref': True,
        'gnd': True
    }

    input = None
    input_n = None

    output = None
    output_n = None

    def __series__(self, instance):
        if self.output and instance.input:
            self.output._name = instance.input._name = f'{self.name}{instance.name}_Net'
            self.output += instance.input

        if self.output_n and instance.input_n:
            self.output_n += instance.input_n

        self.connect_power_bus(instance)

    def __parallel__(self, instance):
        self.input += instance.input
        self.input_n += instance.input_n

        self.output += instance.output
        self.output_n += instance.output_n

        self.connect_power_bus(instance)



    def Z_in(self):
        Z = self.network().Z1oc

        if hasattr(self, 'Z_Load'):
            return Z | self.Z_load
        else:
            return Z

    def Z_out(self):
        return self.network().Z2oc
