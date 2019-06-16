from bem import Block, Stockman, Build
from bem.abstract import Electrical
from skidl import Part, Net, TEMPLATE
from collections import defaultdict
from copy import copy
import string

class Base(Electrical()):
    model = ''

    template = None
    units = 1

    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'unit'):
            self.unitsInit(*args, **kwargs) 
        else:
            kwargs['circuit'] = False
            super().__init__(*args, **kwargs)

            self.part_aliases()
            self.circuit()
        
    def unitsInit(self, *args, **kwargs):
        units = self.props.get('units', 1)

        params = {
            'A': kwargs
        }

        props = {
            'A': self.props
        }

        if len(args) == 1 and type(args[0]) == dict:
            params = args[0]
            args = ()

        if type(units) == int:
            self.units = list(string.ascii_uppercase)[:units]
        
        if type(units) == dict:
            keys = units.keys()
            self.units = list(keys)
            props = units
        else:
            props = { unit: props['A'] for unit in self.units }

        units_requested = self.units
        unit_queue = copy(self.units)
        unit_queue.reverse()
        while unit_queue:
            unit = unit_queue.pop()
            unit_props = props.get(unit, None) or props[self.units[0]]
            unit_params = params.get(unit, None) or params[self.units[0]]
    
            instance = self.unitMount(unit, args, unit_props, unit_params)

            if len(instance.units) > len(units_requested):
                units_requested = instance.units
                unit_queue = list(set(unit_queue + instance.units))
                unit_queue.remove(unit)

    def unitMount(self, unit, args, props, params):
        instance = self
        if unit != self.units[0]:
            instance = copy(self)

        setattr(self, unit, instance)
        setattr(instance, 'parent', self)
        setattr(instance, 'props', props)
        setattr(instance, 'unit', unit)
        
        instance.__init__(*args, **params)

        return instance

    def willMount(self, model=None):
        # pass
        part = self.props.get('part', None)

        if part:
            # library, device = part.split(':')
            # part = {
            #     model: device
            # }

            # self.selected_part = part
            self.selected_part = part
            self.template = self.part_template()

        if not hasattr(self.parent, 'selected_part'):
            selected_part = self.parent.select_part()
            self.parent.apply_part(selected_part)


    def available_parts(self):
        parts = Stockman(self).suitable_parts()
        
        if len(parts) == 0:
            args = self.get_arguments()
            params = self.get_params()
            values = {
                **args,
                **params
            }
            description = ', '.join([ arg + ' = ' + str(values[arg].get('value', '')) + values[arg]['unit'].get('suffix', '') for arg in values.keys()])
            
            raise LookupError("There are should be parts in stock for %s block with suitable characteristics\n%s" % (self.name, description))
            
            
        return parts
      
    def select_part(self):
        available = list(self.available_parts())
        model = self.model

        if model:
            for part in available:
                if part.model == model:
                    return part
        
        part = available[0] if len(available) > 0 else None

        return part

    def apply_part(self, part):
        self.selected_part = part
        
        if self.selected_part.model != self.model:
            self.model = self.selected_part.model

        self.props['footprint'] = self.selected_part.footprint.replace('=', ':')

        if not self.SIMULATION:
            self.template = self.part_template()
            
        units = defaultdict(lambda: defaultdict(list))
        for pin in self.selected_part.pins:
            units[pin.unit][pin.block_pin].append(pin.pin)
            
        self.units = list(units.keys())
        
            # if stock.params
            # if self.units > 1 and type(units) == dict:
            #     for unit in units.keys():


    # Physical or Spice Part
    def part_template(self):
        """
            self.name or self.part should contains definition with ':', for example 'Device:R' 
            or part_template method shoud redefined
        """
        stock = self.selected_part
        if self.props.get('part', None):
            library, symbol = self.props['part'].split(':')
        else:
            library = stock.library
            symbol = stock.symbol

        part = Part(library, symbol, footprint=self.footprint, dest=TEMPLATE)

        return part

    def part_aliases(self):
        if not hasattr(self.selected_part, 'pins'):
            return
            
        part = self.part()

        units = defaultdict(lambda: defaultdict(list))
        for pin in self.selected_part.pins:
            units[pin.unit][pin.block_pin].append(pin.pin)

        # for unit in units.keys():
        for block_pin in units[self.unit]:
            for part_pin in units[self.unit][block_pin]:
                pin_number = int(part_pin.split('/')[1])
                device_name = self.name.replace('.', '')
                net_name = device_name + ''.join([word.capitalize() for word in block_pin.split('_')]) + str(pin_number)
                pin_net = Net(net_name)
                pin_net += part[pin_number]

                setattr(self, block_pin, pin_net)

    def part_spice(self, *args, **kwargs):
        part = Build((self.selected_part.symbol or self.model) + ':' + self.model).spice

        return part(*args, **kwargs)

    def part(self, *args, **kwargs):
        if not hasattr(self.parent, '_part'):
            if self.SIMULATION:
                part = self.part_spice(*args, **kwargs)
            else:
                part = self.template(*args, **kwargs)

            if len(part.pins) == 2:
                part.set_pin_alias('p', 1)
                part.set_pin_alias('n', 2)
                part.set_pin_alias('+', 1)
                part.set_pin_alias('-', 2)

            self.parent._part = part

        part = self.parent._part

        return part

    @property
    def footprint(self):
        return self.props.get('footprint', None)
    
    def set_pins_aliases(self, pins):
        for pin in pins.keys():
            aliases = pins[pin]
            aliases = [aliases] if type(aliases) == str else aliases
            for alias in aliases:
                self.template.set_pin_alias(alias, pin)

            self.template[pin].aliases = { alias for alias in aliases }