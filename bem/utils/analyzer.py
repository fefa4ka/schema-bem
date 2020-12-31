from enum import Enum

class Line(Enum):
    GND = 'GNDREF'
    VCC = 'VBUS'
    VEE = 'GNDA'
    INPUT = 'LINEI'
    OUTPUT = 'LINEO'

# Detect what is Vcc, Vinv, GND, lines
def assume_line_type(net):
    if not net:
        return None

    if net == '0' or net == 'gnd': # or net.find('Gnd') != -1 
        return Line.GND

    if net == 'v_ref': # net[0:2] == 'VS' or 
        return Line.VCC

    if net.find('VInv') != -1 or net == 'v_inv':
        return Line.VEE

    if net.find('Input') != -1 or net.find('input') == 0:
        return Line.INPUT

    if net.find('Output') != -1 or net.find('output') == 0:
        return Line.OUTPUT

    return None

def assume_airwire_direction(net_or_pin):
    line_type = assume_line_type(net_or_pin)
    direction = None
    if line_type in [Line.VEE, Line.GND, Line.OUTPUT]:
        direction = 'input'

    if line_type in [Line.VCC, Line.INPUT]:
        direction = 'output'

    return direction

def is_line_power(net):
    line_type = assume_line_type(net)
    if line_type in [Line.VEE, Line.GND, Line.VCC]:
        return True

    return False

