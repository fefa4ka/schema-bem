from bem.abstract import Network
from ..Network.utils import assign_pins_to_block


class Base(Network(port='two')):
    def __init__(self, *args, **kwargs):
        self.notes = []
        self.ref = ''
        for prop in kwargs.keys():
            setattr(self, prop, kwargs[prop])

        assign_pins_to_block(self)

    def circuit(self):
        pass
