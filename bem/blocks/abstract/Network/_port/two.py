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

    def __series__(self, instance, notes=[]):
        self.comment_pins_connections([self.output, instance.input, self.output_n, instance.input_n], notes)

        self.connect_priority_net(self.output, instance.input)
        self.connect_priority_net(self.output_n, instance.input_n)

        self.connect_power_bus(instance)

    def __parallel__(self, instance, notes=[]):
        self.comment_pins_connections([self.input, self.output, instance.input, instance.output, self.input_n, self.output_n, instance.input_n, instance.output_n], notes)

        self.connect_priority_net(self.input, instance.input)
        self.connect_priority_net(self.input_n, instance.input_n)

        self.connect_priority_net(self.output, instance.output)
        self.connect_priority_net(self.output_n, instance.output_n)

        self.connect_power_bus(instance)

    def Z_in(self):
        Z = self.network().Z1oc

        if hasattr(self, 'Z_Load'):
            return Z | self.Z_load
        else:
            return Z

    def Z_out(self):
        return self.network().Z2oc
