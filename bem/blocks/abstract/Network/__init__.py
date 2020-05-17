from bem import Block, Net, Build, u_V, u_s
from sympy import Integer
import inspect
import sys
import builtins
from skidl import Bus, Network
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

    def willMount(self):
        """
            H -- Transfer function of the block
        """
        pass


    def finish(self):
        super().finish()

        pins = self.get_pins_definition()
        for pin in pins.keys():
            net = getattr(self, pin)
            if net:
                if hasattr(self, 'element') and self.element and len(self.element.pins) == 2:
                    # Try to not use this network name
                    # Broke css schematics
                    # net.name = net.name + '_N$'
                    pass

                net.fixed_name = False

    # Link Routines
    def __getitem__(self, *pin_ids, **criteria):
        if len(pin_ids) == 1 and hasattr(self, str(pin_ids[0])):
            return getattr(self, pin_ids[0])

        if hasattr(self, 'element') and self.element:
            return self.element.__getitem__(*pin_ids, **criteria)

        return None

    def create_network(self):
        # detect by caller method name kind of connetion __and__ or __or__
        # get self from caller
        # Add notes

        notes = self.trace_call_comment(3)

        frame = sys._getframe(1)
        connect_method = frame.f_code.co_name
        instance = frame.f_locals['self']
        if connect_method == '__and__':
            self.comment_pins_connections([self.input, instance[-1]], notes)
        elif connect_method == '__or__':
            self.comment_pins_connections([self.input, self.output, instance[0], instance[-1]], notes)

        return Network(self.input, self.output)

    def trace_call_comment(self, depth=2):
        frame = sys._getframe(depth)
        if frame.f_code.co_name != 'circuit':
            frame = sys._getframe(depth +1)

        # Search in code
        code = []
        notes = []
        try:
            code = inspect.getsourcelines(frame.f_code)[0]
            code_line = frame.f_lineno - frame.f_code.co_firstlineno
        except OSError:
            if hasattr(builtins, 'code'):
                code = builtins.code.split('\n')
                code_line = frame.f_lineno - 1


        if len(code):
            self.log(code[code_line])
            notes = self.inspect_comment(code, code_line, code_line)
            self.log(str(notes))

        return notes

    def comment_pins_connections(self, nets_or_pins, notes):
        if type(nets_or_pins) != list:
            nets_or_pins = [nets_or_pins]

        for net_or_pin in nets_or_pins:
            if type(net_or_pin) is NetType:
                elements = net_or_pin.get_pins()
            else:
                elements = net_or_pin.get_nets()

            for entry in elements:
                entry.notes += notes

            net_or_pin.notes += notes

    def connect_priority_net(self, net_a, net_b):
        is_nets = False # type(net_a) is NetType and type(net_b) is NetType

        if is_nets:
            swp_net = net_a

            if net_a.fixed_name == None:
                swp_net = net_a

            if net_b.fixed_name == None:
                swp_net = net_b

            self.log('Connect nets' + str(net_a) + ' + ' + str(net_b) + ' Swap ' + str(swp_net))

            swp_fixed_name = swp_net.fixed_name
            swp_net.fixed_name = True

        net_a & net_b

        if is_nets:
            swp_net.fixed_name = swp_fixed_name

    def __and__(self, instance, notes=[]):
        self.log("AAADDD")
        notes = self.trace_call_comment()

        if issubclass(type(instance), Block):
            self.__series__(instance, notes)

            return instance
        elif type(instance) == NetPinList:
            self.__and__(instance[0], notes)

            return instance
        elif type(instance) == list:
            for block in instance:
                self.__and__(block, notes)

            return instance
        else:
            self.comment_pins_connections([self.output, instance[0]], notes)

            # self.output & instance[0]
            self.connect_priority_net(self.output, instance[0])

            return instance

        raise Exception

    """
    TODO: += connect __setitem__
    def __setitem__(self, ids, *pins_nets_buses):
        # If the iadd_flag is set, then it's OK that we got
        # here and don't issue an error. Also, delete the flag.
        if getattr(self, "iadd_flag", False):
            del self.iadd_flag
            return

    def connect(self, *blocks_pins_nets):
        from skidl.utilities import flatten
        for pin in flatten(blocks_pins_nets):
            self & pin

        # Set the flag to indicate this result came from the += operator.
        self.iadd_flag = True

        return self
    __iadd__ = connect
    """

    def __rand__(self, instance, notes=[]):
        notes = self.trace_call_comment()

        if issubclass(type(instance), Block):
            instance.__series__(self, notes)

            return self
        elif type(instance) == NetPinList:
            self.__rand__(instance[0], notes)

            return self
        elif type(instance) == list:
            for block in instance:
                self.__rand__(block, notes)

            return self
        else:
            self.comment_pins_connections([self.input, instance[0]], notes)
            self.connect_priority_net(self.input, instance[0])

            return self

        raise Exception


    def __or__(self, instance, notes=[]):
        notes = self.trace_call_comment()

        # print(f'{self.title} parallel connect {instance.title if hasattr(instance, "title") else instance.name}')
        if issubclass(type(instance), Block):
            self.__parallel__(instance, notes)

            return self # NetPinList([self, instance])
        elif type(instance) == NetPinList:
            return self.__and__(instance[0], notes)
        else:
            self.comment_pins_connections([self.input, self.output, instance[0], instance[-1]], notes)
            self.connect_priority_net(self.input, instance[0])
            self.connect_priority_net(self.output, instance[-1])

            return self

        raise Exception

    def connect_power_bus(self, instance):
        if self.gnd and instance.gnd:
            self.gnd += instance.gnd

        if self.v_ref and instance.v_ref:
            self.v_ref & instance.v_ref

        if hasattr(self, 'v_inv') and hasattr(instance, 'v_inv'):
            self.v_inv & instance.v_inv


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
            original_net = getattr(self, pin, None)
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


    # TODO: Lcapy experimental
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
