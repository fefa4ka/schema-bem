  
from .model import Part 
from .model import Param, Mod, Prop
from .util import u, is_tolerated

class Stockman:
    upper_limit = []
    
    def __init__(self, block):
        self.block = block

    @property
    def request(self):
        block = self.block
        load = {
             'V': getattr(block, 'V', None),
             'P_load': block.P_load,
             'I_load': block.I_load,
             'R_load': block.R_load
        }

        self.upper_limit = load.keys()

        params = list(block.props.keys()) + list(block.mods.keys()) + list(load.keys())
        values = list(block.props.values()) + list(block.mods.values()) + list(load.values())
        
        return params, values
        
    def related_parts(self):
        name = self.block.name
        parts = Part.select().where(Part.block == name)
        
        return parts

    def suitable_parts(self):
        """Available parts in stock 
            from Part model
            filtered by Block modifications and params and spice model.
        
        Returns:
            list -- of parts with available values
        """
        available = []

        parts = self.related_parts()
        
        for part in parts:
            if self.is_part_proper(part):
                available.append(part)

        return available
    
    def is_part_proper(self, part):
        params, values = self.request

        units = value[params.index('units')] if 'units' in params else 1
        if not self.is_units_enough(part, units):
            return False
        
        for index, param in enumerate(params):
            if param == 'value':
                continue
            
            value = values[index]
            
            is_param_proper = self.check_attrubute(part, param, value)

            if is_param_proper:
                continue

            break
        else:
            return True
        
        return False

    def check_attrubute(self, part, attribute, desire):
        checks = ['param', 'mod', 'property', 'spice']
        
        for check in checks:
            check_is_proper = getattr(self, 'check_' + check)
            is_proper = check_is_proper(part, attribute, desire)
                
            if not is_proper:
                break
        else:
            return True

        return False

    def check_param(self, part, param, desire):
        part_params = part.params.where(Param.name == param)
        if part_params.count():
            for part_param in part_params:
                if self.is_value_proper(param, desire, part_param.value):
                    return True
            else:
                return False

        return True
    
    def check_mod(self, part, mod, desire):
        part_mods = part.mods.where(Mod.name == mod)
        if part_mods.count():
            for part_mod in part_mods:
                if self.is_value_proper(mod, desire, part_mod.value):
                    return True
            else:
                return False

        return True
    
    def check_property(self, part, property, desire):
        part_props = part.props.where(Prop.name == property)
        if part_props.count():
            for part_prop in part_props:
                return self.is_value_proper(property, desire, part_prop.value)
            else:
                return False

        return True
        
    def check_spice(self, part, param, desire):
        spice_param = part.spice_params.get(param, None)
        if spice_param:
            return self.is_value_proper(param, desire, spice_param)

        return True
            
    def is_value_proper(self, param, desire, value):
        if param in self.upper_limit:
            return self.is_value_enough(desire, value)
        else:
            return self.is_value_preicise(desire, value)

    def is_value_preicise(self, desire, value):
        if is_tolerated(desire, value):
            return True
            
        return False
    
    def is_value_enough(self, desire, value, multiple=1):
        if u(value) >= u(desire) * multiple:
            return True

        return False 

    def is_units_enough(self, part, units):
        part_units = part.params.where(Param.name == 'units')
        if len(part_units) >= units or units == 1:
            return True
        
        return False
