from ..interface import Interfaced
from bem import u_kOhm
from bem.basic import Resistor
from skidl import Part, Net

class Modificator(Interfaced):
    I2C = ['SCL', 'SDA']

    def i2c(self, instance):
        def pull_up():
            support = Net('PullUpSupport')
            pull_up = self.v_ref & Resistor()(4.7 @ u_kOhm) & support

            return support

        scl = self['SCL'] & pull_up() & instance['SCL']
        sda = self['SDA'] & pull_up() & instance['SDA']
