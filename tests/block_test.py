import os

# KiCAD modules and footprints paths
os.environ['KISYSMOD'] = '/Users/fefa4ka/Development/schema.vc/kicad/modules'
os.environ['KICAD_SYMBOL_DIR'] = '/Users/fefa4ka/Development/schema.vc/kicad/library'
# Path where is libngspice.dylib placed
os.environ['DYLD_LIBRARY_PATH'] = '/usr/local/Cellar/libngspice/28/lib/'

from bem import Block, bem_scope, u_V, u_Ohm
from bem.model import Part, Param

def test_bem_scope():
    blocks = bem_scope()

    assert blocks.get('example', False), 'Example scope should exists'
    assert blocks['example'].get('Base', None) != None, 'Base block should exists'


def assert_base_instance(instance, some_arg):
    assert instance.some_param == 31337, "Block should have same_param = 31337"
    assert instance.some_arg == some_arg, "Block should save some_arg as parameter"
    assert instance.get_params().get('some_param', None)['value'] == 31337, "some_param in dict shoudl be 31337"
    assert instance.get_arguments().get('some_arg', None)['value'] == some_arg, "some_arg in dict should be VALUE"

def test_bem_build():
    from bem.example import Base

    base = Base()
    instance = None

    try:
        instance = base()
        assert False, "Base block couldn't be created without argument"
    except:
        instance = base(some_arg="VALUE")

    description = base.get_description(base)
    assert description[0] == "\nBasic block. It accept argument 'some_arg' and have parameter 'some_param'.\n", 'Description should generated from block class docstring wrapped with \\n symbol'

    test_instance = Base(some_prop="PROP_VAL")(some_arg=12345)

    params_description = base.get_params_description(base)
    assert params_description.get('some_param', None) == 'param description parsed by BEM Block', 'some_param description should be set'

    assert_base_instance(instance, 'VALUE')
    assert instance.inherited == [], "Base block should not inherit something"
    assert instance.name == 'example.Base', 'Instance name should be example.Base'
    assert instance.get_ref() == 'Instance', 'Ref should be the same as variable name in code'
    assert instance.mods == {}, "Mods should not set for Base block"
    assert instance.props == {}, "Props should not set for this instance"
    assert len(instance.files) == 2, "Only from two files block should be builded"
    assert instance.files[0] == 'blocks/example/Base/__init__.py', "Front file should be Base/__init__.py"
    assert instance.files[1] == 'bem/base.py', "Last file should be bem/base.py"

    assert_base_instance(test_instance, 12345)
    assert test_instance.inherited == [], "Base block should not inherit something"
    assert test_instance.name == 'example.Base', 'Instance name should be example.Base'
    assert test_instance.get_ref() == 'TestInstance', 'Ref should be the same as variable name in code'
    assert test_instance.mods == {}, "Mods should not set for Base block"
    assert len(test_instance.files) == 2, "Only from two files block should be builded"
    assert test_instance.props.get('some_prop', None) == 'PROP_VAL', "Should be some_prop = PROP_VAL"

def test_bem_inherited_build():
    from bem.example import Parent, Child

    Block = Parent()
    instance = Block(some_arg=9876)
    assert instance.name == 'example.Parent', 'Instance name should be example.Parent'
    assert len(instance.inherited) == 1, "Parent block should inherit Base block"
    assert len(instance.files) == 3, "Only from three files block should be builded"
    assert instance.files[0] == 'blocks/example/Parent/__init__.py', "Front file should be Parent/__init__.py"
    assert instance.files[1] == 'blocks/example/Base/__init__.py', "Middle file should be Base/__init__.py"
    assert instance.files[2] == 'bem/base.py', "Last file should be bem/base.py"

    assert_base_instance(instance, 9876)

    instance_builded_parent = Child()(some_arg=0)

    assert_base_instance(instance_builded_parent, 0)
    assert instance_builded_parent.name == 'example.Child', 'Instance name should be example.Child'
    assert len(instance_builded_parent.inherited) == 0, "Parent block should not inherit Base block"
    assert len(instance_builded_parent.files) == 3, "Only from three files block should be builded"
    assert instance_builded_parent.files[0] == 'blocks/example/Child/__init__.py', "Front file should be Parent/__init__.py"
    assert instance_builded_parent.files[1] == 'blocks/example/Base/__init__.py', "Middle file should be Base/__init__.py"
    assert instance_builded_parent.files[2] == 'bem/base.py', "Last file should be bem/base.py"

def test_bem_modificator():
    from bem.example import Complex

    instance = Complex()(some_arg=123)
    assert_base_instance(instance, 123)
    assert instance.mods == {}, "Mods should not set for Base block"

    instance_mod = Complex(size='small')(some_arg=0, small_mod_arg=132)
    assert 'small' in instance_mod.mods.get('size', []), "Mod should be size = small"

    assert_base_instance(instance_mod, 0)
    instance_another_mod = Complex(size='big')(some_arg=333, big_mod_arg=31337)
    assert_base_instance(instance_another_mod, 333)
    assert 'big' in instance_another_mod.mods.get('size', []), "Mod should be size = big"

    instance_multiply_mod = Complex(size=['small', 'big'])(some_arg=123, small_mod_arg=1111, big_mod_arg=31337)
    instance_multiply_mods = instance_multiply_mod.mods.get('size', [])
    assert 'small' in instance_multiply_mods and 'big' in instance_multiply_mods, "Mod should be size = small, big"
    instance_multiply_mod = Complex(size=['big', 'small'])(some_arg=123)

def test_network():
    import builtins
    builtins.SIMULATION = False
    from bem.abstract import Network
    one = Network(port='one')()
    second = Network(port='one')()
    two = Network(port='two')()
    dubl_two = Network(port='two')()

    assert len(one.get_pins().keys()) == 4, "In Network port=one should be 4 pins"
    assert len(two.get_pins().keys()) == 6, "In Network port=two should be 6 pins"

    assert one.output.is_attached(second.input) == False, "Pins should not connected"
    link = one & second
    assert link == second, "Link should be last connected element"
    assert one.output.is_attached(second.input), "Pins should connected"

    assert (two.output.is_attached(dubl_two.input) or two.output_n.is_attached(dubl_two.input_n)) == False, "Two port should disconnected"
    double_link = two & dubl_two
    assert double_link == dubl_two, "Link should be last connected element"
    assert two.output.is_attached(dubl_two.input) and two.output_n.is_attached(dubl_two.input_n), "Two port should connected"

    interface = Network(interface='i2c')()
    interface_double = Network(interface=['i2c', 'uart'])()

def test_resistor(value=100):
    from bem.basic import Resistor

    part = Part(block='basic.Resistor',
        model='',
        library='Device',
        symbol='R',
        footprint='Resistor_SMD:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal',
        datasheet='',
        description='',
        spice=''
    )
    part.save()

    param = Param(name='value', value=value * 2)
    param.save()
    part.params.add(param)

    param = Param(name='value', value=value * 1.03)
    param.save()
    part.params.add(param)


    part = Part(block='basic.Resistor',
        model='',
        library='Device',
        symbol='R',
        footprint='Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal',
        datasheet='',
        description='',
        spice=''
    )
    part.save()

    param = Param(name='value', value=value / 4)
    param.save()
    part.params.add(param)

    param = Param(name='value', value=value * 1.02)
    param.save()
    part.params.add(param)

    test_impeadance = Resistor()(value @ u_Ohm, V=5 @ u_V, Load=570 @ u_Ohm)
    
    assert test_impeadance.value == value * 1.02, "Resistor should be as selected with tolerance error"
    assert test_impeadance.get_ref() == 'TestImpeadance' and test_impeadance.element.ref == 'TestImpeadance', 'Ref should be the same as variable name in code'
    assert test_impeadance.get_params()['V_drop']['value'] == 1.2, "V_drop should be 1.2 V for V == 5, Load = 570 Ohm"

    next_impeadance = Resistor()(240 @ u_Ohm, V=5 @ u_V - test_impeadance.V_drop, Load=330 @ u_Ohm)

    assert next_impeadance.get_ref() == 'NextImpeadance' and next_impeadance.element.ref == 'NextImpeadance_1', 'Ref should be the same as variable name in code'
    assert next_impeadance.get_params()['V_drop']['value'] == 1.6, "V_drop should be 1.6 V"

    last_impeadance = Resistor()(330 @ u_Ohm, V=5 @ u_V - test_impeadance.V_drop - next_impeadance.V_drop, Load=1 @ u_Ohm)
    assert last_impeadance.get_params()['V_drop']['value'] == 2.2, "V_drop should be 1.2 V"


    # Simulation test
    from bem.basic.source import VS

    dc = VS(flow='V')(V=10 @ u_V)

    dc & test_impeadance & next_impeadance & last_impeadance & dc

    from bem.simulator import Simulate
    # Simulation could be done from every used Block in schema
    #Simulate(test_impeadance).transient()


test_bem_scope()
test_bem_build()
test_bem_inherited_build()
test_bem_modificator()
test_network()
test_resistor(180)

