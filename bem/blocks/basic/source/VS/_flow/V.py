from bem import u, u_V, u_s
from lcapy import Vdc
from sympy import Float


class Modificator:
    # def transfer(self, time=0 @ u_s):
    #     return Float(u(self.value))
    def get_spice_arguments(self):
        return {
            'value': self.V
        }

    def network(self):
        return Vdc(self.V)

    def part(self):
        return super().part(value=self.V)
