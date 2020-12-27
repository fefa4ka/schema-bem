# -*- coding: utf-8 -*-

"""
Handler for reading PCBmodE libraries and generating netlists.
"""
import os
from collections import defaultdict
import json
from subprocess import PIPE, run

PCBMODE = tool_name = 'pcbmode'
lib_suffix = '_pcbmode.py'

def generate_netlist(self):
    components = {}
    for component in sorted(self.parts, key=lambda component: str(component.ref)):
        components[component.ref] = generate_netlist_component(component)
        components[component.ref]['pins'] = {}
        for pin in component.pins:
            components[component.ref]['pins'][pin.num] = {
                'name': str(pin),
                'net': str(pin.nets[0].name) if len(pin.nets) > 0 else ''
            }

    nets = {}
    for code, net in enumerate(
            sorted(self.get_nets(), key=lambda net: str(net.name))):
        net.code = code
        nets[net.name] = generate_netlist_net(net)

    netlist = {
        'components': components,
        'netlist': nets
    }

    import pathlib
    pwd = pathlib.Path(__file__).parent.absolute()
    working_dir = pathlib.Path().absolute()

    path = working_dir / 'netlist.json'
    with open(path, 'w') as f:
        json.dump(netlist, f)

    command = ['node', pwd / 'netlist.js', path]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    return result.stdout

def generate_netlist_component(self):

    try:
        value = self.value
        if not value:
            value = self.name
    except AttributeError:
        try:
            value = self.name
        except AttributeError:
            value = self.ref_prefix

    try:
        footprint = self.footprint
    except AttributeError:
        print('No footprint for {part}/{ref}.'.format(
            part=self.name, ref=ref))
        footprint = 'No Footprint'

    # lib = add_quotes(getattr(self, 'lib', 'NO_LIB'))  # pylint: disable=unused-variable
    # name = add_quotes(self.name)  # pylint: disable=unused-variable

    # # Embed the hierarchy along with a random integer into the sheetpath for each component.
    # # This enables hierarchical selection in pcbnew.
    # hierarchy = add_quotes('/'+getattr(self,'hierarchy','.').replace('.','/')+'/'+str(randint(0,2**64-1)))
    # tstamps = hierarchy

    # fields = ''
    # for fld_name in self._get_fields():
    #     fld_value = add_quotes(self.__dict__[fld_name])
    #     if fld_value:
    #         fld_name = add_quotes(fld_name)
    #         fields += '\n        (field (name {fld_name}) {fld_value})'.format(
    #             **locals())
    # if fields:
    #     fields = '      (fields' + fields
    #     fields += ')\n'

    part = {
        'footprint': footprint,
        'label': str(value)
    }
    return part

def generate_netlist_net(self):
    parts = defaultdict(list)
    for pin in sorted(self.get_pins(), key=str):
        parts[pin.part.ref].append(pin.num)

    return parts
