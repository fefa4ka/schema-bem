from bem import Block, Net, Build, u_V, u_s
from sympy import Integer
import inspect
from skidl import Bus
from skidl.Net import Net as NetType
from skidl.NetPinList import NetPinList

class Base(Block):
    pins = {}

    v_ref = None
    gnd = None

    def __init__(self, *args, **kwargs):
        self.set_pins()

        super().__init__(*args, **kwargs)

        transfer = self.transfer()
        if transfer:
            self.H = transfer.latex_math()

        pins = self.get_pins_definition()
        for pin in pins.keys():
            net = getattr(self, pin)
            if net:
                net.fixed_name = False

    # Link Routines
    def __getitem__(self, *pin_ids, **criteria):
        if len(pin_ids) == 1 and hasattr(self, str(pin_ids[0])):
            return getattr(self, pin_ids[0])

        if self.element:
            return self.element.__getitem__(*pin_ids, **criteria)

        return None


    def __and__(self, instance):
        if issubclass(type(instance), Block):
            # print(f'{self.title} series connect {instance.title if hasattr(instance, "title") else instance.name}')
            self.__series__(instance)

            return instance
        elif type(instance) == NetPinList:
            self.__and__(instance[0])

            return instance
        elif type(instance) == list:
            for block in instance:
                super().__and__(block)

            return instance
        else:
            self.output += instance[0]

            return instance
            # try:
            #     ntwk = instance.create_network()
            # except AttributeError:
            #     raise Exception

            # self.output += ntwk[0]

            # return ntwk[-1]
            # return Network(self.output, ntwk[-1])

        raise Exception

    def __rand__(self, instance):
        if issubclass(type(instance), Block):
            # print(f'{self.title} series connect {instance.title if hasattr(instance, "title") else instance.name}')
            instance.__series__(self)

            return self
        elif type(instance) == NetPinList:
            self.__rand__(instance[0])

            return self
        elif type(instance) == list:
            for block in instance:
                super().__rand__(block)

            return self
        else:
            self.input += instance[0]

            return self

        raise Exception


    def __or__(self, instance):
        # print(f'{self.title} parallel connect {instance.title if hasattr(instance, "title") else instance.name}')
        if issubclass(type(instance), Block):
            self.__parallel__(instance)

            return NetPinList([self, instance])
        elif type(instance) == NetPinList:
            return self.__and__(instance[0])
        else:
            # try:
            #     ntwk = instance.create_network()
            # except AttributeError:
            #     raise Exception

            self.input += instance[0]
            self.output += instance[-1]

            return self

    def create_network(self):
        return [self.input, self.output]

    def connect_power_bus(self, instance):
        if self.gnd and instance.gnd:
            self.gnd += instance.gnd

        if self.v_ref and instance.v_ref:
            self.v_ref += instance.v_ref


    # Pins
    def get_pins(self):
        pins = {}
        for key, value in inspect.getmembers(self, lambda item: not (inspect.isroutine(item))):
            if type(value) == NetType and key not in ['__doc__', 'element', 'simulation', 'ref']:
                pins[key] = [str(pin).split(',')[0] for pin in getattr(self, key) and getattr(self, key).get_pins()]

        return pins

    def get_pins_definition(self):
        pins = self.pins 
        pins = pins if type(pins) == dict else pins()

        return pins

    def set_pins(self):
        pins = self.get_pins_definition() 
        for pin in pins.keys():
            pin_description = [pins[pin]] if type(pins[pin]) == bool else pins[pin]
            device_name = ''.join([name for name in self.name.split('.') if name[0] == name[0].upper()])
            net_name = device_name + ''.join([word.capitalize() for word in pin.split('_')])

            related_nets = [pin]

            # pin = True, str -- Net(pin_name | str)
            # pin = Int -- Bus(pin_name, Int)
            original_net = getattr(self, pin) if hasattr(self, pin) else None
            if type(pin_description) in [list, tuple]: 
                for pin_data in pin_description:
                    if type(pin_data) == str:
                        net_name = device_name + pin_data

                    if type(pin_data) == list:
                        related_nets += pin_data
            else:
                if type(pin_description) == int:
                    original_net = Bus(pin, pin_description)
                else:
                    net_name = device_name + pin_description


            if not original_net:
                original_net = Net(net_name)

            original_net.fixed_name = True

            for net in related_nets:
                setattr(self, net, original_net)

    def transfer(self):
        if hasattr(self, 'network'):
            network = self.network()
            try:
                return network.Vtransfer.inverse_laplace(casual=True)
            except:
                return network.Isc.transient_response()

        return None

    def transient(self, start=0 @ u_s, stop=0 @ u_s, num=50):
        time_space = linspace(start, stop, num)

        return self.transfer().evaluate(time_space)
