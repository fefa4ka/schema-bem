from bem import Block, Net, Build, u_V, u_s
from bem.utils.parser import inspect_comments, trace_call_comment
from sympy import Integer
import inspect
import sys
import builtins
from skidl import Bus, Network, Pin
from skidl.Net import Net as NetType
from skidl.NetPinList import NetPinList
from .utils import comment_pins_connections, annotate_pins_connections, connect_priority_net, pins_definition, assign_pins_to_block


class Base(Block):
    pins = {}

    v_ref = None
    gnd = None

    def __init__(self, *args, **kwargs):
        assign_pins_to_block(self)

        super().__init__(*args, **kwargs)

        """
        transfer = self.transfer()
        if transfer:
            self.H = transfer.latex_math()
        """

    def willMount(self):
        """
            H -- Transfer function of the block
        """
        pass


    def finish(self):
        super().finish()

        pins = pins_definition(self.pins)
        for pin in pins.keys():
            net = getattr(self, pin)
            if net:
                if hasattr(self, 'element') and self.element and len(self.element.pins) == 2:
                    # Try to not use this network name
                    # Broke css schematics
                    # net.name = net.name + '_N$'
                    pass

                net.fixed_name = False

        annotate_pins_connections(self)

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

        notes = trace_call_comment(3)

        frame = sys._getframe(1)
        connect_method = frame.f_code.co_name
        instance = frame.f_locals['self']
        if connect_method == '__and__':
            comment_pins_connections([self.input, instance[-1]], notes)
        elif connect_method == '__or__':
            comment_pins_connections([self.input, self.output, instance[0], instance[-1]], notes)

        return Network(self.input, self.output)



    def __and__(self, instance, notes=[]):
        notes = trace_call_comment()

        if issubclass(type(instance), Block):
            self.__series__(instance, notes)

            return instance
        elif isinstance(instance, NetPinList):
            self.__and__(instance[0], notes)

            return instance
        elif isinstance(instance, list):
            for block in instance:
                self.__and__(block, notes)

            return instance
        else:
            comment_pins_connections([self.output, instance[0]], notes)

            # self.output & instance[0]
            connect_priority_net(self.output, instance[0])

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
        notes = trace_call_comment()

        if issubclass(type(instance), Block):
            instance.__series__(self, notes)

            return self
        elif isinstance(instance, NetPinList):
            self.__rand__(instance[0], notes)

            return self
        elif isinstance(instance, list):
            for block in instance:
                self.__rand__(block, notes)

            return self
        else:
            comment_pins_connections([self.input, instance[0]], notes)
            connect_priority_net(self.input, instance[0])

            return self

        raise Exception


    def __or__(self, instance, notes=[]):
        notes = trace_call_comment()

        # print(f'{self.title} parallel connect {instance.title if hasattr(instance, "title") else instance.name}')
        if issubclass(type(instance), Block):
            self.__parallel__(instance, notes)

            return self # NetPinList([self, instance])
        elif isinstance(instance, NetPinList):
            return self.__and__(instance[0], notes)
        else:
            comment_pins_connections([self.input, self.output, instance[0], instance[-1]], notes)
            connect_priority_net(self.input, instance[0])
            connect_priority_net(self.output, instance[-1])

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
            if isinstance(value, NetType) and key not in ['__doc__', 'element', 'simulation', 'ref']:
                pins[key] = [str(pin).split(',')[0] for pin in getattr(self, key) and getattr(self, key).get_pins()]

        return pins

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


