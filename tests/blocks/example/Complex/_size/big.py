from bem.example import Parent

class Modificator(Parent()):
    def willMount(self, big_mod_arg=0):
        print(self.name + ':', 'big modificator willMount with big_mod_arg =', big_mod_arg)
