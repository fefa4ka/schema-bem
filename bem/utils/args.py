from PySpice.Unit import u_s, u_Hz, u_A, u_V
from PySpice.Unit import FrequencyValue, PeriodValue
from PySpice.Unit.Unit import UnitValue
from copy import copy
from inspect import getargspec, signature as func_signature
from . import uniq_f7


_prefix = {
    'y': 1e-24,  # yocto
    'z': 1e-21,  # zepto
    'a': 1e-18,  # atto
    'f': 1e-15,  # femto
    'p': 1e-12,  # pico
    'n': 1e-9,   # nano
    'u': 1e-6,   # micro
    'm': 1e-3,   # mili
    'c': 1e-2,   # centi
    'd': 1e-1,   # deci
    'k': 1e3,    # kilo
    'M': 1e6,    # mega
    'G': 1e9,    # giga
    'T': 1e12,   # tera
    'P': 1e15,   # peta
    'E': 1e18,   # exa
    'Z': 1e21,   # zetta
    'Y': 1e24,   # yotta
}

def u(unit):
    """Absolute float value of PySpice.Unit
    """
    if type(unit) in [int, float]:
        return float(unit)
    elif type(unit) == str:
        try:
            # unit = '10.2'
            return float(unit)
        except:
            # unit = '10 G'
            return float(unit[:-1]) * _prefix[unit[-1]]
    else:
        return float(unit.convert_to_power())


def is_tolerated(a, b, tollerance=0.1):
    """
    A mathematical model for symmetrical parameter variations is
    `P_(nom) * (1 − ε) ≤ P ≤ P_(nom)(1 + ε)`
    in which `P_(nom)` is the nominal specification for the parameter
    such as the resistor value or independent source value,
    and `ε` is the fractional tolerance for the component.

    For example, a resistor `R` with nominal value of 10 kOhm
    and a 5 percent tolerance could exhibit a resistance
    anywhere in the following range:
    `10,000 * (1 − 0.05) ≤ R ≤ 10,000 * (1 + 0.05)`
    `9500 ≤ R ≤ 10,500`
    """

    if type(a) == list and b in a:
        return True

    if type(a) not in [int, float]:
        try:
            a = u(a)
        except:
            pass

    if type(b) not in [int, float]:
        try:
            b = u(b)
        except:
            pass

    if b == type(b)(a):
        return True

    try:
        b = abs(float(b))
        a = abs(float(a))
        diff = abs(a - b)
        if diff < a * tollerance:
            return True
    except:
        pass

    return False


def unit_from_arg(part, arg):
    description = getattr(part, 'description')
    part_type = 'current' if description.lower().find('current') != -1 else 'voltage'

    unit = None
    if arg.find('time') != -1 or arg.find('delay') != -1 or arg in ['pulse_width', 'period', 'duration']:
        unit = u_s

    if arg.find('frequency') != -1:
        unit = u_Hz

    if arg.find('amplitude') != -1 or arg.find('value') != -1 or arg.find('offset') != -1:
        if part_type == 'current':
            unit = u_A
        else:
            unit = u_V

    return unit


def min_period(sources):
    period = 0 # Default 100 ms
    min_period = None

    for source in sources:
        for arg in source['args'].keys():
            if arg.find('time') != -1 or arg in ['pulse_width', 'period', 'duration']:
                if source['args'][arg]['value']:
                    time = float(source['args'][arg]['value'])
                    if period < time:
                        period = time

                    if not min_period or min_period > time:
                        min_period = time

            if arg.find('frequency') != -1:
                time = 1 / float(source['args'][arg]['value'])
                if period < time:
                    period = time

                if not min_period or min_period > time:
                    min_period = time

    return period if min_period and period / min_period <= 20 else period / 5 if period else 1

def value_to_strict(value):
    default = value
    if type(value) in [UnitValue, PeriodValue, FrequencyValue]:
        value = {
            'value': default.value * default.scale,
            'unit': {
                'name': default.unit.unit_name,
                'suffix': default.unit.unit_suffix
            }
        }
    elif type(default) in [int, float]:
        value = {
            'value': default,
            'unit': {
                'name': 'number'
            }
        }
    elif type(default) == str:
        value = {
            'value': default,
            'unit': {
                'name': 'string'
            }
        }
    elif type(default) == type(None):
        value = {
            'unit': {
                'name': 'network'
            }
        }
    else:
        return False

    return value

def value_to_round(value):
    is_ci_value = isinstance(value, (UnitValue, PeriodValue, FrequencyValue))

    if is_ci_value:
        value = value.canonise() if value.value else value
        value = {
            'value': round(value.value, 1),
            'unit': {
                'name': value.unit.unit_name,
                'suffix': value.prefixed_unit.str()
            }
        }
    elif isinstance(value, (int, float)):
        value = {
            'value': value if isinstance(value, int) else round(value, 3),
            'unit': {
                'name': 'number'
            }
        }
    elif isinstance(value, str):
        value = {
            'value': value,
            'unit': {
                'name': 'string'
            }
        }
    else:
        return False


    return value

def default_arguments(block):
    args = []
    defaults = {}

    classes = block.classes
    classes.reverse()
    for cls in classes:
        if hasattr(cls, 'willMount'):
            args += getargspec(cls.willMount).args
            signature = func_signature(cls.willMount)
            defaults = { **defaults,
                     **{
                        k: v.default
                        for k, v in signature.parameters.items()
                    }
            }

    args = uniq_f7([arg for arg in args if arg != 'self'])

    return args, defaults


def parse_arguments(arguments, request, defaults):
    props = {}

    for attr in arguments:
        value = request.get(attr, None)

        props[attr] = copy(defaults.get(attr, None)) #copy(getattr(cls, attr))

        if not value:
            continue

        if isinstance(value, dict):
            value = value.get('value', None)

        if isinstance(props[attr], (int, float)):
            props[attr] = float(value)
        #elif type(props[attr]) in [str, bool]:
        #    props[attr] = arg
        # elif type(props[attr]) == list:
        #    props[attr] = props[attr][0]
        elif isinstance(props[attr], (UnitValue, PeriodValue, FrequencyValue)):
            if isinstance(value, (UnitValue, PeriodValue, FrequencyValue)):
                # unit value
                props[attr] = value
            elif isinstance(value, slice):
                # slice(start, stop, step)
                props[attr]._value = value.stop
            elif isinstance(value, list):
                # Range [start, stop]
                props[attr]._value = value[1]
            else:
                # number
                props[attr]._value = float(value)
        else:
            props[attr] = value

    return props
