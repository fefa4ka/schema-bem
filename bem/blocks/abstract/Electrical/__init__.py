from bem import u, Block
from bem.abstract import Network
from PySpice.Unit import u_V, u_Ohm, u_A, u_W, u_S, u_s
from lcapy import R
import sys

tracer_instances = [None]

class Base(Network(port='one')):
    doc_methods = ['willMount', 'circuit']

    element = None
    ref = ''

    # For stockman
    P = 0 @ u_W
    I = 0 @ u_A
    Z = 0 @ u_Ohm

    def __init__(self, *args, **kwargs):
        sys.setprofile(None)

        is_ciruit_building = kwargs.get('circuit', True)
        if kwargs.get('circuit', None) != None:
            del kwargs['circuit']

        super().__init__(*args, **kwargs)

        if is_ciruit_building:
            self.release()

        if hasattr(self, 'Power') and not self.P:
            self.consumption(self.V)

    def mount(self, *args, **kwargs):
        super().mount(*args, **kwargs)

        if hasattr(self, 'Power'):
            self.consumption(self.V)

    def release(self):
        self.circuit_locals = {}

        name = self.get_ref()

        # TODO: Hack for schema-explorer
        self.ref = ref = self.name if name in ['Block', 'Instance'] else name
        ref_index = 1
        while self.ref in self.refs:
            self.ref = ref + '_' + str(ref_index)
            ref_index += 1

        self.refs.append(self.ref)

        name = self.ref
        name = name.split('.')[-1]

        def tracer(frame, event, arg, self=self):
            if event == 'return':
                self.circuit_locals = frame.f_locals

        # tracer is activated on next call, return or exception
        sys.setprofile(tracer)
        tracer_instances.append(tracer)

        try:
            # trace the function 
            self.circuit()
        finally:
            # disable tracer and replace with old one
            tracer_current = tracer_instances.pop()
            sys.setprofile(tracer_instances[-1])

        values = []

        for key, value in self.circuit_locals.items():
            is_block_has_part = hasattr(value, 'element') and value.element
            is_block = issubclass(value.__class__, Block)
            is_not_refed = value not in values
            if key != 'self' and is_block and is_not_refed:
                key = ''.join([word.capitalize() for word in key.replace('_', '.').split('.')])
                ref = name + '_' + key

                if is_block_has_part:
                    values.append(value)
                    value._part.ref = ref

                value.ref = ref

        self.annotate_pins_connections()

        super().release()

    def annotate_pins_connections(self):
        pads = self.get_pins()

        for pad_name in pads.keys():
            for net in getattr(self, pad_name):
                for pin in net.get_pins():
                    pin.notes += pad_name + ':' + str(self)

    def willMount(self, V=10 @ u_V, Load=1000 @ u_Ohm):
        """
            V -- Volts across its input terminal and gnd
            V_out -- Volts across its output terminal and gnd
            G -- Conductance `G = 1 / Z`
            Z -- Input unloaded impedance of block
            P -- The power dissipated by block
            I -- The current through a block
            I_load -- Connected load presented in Amperes
            R_load -- Connected load presented in Ohms
            P_load -- Connected load presented in Watts
        """
        self.load(self.V)

    # Circuit Creation
    def circuit(self, *args, **kwargs):
        element = self.part(*args, **kwargs)
        if element:
            self.element = element

            self.input += self.element[1]
            self.output += self.element[2]

    # Consumption and Load
    def consumption(self, V):
        # Reset class attributes, make it uniq for instance
        self.P = None # 0 @ u_W #None
        self.I = None # 0 @ u_A #None
        self.Z = None # 0 @ u_Ohm #None

        if not V or not hasattr(self, 'Power'):
            return

        Power = self.Power

        if Power.is_same_unit(1 @ u_Ohm):
            self.Z = Power
            self.I = V / self.Z

        if Power.is_same_unit(1 @ u_W):
            self.P = Power
            self.I = self.P / V
        else:
            if Power.is_same_unit(1 @ u_A):
                self.I = Power

            self.P = V * self.I

        if not self.Z:
            self.Z = V / self.I

        self.G = (1 / self.Z) @ u_S

    def load(self, V_load):
        # Predefine instance attributes
        self.R_load = None
        self.I_load = None
        self.P_load = None

        self.V_load = V_load
        Load = self.Load

        if type(Load) in [int, float] or Load.is_same_unit(1 @ u_Ohm):
            Load = self.Load = Load @ u_Ohm
            self.R_load = Load
            self.I_load = V_load / self.R_load

        if Load.is_same_unit(1 @ u_W):
            self.P_load = Load
            self.I_load = self.P_load / V_load
        else:
            if Load.is_same_unit(1 @ u_A):
                self.I_load = Load

            self.P_load = V_load * self.I_load

        if not self.R_load:
            self.R_load = V_load / self.I_load

        if not hasattr(self, 'Z_load'):
            self.Z_load = R(self.R_load)

    def current(self, voltage, impedance):
        return voltage / impedance

    def power(self, voltage, impedance):
        return voltage * voltage / impedance

    def part(self, *args, **kwargs):
        return self.part_spice(*args, **kwargs)

    def part_spice(self, *args, **kwargs):
        return None

