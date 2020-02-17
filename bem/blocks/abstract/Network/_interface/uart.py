from ..interface import Interfaced

class Modificator(Interfaced):
    UART = ['TX', 'RX']

    def uart(self, instance):
        rx = self['RX']
        tx = self['TX']

        rx += instance['TX']
        tx += instance['RX']
