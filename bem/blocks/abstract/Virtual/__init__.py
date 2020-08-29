from bem.abstract import Network
from ..Network.utils import assign_pins_to_block


class Base(Network(port='two')):
    def __init__(self, *args, **kwargs):
        assign_pins_to_block(self)

        for prop in kwargs.keys():
            if hasattr(self, prop):
                setattr(self, prop, kwargs[prop])

    def willMount(self, v_ref=None, input=None, input_n=None, output=None, output_n=None, gnd=None):
        pass

    def circuit(self):
        pass
