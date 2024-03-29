from bem import Build
from bem.abstract import Combination
from skidl import Part, TEMPLATE
from PySpice.Unit import u_F, u_V, u_C, u_J, u_F
import numpy as np
from lcapy import C


class Base(Combination()):
    """
        ## Description
        A capacitor (the old-fashioned name was condenser) is a device that has two wires sticking out of it and has the property
       `Q = CV`

        Taking the derivative of the defining equation, you get `I = C (dV)/(dt)`

        A farad is an enormous capacitance, and you usually deal in microfarads (μF), nanofarads (nF), or picofarads (pF).

        When you charge up a capacitor, you’re supplying energy. The capacitor doesn’t get hot; instead, it stores the energy in its internal electric fields.

        ## Applications
        * [Filters](/block/analog.Filter)
        * [Time constant](/block/analog.voltage.Decay)
        * Resonators
        * [Power supply](/block/analog.power.Supply)
        * [Voltage multiplier](/block/analog.voltage.Multiplier)

        ## Features
        So a capacitor is more complicated than a resistor: the current is not simply proportional to the voltage, but rather to the rate of change of voltage. If you change the voltage across a farad by 1 volt per second, you are supplying an amp. Conversely, if you supply an amp, its voltage changes by 1 volt per second.
        ```
        from bem.basic import Capacitor
        vs = VS(flow='SINEV')(V=5, frequency=[1, 1e3])
        load = Resistor()(1000)
        capacitor = Example()
        vs & capacitor & load & vs

        watch = capacitor
        ```

        ## Reference
        - Paul Horowitz and Winfield Hill. "1.4.1 Capacitors" The Art of Electronics – 3rd Edition. Cambridge University Press, 2015, pp. 51-52
    """
    __increase = False
    upper_limit = True

    def willMount(self, value = 1 @ u_F):
        """
            value -- The capacitance is proportional to the area and inversely proportional to the spacing. For the simple parallel-plate capacitor, with separation `d` and plate area `A` (and with the spacing `d` much less than the dimensions of the plates), the capacitance `C` is given by `C = 8.85 xx 10^-14 (εA)/d F` where `ε` is the [dielectric constant](https://en.wikipedia.org/wiki/Relative_permittivity) of the insulator, and the dimensions are measured in centimeters.
            Q -- A capacitor of `C` farads with `V` volts across its terminals has `Q` coulombs of stored charge on one plate and `−Q` on the other.
            U_C -- The capacitor stores the energy in its internal electric fields. The amount of stored energy in a charged capacitor is just `U_C = (CV^2)/2`
        """

        #self.value = self.value_closest(self.value) if not self.SIMULATION else self.value
        self.consumption(0)

        self.Q = self.value * self.V
        self.U_C = self.energy(self.V)

    # Lcapy
    def network(self):
        return C(self.value)

    def energy(self, voltage):
        return self.value * voltage * voltage / 2

    def voltage_after_time(self, time):
        return np.sqrt(self.V ** 2 - 2 * self.P_load * time / self.value)

    def discharge_to_voltage(self, V_min, step_time=1e-3, RMS=True, energy_remain=False):
        """Returns time to discharge from Vinit to Vmin in seconds.
        May also return remaining energy in capacitor

        Arguments:
            V_min {u_V} -- Minimal voltage

        Keyword Arguments:
            step_time{u_s} -- Time step-size (in seconds) (defaults to 1ms) (default: {1e-3})
            RMS {bool} -- if true converts RMS Vin to peak (default: {True})
            Eremain {bool} -- if true: also returns the energy remaining in cap (default: {False})
        """
        time = 0

        V_step = self.voltage_after_time(time)
        while V_step >= V_min:
            time = time + step_time
            V_prev = V_step
            V_step = self.voltage_after_time(time)

        E = self.energy(V_prev)

        return (time - step_time, E)

    def part_spice(self, *args, **kwargs):
        return Build('C').spice(*args, **kwargs)
