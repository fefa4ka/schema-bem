from ..interface import Interfaced
from bem.basic import Resistor
from bem import u_Ohm
from skidl import Part, Net
#import sys, time, pylibftdi as ftdi

class Modificator(Interfaced):
    SPI = ['SCK', 'MISO', 'MOSI', 'SS']

    def spi(self, instance):
        self.interface('SPI', instance)


    # def set_device(self):

    # # Set mode (bitbang / MPSSE)
    # def set_bitmode(d, bits, mode):
    #     return (d.setBitMode(bits, mode) if FTD2XX else
    #                 d.ftdi_fn.ftdi_set_bitmode(bits, mode))

    # # Open device for read/write
    # def ft_open(index=0):
    #     d = ftdi.Device(device_index=index)
    #     return d

    # # Set SPI clock rate
    # def set_spi_clock(d, hz):
    #     div = int((12000000 / (hz * 2)) - 1)  # Set SPI clock
    #     ft_write(d, (0x86, div%256, div//256))

    # # Read byte data into list of integers
    # def ft_read(d, nbytes):
    #     s = d.read(nbytes)
    #     return [ord(c) for c in s] if type(s) is str else list(s)

    # # Write list of integers as byte data
    # def ft_write(d, data):
    #     s = bytes(data)
    #     return d.write(s)

    # # Write MPSSE command with word-value argument
    # def ft_write_cmd_bytes(d, cmd, data):
    #     n = len(data) - 1
    #     ft_write(d, [cmd, n%256, n//256] + list(data))
