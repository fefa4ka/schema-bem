from ..interface import Interfaced
from bem.basic import Resistor
from bem import u_Ohm
from skidl import Part, Net
#import sys, time, pylibftdi as ftdi

class Modificator(Interfaced):
    """
        * Atmel. "4.1 SPI Programming Interface" AVR042: AVR Hardware Design Considerations, 2016, p. 8"
    """

    ISP = ['SCK', 'MISO', 'MOSI', 'RST']

    def isp(self, instance):
        self.interface('ISP', instance)

        self.gnd & instance.gnd
