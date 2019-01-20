from bem import Block, Build
from skidl import Net, subcircuit
from PySpice.Unit import u_ms, u_Ohm, u_A, u_V, u_Hz


class Base(Block):
    """Diode Bridge

    Props:
    R_load=None, V_out=None, V_ripple=1 @ u_V, I_load=1 @ u_A, P_load=None, frequency=220 @ u_Hz
    
    wave = half | full
    rectifier = full | split

    Power = Build('Power').block
    DiodeBridge = Build('DiodeBridge', wave='full', rectifier='split').block

    VCC = Power(source=SINEV(amplitude=10@u_V, frequency=100@u_Hz))
    bridge = DiodeBridge(V_ripple = 0.01 @ u_V, frequency=100 @ u_Hz, R_load=600 @ u_Ohm, V_out = 10 @ u_V)
    bridge.output_gnd += gnd
    rc = VCC & bridge & divi
    der  & gnd
    """

    output_gnd = None
    V_out = None
    V_ripple = 1 @ u_V

    R_load = 0 @ u_Ohm
    I_load = 0 @ u_A
    P_load = 0
    frequency = 220 @ u_Hz
    
    def __init__(self, *args, **kwargs):
        super().__init__(circuit=False, *args, **kwargs)

        if self.R_load and self.V_out:
            self.I_load = self.V_out / self.R_load
        
        self.circuit()

    def __series__(self, instance):
        if self.output and instance.input:
            self.output._name = instance.input._name = f'{self.name}{instance.name}_Net'
            self.output += instance.input
        
        if self.output_gnd and instance.gnd:
            self.output_gnd += instance.gnd
        
        if self.v_ref and instance.v_ref:
            self.v_ref += instance.v_ref

    @subcircuit
    def circuit(self, **kwargs):
        self.input = Net("BridgeVoltage")
        self.gnd = Net()
        self.output = Net("BridgeOutput")
        self.output_gnd = Net()
        
        self.create_bridge()