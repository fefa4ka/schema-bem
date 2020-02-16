import importlib
import logging
from pathlib import Path

from .base import Block as BaseBlock
from skidl import TEMPLATE
from inspect import getmro
from collections import OrderedDict

logger = logging.getLogger(__name__)

BLOCKS_PATH = 'blocks'

class Build:
    name = None
    base = None
    mods = {}
    props = {}
    models = {}
    files = []

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.mods = {}
        self.props = {}
        self.models = []
        self.inherited = []
        self.files = []

        block_dir = self.name.replace('.', '/')

        base_file = Path(BLOCKS_PATH) / block_dir / ('__init__.py')
        self.base = base_file.exists() and importlib.import_module(BLOCKS_PATH + '.' + self.name).Base

        if self.base:
            self.files.append(str(base_file))

            for mod, value in kwargs.items():
                if type(value) == list:
                    self.mods[mod] = value
                else:
                    value = str(value)
                    self.mods[mod] = value.split(',')

            for mod, value in self.base.mods.items():
                if not self.mods.get(mod, None):
                    self.mods[mod] = value

            for mod, values in self.mods.items():
                if type(values) != list:
                    values = [str(values)]

                for value in values:
                    for mod_block_dir in set([block_dir]):
                        module_file = Path(BLOCKS_PATH) / mod_block_dir / ('_' + mod) / (value + '.py')
                        if module_file.exists():
                            Module = importlib.import_module(BLOCKS_PATH + '.' + mod_block_dir.replace('/', '.') + '._' + mod + '.' + value)
                            self.models.append(Module.Modificator)

                            if hasattr(Module.Modificator, 'files'):
                                self.files += Module.Modificator.files
                                self.files.append(str(module_file))
                                print(mod, value, Module.Modificator.files)

                            mods = Module.Modificator.mods if hasattr(Module.Modificator, 'mods') else None
                            if mods:
                                self.mods = {
                                    **mods,
                                    **self.mods
                                }

                        else:
                            self.props[mod] = value

            for key, value in self.props.items():
                del self.mods[key]
        else:
            self.props = kwargs

        self.files = sorted(set(self.files), key=self.files.index)
        self.files.reverse()
        if type(self.base.files) == list:
            self.files += list(self.base.files)


    # Run once
    def ancestors(self, ancestor=None):
        if not ancestor:
            self.inherited = []

        ancestor = ancestor or self.base
        mods = ancestor.mods if ancestor and hasattr(ancestor, 'mods') else self.mods
        inherited = ancestor.inherited if hasattr(ancestor, 'inherited') else []
        for parent in inherited:
            ParentBlock = parent(**mods)
            parent_models = getmro(ParentBlock)[1:-1]
            self.inherited += parent_models

            parent_files = ParentBlock.files.copy()
            self.files += parent_files

            self.ancestors(ParentBlock)


        return list(OrderedDict.fromkeys(self.inherited))


    def blocks(self):
        if self.base:
            Models = self.models.copy()

            Models.reverse()

            if self.base not in Models:
                Models.append(self.base)

            Models += self.ancestors()

        else:
            Models = [BaseBlock]

        return Models

    @property
    def block(self):
        def uniq_f7(seq):
            seen = set()
            seen_add = seen.add
            return [x for x in seq if not (x in seen or seen_add(x))]

        Models = self.blocks()
        self.inherited = []

        self.files.reverse()
        self.files = uniq_f7(self.files)
        self.files.reverse()

        print('BUILD:', self.name, Models, self.files)
        Block = type(self.name,
                    tuple(Models),
                    {
                        'name': self.name,
                        'mods': self.mods,
                        'props': self.props,
                        'files': self.files,
                        'models': Models
                    })

        return Block

    @property
    def element(self):
        return self.block().element

    @property
    def spice(self):
        from skidl import SKIDL, SPICE, set_default_tool, SchLib, Part
        from skidl.tools.spice import set_net_bus_prefixes

        set_default_tool(SPICE)
        set_net_bus_prefixes('N', 'B')
        _splib = SchLib('pyspice', tool=SKIDL)

        for p in _splib.get_parts():
            if self.name == p.name or (hasattr(p, 'aliases') and self.name in p.aliases):
                return p

        if self.name.find(':') != -1:
            kicad, spice = self.name.split(':')

            return Part(kicad, spice, dest=TEMPLATE)
