from bem import Block
from skidl import Part, TEMPLATE
from PySpice.Unit import u_H

class Base(Block):
    increase = False
    value = 0 @ u_H

    def __init__(self, value):
        if type(value) in [float, int]:
            value = float(value) @ u_H

        self.value = value.canonise()
        
        self.circuit()

    @property
    def spice_part(self):
        from skidl.pyspice import L

        return L

    @property
    def part(self):
        if self.DEBUG:
            return

        part = Part('Device', 'L', footprint=self.footprint, dest=TEMPLATE)
        part.set_pin_alias('p', 1)
        part.set_pin_alias('n', 2)
        
        return part