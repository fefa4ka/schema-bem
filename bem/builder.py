import logging
from collections import OrderedDict
from functools import lru_cache
from inspect import getmro

from skidl import SKIDL, SPICE, TEMPLATE, Part, SchLib, set_default_tool
from skidl.tools.spice import set_net_bus_prefixes

from .base import Block as BaseBlock
from .utils.structer import lookup_block_class, lookup_mod_classes, \
                            mods_predefined, mods_from_dict
from .utils.args import default_arguments

logger = logging.getLogger(__name__)


@lru_cache(maxsize=100)
def PartCached(library, symbol, dest):
    return Part(library, symbol, dest=dest)


class Build:
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.mods = {}
        self.props = {}
        self.models = []
        self.inherited = []
        self.files = []

        base_file, self.base = lookup_block_class(self.name)

        if self.base:
            self.files.append(str(base_file))

            self.mods = {
                **mods_predefined(self.base),
                **mods_from_dict(kwargs)
            }

            mod_files, mod_classes, mods_loaded = lookup_mod_classes(self.name, self.mods)
            self.files += mod_files
            self.models += mod_classes

            for mod in self.mods:
                if mod not in mods_loaded:
                    self.props[mod] = self.mods[mod]

            self.mods = mods_loaded

            self.files = sorted(set(self.files), key=self.files.index)
            self.files.reverse()

            if hasattr(self.base, 'files') and isinstance(self.base.files, list):
                self.files += list(self.base.files)
        else:
            self.props = kwargs

    # Run once
    def ancestors(self, ancestor=None):
        if not ancestor:
            self.inherited = []

        ancestor = ancestor or self.base
        
        mods = {}
        if ancestor and hasattr(ancestor, 'mods'):
            mods = ancestor.mods
        else:
            mods = self.mods

        self.mods = {
            **mods,
            **self.mods
        }

        inherited = []
        if hasattr(ancestor, 'inherited'):
            inherited = ancestor.inherited

        for parent in inherited:
            ParentBlock = parent(**mods)
            parent_models = ParentBlock.models
            parent_models.reverse()
            self.inherited += parent_models[1:-1]

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

        Block = type(self.name,
                     tuple(Models),
                     {
                         'name': self.name,
                         'mods': self.mods,
                         'props': self.props,
                         'files': self.files,
                         'models': Models
                     })

        Block.classes = list(getmro(Block))
        Block.models = tuple(Models)
        Block.arguments, Block.defaults = default_arguments(Block)

        return Block

    @property
    def element(self):
        return self.block().element

    @property
    def spice(self):
        set_default_tool(SPICE)
        set_net_bus_prefixes('N', 'B')
        _splib = SchLib('pyspice', tool=SKIDL)

        for p in _splib.get_parts():
            if self.name == p.name or (hasattr(p, 'aliases') and self.name in p.aliases):
                return p

        if self.name.find(':') != -1:
            kicad, spice = self.name.split(':')

            return PartCached(kicad, spice, dest=TEMPLATE)
