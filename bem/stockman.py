from .model import Part
from .model import Param, Mod, Prop
from .utils.args import u, is_tolerated

class Stockman:
    def __init__(self, block):
        self.block = block

    @property
    def request(self):
        block = self.block
        load = {
             'V': block.V,
             'P': block.P,
             'I': block.I,
             'Z': block.Z
        }

        """
        load = {}

        params = block.get_params()
        args = block.get_arguments()
        keys = { **params, **args }
        for param in keys:
            if param not in ['units', 'unit', 'model', 'Load']:
                continue

            load[param] = keys[param]['value']
        """
        self.upper_limit = load.keys()

        params = list(block.props.keys()) + list(block.mods.keys()) + list(load.keys())
        values = list(block.props.values()) + list(block.mods.values()) + list(load.values())

        return params, values

    def related_parts(self):
        name = self.block.name
        parts = Part.select().where(Part.block == name)

        return parts

    def suitable_parts(self, parts=[]):
        """Available parts in stock
            from Part model
            filtered by Block modifications and params and spice model.

        Returns:
            list -- of parts with available values
        """
        available = []

        for part in parts:
            if self.is_part_proper(part):
                available.append(part)

        for part in self.related_parts():
            if self.is_part_proper(part):
                available.append(part)

        return available

    def is_part_proper(self, part):
        params, values = self.request

        if not self.check_mods(part):
            return False

        units = int(values[params.index('units')] if 'units' in params else 1)
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

    def get_param(self, part, param):
        values = []
        part_params = part.params.where(Param.name == param)
        for part_param in part_params:
            values.append(part_param.value)

        return values

    def check_param(self, part, param, desire):
        part_params = part.params.where(Param.name == param)
        if part_params.count():
            for part_param in part_params:
                if self.is_value_proper(param, desire, part_param.value):
                    return True
            else:
                return False

        return True

    def check_mods(self, part):
        for mod in part.mods:
            block_mod = self.block.mods.get(mod.name, None)
            if not block_mod:
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
        # TODO: Maybe strict negative value comparation needed
        if param in self.upper_limit:
            return self.is_value_enough(desire, value)
        else:
            return self.is_value_preicise(desire, value)

    def is_value_preicise(self, desire, value):
        if is_tolerated(desire, value):
            return True

        return False

    def is_value_enough(self, desire, value, multiple=1):
        if abs(u(value)) >= abs(u(desire)) * multiple:
            return True

        return False

    def is_units_enough(self, part, units):
        part_units = part.params.where(Param.name == 'units')
        if len(part_units) >= units or units == 1:
            return True

        return False
