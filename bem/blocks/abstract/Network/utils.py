from skidl.Net import Net as NetType
from bem import Net


def comment_pins_connections(nets_or_pins, notes):
    if not len(notes):
        return

    if not isinstance(nets_or_pins, list):
        nets_or_pins = [nets_or_pins]

    for net_or_pin in nets_or_pins:
        if isinstance(net_or_pin, NetType):
            elements = net_or_pin.get_pins()
       # else:
        #    elements = net_or_pin.get_nets()

        for entry in elements:
            entry.notes += notes

        net_or_pin.notes += notes

def annotate_pins_connections(block):
    pads = block.get_pins()

    for pad_name in pads.keys():
        for net in getattr(block, pad_name):
            comment_pins_connections(net, pad_name + ':' + block.ref)

def connect_priority_net(net_a, net_b):
    is_nets = False #isinstance(net_a, NetType) and isinstance(net_b, NetType)

    if is_nets:
        swp_net = net_a

        if net_a.fixed_name == None:
            swp_net = net_a

        if net_b.fixed_name == None:
            swp_net = net_b

        swp_fixed_name = swp_net.fixed_name
        swp_net.fixed_name = True

    net_a & net_b

    if is_nets:
        swp_net.fixed_name = swp_fixed_name

def pins_definition(pins):
    pins = pins if isinstance(pins, dict) else pins()

    return pins

def assign_pins_to_block(block):
    pins = pins_definition(block.pins)
    for pin in pins.keys():
        pin_description = [pins[pin]] if isinstance(pins[pin], bool) else pins[pin]
        device_name = ''.join([name for name in block.name.split('.') if name[0] == name[0].upper()])
        net_name = device_name + ''.join([word.capitalize() for word in pin.split('_')])

        related_nets = [pin]

        # pin = True, str -- Net(pin_name | str)
        # pin = Int -- Bus(pin_name, Int)
        original_net = getattr(block, pin, None)
        if type(pin_description) in [list, tuple]:
            for pin_data in pin_description:
                if isinstance(pin_data, str):
                    net_name = device_name + pin_data

                if isinstance(pin_data, list):
                    related_nets += pin_data
        else:
            if isinstance(pin_description, int):
                original_net = Bus(pin, pin_description)
            else:
                net_name = device_name + pin_description


        if not original_net:
            original_net = Net(net_name)

        original_net.fixed_name = True

        for net in related_nets:
            setattr(block, net, original_net)

