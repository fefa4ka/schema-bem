from bem import Block

class Base(Block):
    """
        Basic block. It accept argument 'some_arg' and have parameter 'some_param'.
    """
    some_arg = 0
    some_param = 31337

    def willMount(self, some_arg):
        """
            some_param -- param description parsed by BEM Block
        """

        print(self.name + ': Base willMount with param =', some_arg)
