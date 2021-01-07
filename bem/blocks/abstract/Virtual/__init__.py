from bem.abstract import Network
from ..Network.utils import assign_pins_to_block, pins_definition


class Base(Network(port='two')):
    def __init__(self, *args, **kwargs):
        self.notes = []
        self.ref = ''
        for prop in kwargs.keys():
            setattr(self, prop, kwargs[prop])

        assign_pins_to_block(self)

        pins = pins_definition(self.pins)
        for pin in pins.keys():
            original_net = getattr(self, pin, None)
            original_net.fixed_name = False

    def circuit(self):
        pass
