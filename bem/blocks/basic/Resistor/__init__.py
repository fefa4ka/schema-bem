
# from blocks.Abstract.Combination import Base as Block
from skidl import Part, TEMPLATE
from PySpice.Unit import u_Ohm, u_V, u_W, u_A, u_S
from lcapy import R
from numpy import sum
from operator import or_ as Or
from functools import reduce
from bem import Block, Build, Net, u
from bem.abstract import Combination, Physical
import logging

class Base(Combination()):
    """
    # Generic resistance

    Resistance implemented by combination of series or parallel connected resistors from available values in stock.

    ```
    vs = VS(flow='SINEV')(V=5, frequency=120)
    load = Example()

    vs & load & vs

    watch = load
    ```

    """
    increase = True

    def willMount(self, value=1000 @ u_Ohm, V=12 @ u_V):
        """
            value -- A resistor is made out of some conducting stuff (carbon, or a thin metal or carbon film, or wire of poor conductivity), with a wire or contacts at each end. It is characterized by its resistance.
            V_drop -- Voltage drop after resistor with Load
        """
        self.Power = self.value
        self.consumption(self.V)

        # Power Dissipation
        I_total = self.V / (self.R_load + self.value)
        self.V_drop = self.value * I_total

        self.load(self.V - self.V_drop)

    def part_spice(self, *args, **kwargs):
        return Build('R').spice(*args, **kwargs)

    # Lcapy experimental
    def network(self):
        return R(self.value)

    # def expression(self, time=0 @ u_s):
    #     return self.input + R(self.value)

