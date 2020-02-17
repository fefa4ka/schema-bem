from ..interface import Interfaced

class Modificator(Interfaced):
    USB = ['D-', 'D+']

    def usb(self, instance):
        print('###USB', self)
        self.interface('USB', instance)
