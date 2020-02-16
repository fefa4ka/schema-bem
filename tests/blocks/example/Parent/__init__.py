from bem import Block
from bem.example import Base

class Base(Block):
    inherited = [Base]

    def willMount(self):
        print(self.name + ':', 'Parent willMount')
