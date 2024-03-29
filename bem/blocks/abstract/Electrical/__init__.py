from bem import u, Block
from bem.utils.parser import inspect_comments, inspect_ref
from bem.utils import uniq_f7
from bem.abstract import Network
from PySpice.Unit import u_V, u_Ohm, u_A, u_W, u_S, u_s
from lcapy import R
from skidl.net import Net as NetType
import sys
import re
import inspect
import builtins

tracer_instances = [None]

class Base:
    inherited = Network
    mods = { 'port': 'one' }

    #doc_methods = ['willMount', 'circuit']

    # For stockman
    P = 0 @ u_W
    I = 0 @ u_A
    Z = 0 @ u_Ohm

    P_load = 0 @ u_W
    I_load = 0 @ u_A
    R_load = 0 @ u_Ohm

    def __init__(self, *args, **kwargs):
        self.element = None

        sys.setprofile(None)

        is_ciruit_building = kwargs.get('circuit', True)
        if kwargs.get('circuit', None) != None:
            del kwargs['circuit']

        super().__init__(*args, **kwargs)

        if is_ciruit_building:
            self.release()

        if hasattr(self, 'Power') and not self.P:
            self.consumption(self.V)

        self.finish()

    def willMount(self, V=10 @ u_V, Load=1000 @ u_Ohm, ref=''):
        """
            V -- Volts across blocks v_ref or input terminals and gnd.
            V_out -- Volts across its output terminal and gnd
            ref -- Reference name used in schematics
            G -- Conductance `G = 1 / Z`
            Z -- Input unloaded impedance of the block
            P -- The power (energy per unit time) consumed by a circuit device. If a current `I` flows through through a given element in your circuit, losing voltage `V` in the process, then the power dissipated by that circuit element is the product of that current and voltage: `P = I × V`. A watt is a joule per second (`1 W = 1 J/s`)
            I -- Current is the rate of flow of electric charge past a point. The unit of measure is the ampere (`A`).  A current of 1 amp equals a flow of 1 coulomb of charge per second. By convention, current in a circuit is considered to flow from a more positive point to a more negative point, even though the actual electron flow is in the opposite direction.
            Load -- Load attached to the block (A, W, Ω)
            I_load -- Connected load presented in Amperes
            R_load -- Connected load presented in Ohms
            P_load -- Connected load presented in Watts
        """
        self.load(self.V)

    def mount(self, *args, **kwargs):
        super().mount(*args, **kwargs)

        if hasattr(self, 'Power'):
            self.consumption(self.V)

    def release(self):
        self.build_frame = {}
        self.build_frames = []

        name = inspect_ref(self)

        # TODO: Hack for schema-explorer
        self.ref = ref = self.name if name in ['Block', 'Instance'] else name

        ref_index = 1
        while self.ref in self.refs:
            self.ref = ref + '_' + str(ref_index)
            ref_index += 1

        self.refs.append(self.ref)

        def tracer(frame, event, arg, self=self):
            if event == 'return':
                self.build_frame = frame
                if frame.f_code.co_name == 'circuit':
                    self.build_frames.append(frame)

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

        super().release()

    def finish(self):
        super().finish()

        ref_inner_blocks(self, split=not hasattr(self, 'root'))

    # Circuit Creation
    def circuit(self, *args, **kwargs):
        element = self.part(*args, **kwargs)

        if element:
            self.element = element

            if len(element.pins) == 2:
                positive = 1
                negative = 2

                if self.element['P']:
                    positive = 'P'
                elif self.element['A']:
                    positive = 'A'

                if self.element['N']:
                    negative = 'N'
                elif self.element['K']:
                    negative = 'K'

                self.input += self.element[positive]
                self.output += self.element[negative]

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


def ref_inner_blocks(block, split=True):
    name = block.ref
    name = name.split('.')[-1]
    values = []
    def short_tokens(origin_ref, length=4):
        tokens = re.findall('[A-Z0-9][^A-Z0-9]*', origin_ref)
        short_name = ''.join([token[0:length] for token in tokens])
        return short_name

    for frame in block.build_frames:
        for key, value in frame.f_locals.items():
            is_block_has_part = hasattr(value, 'element') and value.element
            is_block = issubclass(value.__class__, Block)
            is_not_refed = is_block and value not in values

            if key != 'self' and is_block and is_not_refed:
                # Search in code
                code = []
                try:
                    code = inspect.getsourcelines(frame.f_code)[0]
                except OSError:
                    if builtins.code:
                        code = builtins.code.split('\n')

                notes = []
                if len(code):
                    for index, line in enumerate(code):
                        line = line.replace(' ', '').strip()
                        if line.find(key + '=') == 0:
                            comment_line_start = comment_line_end = index
                            notes = inspect_comments(code, comment_line_start, comment_line_end)
                            if hasattr(value, 'notes'):
                                value.notes = uniq_f7(value.notes + notes)
                            else:
                                value.notes = notes
                            break

                key = ''.join([word.capitalize() for word
                               in key.replace('_', '.').split('.')])

                ref = key
                if split:
                    ref = name + '_' + key

                if len(ref) > 6:
                    name = name.replace('_', '')
                    ref = name + '_' + key

                if len(ref) > 6:
                    name = short_tokens(name, 3)
                    ref = name + key

                if len(ref) > 6:
                    ref = name + short_tokens(key, 3)

                if len(ref) > 6:
                    name = short_tokens(name, 2)
                    ref = name + short_tokens(key, 3)

                if len(ref) > 6:
                    ref = short_tokens(name, 2) + short_tokens(key, 2)

                if len(ref) > 6:
                    ref = ''.join(re.findall('[A-Z0-9]+', ref))

                if is_block_has_part:
                    values.append(value)
                    if value._part.ref != ref:
                        value._part.ref = ref
                    value._part.notes = uniq_f7(value._part.notes + notes)

                value.ref = ref
