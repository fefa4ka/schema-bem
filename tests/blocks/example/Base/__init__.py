from bem import Block

class Base(Block):
    """
        Basic block. It accept argument 'some_arg' and have parameter 'some_param'.
    """
    some_param = 31337

    def willMount(self, some_arg="str"):
        """
            some_param -- param description parsed by BEM Block
        """

        print(self.name + ': Base willMount with param =', some_arg)
