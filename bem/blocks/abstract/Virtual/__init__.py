from bem.abstract import Network

class Base(Network(port='two')):
    def __init__(self, *args, **kwargs):
        self.set_pins()

        for prop in kwargs.keys():
            if hasattr(self, prop):
                setattr(self, prop, kwargs[prop])

    def willMount(self, v_ref=None, input=None, input_n=None, output=None, output_n=None, gnd=None):
        pass

    def circuit(self):
        pass