
from blocks.Abstract.Combination import Base as Block
from skidl import Part, Net, subcircuit, TEMPLATE
from PySpice.Unit import u_Ohm, u_V, u_W, u_A, u_S
import numpy as np
from bem import Build, u
import logging

class Base(Block):
    """Resistor
    
    Generic resistance. 
    Resistance implemented by combination of series or parallel connected resistors from available values in stock. 
    """

    increase = True
    value = 1000 @ u_Ohm
    G = 0 @ u_S
    V_drop = 0 @ u_V

    ref = 'R'

    def willMount(self, value):
        """
            value -- A resistor is made out of some conducting stuff (carbon, or a thin metal or carbon film, or wire of poor conductivity), with a wire or contacts at each end. It is characterized by its resistance.
            V_drop -- Voltage drop after resistor with Load 
        """

        if type(value) in [str, int, float]:
            value = float(value) @ u_Ohm

        self.value = self.Power = value
        
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

    def series_sum(self, values):
        return sum(values) @ u_Ohm

    def parallel_sum(self, values):
        return 1 / sum(1 / np.array(values)) @ u_Ohm

    def part_spice(self, *args, **kwargs):
        return Build('R').spice(*args, **kwargs)

    def part_template(self):
        part = Part('Device', 'R', footprint=self.footprint, dest=TEMPLATE)
        part.set_pin_alias('+', 1)
        part.set_pin_alias('-', 2)

        return part

    def circuit(self):
        values = self.values_optimal(self.value, error=5) if not self.SIMULATION else [self.value]
        resistors = []
        
        self.log(f'{self.value} implemented by {len(values)} resistors: ' + ', '.join([str(value) + " Ω" for value in values]))
        total_value = 0
        for index, value in enumerate(values):
            if type(value) == list:
                parallel_in = Net()
                parallel_out = Net()
                
                for resistance in value:
                    r = self.part(value=resistance)
                    r.ref = self.ref
                    total_value += resistance.value * resistance.scale
                        
                    r[1] += parallel_in
                    r[2] += parallel_out
                
                if index:
                    previous_r = resistors[-1]
                    previous_r[2] += parallel_in[1]

                resistors.append((None, parallel_in, parallel_out))

            else:
                r = self.part(value=value)
                total_value += value.value * value.scale
                r.ref = self.ref
                self.element = r
                        
                if index:
                    previous_r = resistors[-1]
                    previous_r[2] += r[1]
                
                resistors.append(r)

        self.value = total_value @ u_Ohm
        
        self.input += resistors[0][1]
        self.output += resistors[-1][2]
        