from bem.example import Child

class Base(Child()):
    complex_param = 'lala'

    def willMount(self):
        print(self.name + ':', 'Complex willMount')


