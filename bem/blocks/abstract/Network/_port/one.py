from ..utils import comment_pins_connections, connect_priority_net


class Modificator:
    pins = {
        'input': True,
        'output': True,
        'v_ref': True,
        'gnd': True
    }

    # Link Routines
    def __series__(self, instance, notes=[]):
        if hasattr(self, 'output') and hasattr(instance, 'input'):
            comment_pins_connections([instance.input, self.output], notes)

            connect_priority_net(self.output, instance.input)

        self.connect_power_bus(instance)

    def __parallel__(self, instance, notes=[]):
        comment_pins_connections([self.input, self.output, instance.input, instance.output], notes)

        connect_priority_net(self.input, instance.input)
        connect_priority_net(self.output, instance.output)

        self.connect_power_bus(instance)


    # TODO: Experimental
    def Z_in(self):
        Z = self.network().Z

        if hasattr(self, 'Z_Load'):
            return Z | self.Z_load
        else:
            return Z

    def Z_out(self):
        return self.network().Z

    def thevenin(self):
        """
            Thevenin’s theorem states that any two-terminal network of resistors and voltage sources is equivalent to a single impedance in series with a single voltage source V.
        """
        return (self.input.signal + self.Z).thevenin()

    def norton(self):
        """
            You can replace a Thévenin circuit with a Norton circuit, which consists of a current source IN in parallel with a impedance.
        """
        return (self.input.signal + self.Z).norton()

    def transfer(self):
        if hasattr(self, 'input') and hasattr(self, 'output'):
            if hasattr(self.input, 'signal') and hasattr(self.output, 'signal'):
                return self.output.signal.V.laplace() / self.input.signal.V.laplace()

        return super().transfer()
