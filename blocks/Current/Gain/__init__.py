from bem import Block, Voltage_Divider, Transistor_Bipolar, Resistor, u, u_Ohm, u_V, u_A
from skidl import Net

class Base(Block):
    """**Emitter-Follower** Common-Collector Amplifier
    
    The circuit shown here is called a common-collector amplifier, which has current gain but no voltage gain. It makes use of the emitter-follower arrangement but is modified to avoid clipping during negative input swings. The voltage divider (`R_s` and `R_g`) is used to give the input signal (after passing through the capacitor) a positive dc level or operating point (known as the quiescent point). Both the input and output capacitors are included so that an ac input-output signal can be added without disturbing the dc operating point. The capacitors, as you will see, also act as filtering elements.”

    * Paul Scherz. “Practical Electronics for Inventors, Fourth Edition
    """
    
    V_ref = 10 @ u_V
    V_in = 1 @ u_V
    # I_load = 0.015 @ u_A
    # R_load = 1000 @ u_Ohm

    I_in = 0 @ u_A
    R_e = 0 @ u_Ohm
    Beta = 100
    
    

    def __init__(self, V_ref, V_in, Load):
        """
        R_in -- `1/R_(i\\n) = 1/R_s + 1/R_g + 1 / R_(i\\n(base))`
        R_e -- `R_e = V_e / I_(load)`
        V_je -- Base-emitter built-in potential
        V_e -- `V_e = V_(ref) / 2`
        V_b -- `V_b = V_e + V_(je)` 
        I_in -- `I_(i\\n) = I_(load) / beta`
        R_in_base_dc -- `R_(i\\n(base),dc) = beta * R_e`
        R_in_base_ac -- `R_(i\\n(base),ac) = beta * (R_e * R_(load)) / (R_e + R_(load))`
        """
        
        self.V_ref = V_ref
        self.V_in = V_in
        self.Load = Load
        self.load(V_ref)
        self.input_n = None

        self.circuit()

    def circuit(self):
        R = Resistor()
        is_ac = 'ac' in self.mods.get('coupled', []) 
        is_compensating = 'compensate' in self.mods.get('drop', [])
        self.gnd = Net()
        self.v_ref = Net()
        
        self.input =  self.output = Net()
       
        self.V_e = self.V_ref / 2
        self.R_e = self.V_e / self.I_load
        
        if is_compensating:
            self.R_e = self.R_e * 2
        
        
        amplifier = Transistor_Bipolar(
            type='npn',
            common='emitter',
            follow='emitter')(
                emitter = R(self.R_e)
            )
        
        self.V_je = (amplifier.selected_part.spice_params.get('VJE', None) or 0.6) @ u_V
        self.V_b = self.V_e + self.V_je
        self.Beta = amplifier.selected_part.spice_params.get('BF', self.Beta) 
        self.I_in = self.I_load / self.Beta
        
        self.R_in_base_dc = self.Beta * self.R_e
        self.R_in_base_ac = self.Beta * ((self.R_e * self.R_load) / (self.R_e + self.R_load)) 

        stiff_voltage = Voltage_Divider(type='resistive')(
            V_in = self.V_ref,
            V_out = self.V_b,
            Load = self.I_in
        )
        stiff_voltage.gnd += self.gnd
        
        self.R_in = R.parallel_sum(R, [self.R_in_base_ac if is_ac else self.R_in_base_dc, stiff_voltage.R_in, stiff_voltage.R_out])

        if is_compensating:
            compensator = Transistor_Bipolar(
                type='pnp',
                common='collector',
                follow='emitter')(
                    emitter = R(self.R_e)
                )
            compensator.v_ref += self.v_ref
            compensator.gnd += self.input_n or self.gnd

            compensated = Net('CurrentGainCompensation')
            rc = self.v_ref & stiff_voltage & self.input & compensator & compensated
            self.output = compensated
        else:
            rc = self.v_ref & stiff_voltage & self.input
    
        amplified = Net('CurrentGainOutput')
        amplifier.v_ref += self.v_ref
        amplifier.gnd += self.input_n or self.gnd
        gain = self.output & amplifier & amplified 

        self.output = amplified
