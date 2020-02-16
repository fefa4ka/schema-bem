from bem.example import Base

class Base(Base()):
    def willMount(self):
        print(self.name + ':', 'Child willMount')
