from ..utils import comment_pins_connections, connect_priority_net


class Modificator:
    pins = {
        'input': True,
        'output': True,
        'input_n': True,
        'output_n': True,
        'v_ref': True,
        'gnd': True
    }

    def __series__(self, instance, notes=[]):
        instance_input_n = instance.input_n if hasattr(instance, 'input_n') else None

        pins = [self.output, instance.input, self.output_n]

        connect_priority_net(self.output, instance.input)

        if instance_input_n:
            pins.append(instance.input_n)
            connect_priority_net(self.output_n, instance.input_n)

        comment_pins_connections(pins, notes)

        self.connect_power_bus(instance)

    def __parallel__(self, instance, notes=[]):
        instance_input_n = instance.input_n if hasattr(instance, 'input_n') else None
        instance_output_n = instance.output_n if hasattr(instance, 'output_n') else None

        pins = [self.input, self.output, instance.input, instance.output, self.input_n, self.output_n]

        connect_priority_net(self.input, instance.input)

        if instance_input_n:
            pins.append(instance.input_n)
            connect_priority_net(self.input_n, instance.input_n)

        connect_priority_net(self.output, instance.output)

        if instance_output_n:
            pins.append(instance.output_n)
            connect_priority_net(self.output_n, instance.output_n)

        comment_pins_connections(pins, notes)

        self.connect_power_bus(instance)

    def Z_in(self):
        Z = self.network().Z1oc

        if hasattr(self, 'Z_Load'):
            return Z | self.Z_load
        else:
            return Z

    def Z_out(self):
        return self.network().Z2oc
