from ..interface import Interfaced

class Modificator(Interfaced):
    USB = ['D-', 'D+']

    def usb(self, instance):
        self.interface('USB', instance)
