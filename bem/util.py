from PySpice.Unit import u_s, u_Hz, u_A, u_V


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
            return float(unit)
        except:
            return float(unit[:-1]) * _prefix[unit[-1]]
    else:
        return float(unit.convert_to_power())


def label_prepare(text):
    last_dash = text.rfind('_')
    if last_dash > 0:
        text = text[:last_dash] + '$_{' + text[last_dash + 1:] + '}$'

    return text

def is_tolerated(a, b, tollerance=0.1):
    """
    A mathematical model for symmetrical parameter variations is
    `P_(nom) * (1 − ε) ≤ P ≤ P_(nom)(1 + ε)`
    in which `P_(nom)` is the nominal specification for the parameter such as the resistor value or independent source value, and `ε` is the fractional tolerance for the component. 

    For example, a resistor `R` with nominal value of 10 kOhm and a 5 percent tolerance could exhibit a resistance anywhere in the following range:
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
        b = float(b)
        a = float(a)
        diff = abs(a - b)
        if diff < a * tollerance:
            return True
    except:
        pass

    return False

def get_arg_units(part, arg):
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

def get_minimum_period(sources):
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


def merge(source, destination):
    """
    run me with nosetests --with-doctest file.py

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value

    return destination
