
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
    """Resistor

    Generic resistance.
    Resistance implemented by combination of series or parallel connected resistors from available values in stock.

    """
    increase = True

    value = 1000 @ u_Ohm
    G = 0 @ u_S
    V_drop = 0 @ u_V

    def willMount(self):
        """
            value -- A resistor is made out of some conducting stuff (carbon, or a thin metal or carbon film, or wire of poor conductivity), with a wire or contacts at each end. It is characterized by its resistance.
            V_drop -- Voltage drop after resistor with Load
        """

        self.Power = self.value

        # Power Dissipation
        if self.Load.is_same_unit(1 @ u_Ohm):
            I_total = self.current(self.V, self.Load + self.value)
        elif self.Load.is_same_unit(1 @ u_A):
            I_total = self.I + self.Load
        elif self.Load.is_same_unit(1 @ u_W):
            I_total = (self.P + self.Load) / self.V

        self.V_drop = self.value * I_total

        self.load(self.V - self.V_drop)
        self.consumption(self.V)


    def network(self):
        return R(self.value)

    # def expression(self, time=0 @ u_s):
    #     return self.input + R(self.value)

    def part_spice(self, *args, **kwargs):
        return Build('R').spice(*args, **kwargs)

