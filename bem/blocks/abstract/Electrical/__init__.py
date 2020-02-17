from bem import u
from bem.abstract import Network
from bem.tester import BuildTest
from PySpice.Unit import u_V, u_Ohm, u_A, u_W, u_S, u_s
from lcapy import R
import sys

tracer_instances = [None]

class Base(Network(port='one')):
    V = 10 @ u_V
    Power = 0 @ u_W
    Load = 1000 @ u_Ohm  # [0 @ u_Ohm, 0 @ u_A, 0 @ u_W]
    I_load = 1 @ u_A
    R_load = 1 @ u_Ohm
    P_load = 1 @ u_W

    doc_methods = ['willMount', 'circuit']

    element = None
    ref = ''

    def __init__(self, *args, **kwargs):
        sys.setprofile(None)

        is_ciruit_building = kwargs.get('circuit', True)
        if kwargs.get('circuit', None) != None:
            del kwargs['circuit']

        self.load(self.V)

        super().__init__(*args, **kwargs)

        if self.Power and not hasattr(self, 'P'):
            self.consumption(self.V)

        if is_ciruit_building:
            self.release()

    def release(self):
        self.circuit_locals = {}

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
        name = self.name.split('.')[-1]
        for key, value in self.circuit_locals.items():
            if key != 'self'and value not in values and hasattr(value, 'element') and value.element: 
                key = ''.join([word.capitalize() for word in key.replace('_', '.').split('.')])
                values.append(value)
                value.element.ref = name + '_' + key.capitalize()

        self.documentScheme()

    def documentScheme(self):
        pads = self.get_pins()

        for pad_name in pads.keys():
            for net in getattr(self, pad_name):
                for pin in net.get_pins():
                    pin.notes += pad_name + ':' + str(self)

    def willMount(self, V=None, Load=None):
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
        pass

    # Circuit Creation
    def circuit(self, *args, **kwargs):
        element = self.part(*args, **kwargs)
        if element:
            self.element = element

            self.input += self.element[1]
            self.output += self.element[2]

    # Consumption and Load

    def consumption(self, V):
        self.P = None
        self.I = None
        self.Z = None

        if self.Power == 0 @ u_Ohm or V == 0:
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
        self.R_load = None
        self.I_load = None
        self.P_load = None
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

        self.load_args = {
            'V': V_load,
            'Load': self.Load
        }

    def current(self, voltage, impedance):
        return voltage / impedance

    def power(self, voltage, impedance):
        return voltage * voltage / impedance

    def part(self, *args, **kwargs):
        return self.part_spice(*args, **kwargs)

    def part_spice(self, *args, **kwargs):
        return None

    def simulate(self, body_kit):
        Test = BuildTest(self.__class__, **(self.mods))

        def method_body_kit():
            return body_kit

        Test.body_kit = method_body_kit

        arguments = self.get_arguments()
        simulation = Test.simulate(arguments)

        return simulation

