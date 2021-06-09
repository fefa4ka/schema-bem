from PySpice.Unit import u_Ohm, u_V
from lcapy import R
from bem import Build
from bem.abstract import Combination


class Base:
    """
    ## Description
    Typical resistors of the most frequently used type (metal-oxide film, metal film, or carbon film) come in values from 1 ohm (1 Ω) to about 10 megohms (10 MΩ).

    Resistors are also characterized by how much power they can safely dissipate (the most commonly used ones are rated at 1/4 or 1/8 W), their physical size, and by other
    parameters such as tolerance (accuracy), temperature coefficient, noise, voltage coefficient
    (the extent to which R depends on applied `V`), stability with time, inductance, etc.

    ## Features
    Resistor is characterized by its resistance `R = V / I`, where `R` is in ohms for `V` in volts and `I` in amps. This is known as Ohm’s law.

    Roughly speaking, resistors are used to _convert a voltage to a current, and vice versa_.

    ```
    voltage = 12 @ u_V
    vs = VS(flow='SINEV')(V=voltage, frequency=120)
    resistor = Example()
    load = Resistor()(1000, resistor.V_load)

    vs & resistor & load & vs

    watch = resistor
    ```

    ## Applications
    Resistors are used in *amplifiers as loads* for active devices, in *bias networks*, as *feedback* elements, "de-amplifiers" as [voltage divider](/block/analog.voltage.Divider#type=resistive). In combination with [capacitors](basic.Capacitor) they establish [time constants](analog.voltage.Decay) and act as [filters](analog.Filter).

    They are used to set operating currents and signal levels. Resistors are used in power circuits to reduce voltages by dissipating power, to measure currents, and to discharge capacitors after power is removed.

    They are used in precision circuits to establish currents, to provide accurate voltage ratios, to set precise gain values. In logic circuits they act as bus and line terminators and as “pull-up” and “pull-down” resistors.

    In *high voltage* circuits they are used to measure voltages and to equalize leakage currents among diodes or capacitors connected in series. In radiofrequency (RF) circuits they set the bandwidth of resonant circuits, and they are even used as coil forms for inductors.


    """

    inherited = Combination

    def willMount(self, value=1000 @ u_Ohm, V=12 @ u_V):
        """
            value -- A resistor is made out of some conducting stuff (carbon, or a thin metal or carbon film, or wire of poor conductivity), with a wire or contacts at each end. It is characterized by its resistance.
            V_drop -- Voltage drop after resistor with Load
        """
        self.Power = self.value

        # Power Dissipation
        I_total = self.V / (self.R_load + self.value)
        self.V_drop = self.value * I_total

        self.load(self.V - self.V_drop)
        self.consumption(self.V_drop)

    def part_spice(self, *args, **kwargs):
        return Build('R').spice(*args, **kwargs)

    # Lcapy experimental
    def network(self):
        return R(self.value)

