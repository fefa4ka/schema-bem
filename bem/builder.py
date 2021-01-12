import logging
from collections import OrderedDict
from functools import lru_cache
from inspect import getmro, currentframe

from os import path
from skidl import SKIDL, SPICE, TEMPLATE, Part, SchLib, set_default_tool
from skidl.tools.spice import set_net_bus_prefixes

from .base import Block as BaseBlock
from .utils.structer import lookup_block_class, lookup_mod_classes, \
                            mods_predefined, mods_from_dict
from .utils.args import default_arguments


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
log_handler = logging.FileHandler('bem.log')
log_handler.setFormatter(formatter)
log.addHandler(log_handler)





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

        if not self.base:
            self.props = kwargs
            return

        # Base Class that called

        # Class could maked from prebuilded Block
        # Class could inherit some class

        # Base Composed
        # InheritedBase + InheritedBase Modificator 
        # BlockBase + BlockBase Modificator

        bases = [self.base]

        request_mods = {
            **mods_predefined(self.base),
            **mods_from_dict(kwargs)
        }
        self.mods = {}

        classes = list(getmro(self.base))[:-1]
        if hasattr(self.base, 'inherited'):
            mod_files, mod_classes, mods_loaded = lookup_mod_classes(self.name, request_mods)
            for cls in mod_classes:
                request_mods = {
                    **request_mods,
                    **mods_predefined(cls)
                }
                log.info(mods_predefined(cls))


            self.inherited = self.base.inherited
            if not isinstance(self.base.inherited, list):
                self.inherited = [self.base.inherited]

            for model in self.inherited:
                block_base = model(**request_mods)
                bases.append(block_base)

        self.base.name = self.name
        base_compound = []

        for index, base in enumerate(bases):
            base_file, base_cls = lookup_block_class(base.name)

            if hasattr(self.base, 'models') and base_cls in self.base.models:
                # FIX: How recompoud if mods changed?
                # Maybe add only mod_class that not available
                # Is it possible remove old Modificators
                # Get position of original, detect available Modificators
                continue

            files = []
            files.append(str(base_file))

            request_mods = {
                **mods_predefined(base_cls),
                **request_mods,
            }
            mod_files, mod_classes, mods_loaded = lookup_mod_classes(base.name, request_mods)
            for cls in mod_classes:
                request_mods = {
                    **mods_predefined(cls),
                    **request_mods,
                }
            files += mod_files

            base_models = []
            if hasattr(base, 'models'):
                base_models = list(base.models)
                if index == 0:
                    base_compound = mod_classes
            else:
                base_models = [base]
                base_models += mod_classes

            base_models.reverse()
            self.models += base_models


            self.mods = { **self.mods,
                         **mods_loaded }

            files = sorted(set(files), key=files.index)
            files.reverse()

            if hasattr(base, 'files') and isinstance(base.files, list):
                files += list(base.files)

            self.files += files

        if self.base not in self.models:
            self.models.reverse()
            self.models.append(self.base)
            self.models += base_compound
            self.models.reverse()

        for mod in request_mods:
            if mod not in self.mods:
                self.props[mod] = request_mods[mod]

        self.log(str(self.models))

    def blocks(self):
        if self.base:
            Models = [self.base] + self.models.copy()

            Models.reverse()
        else:
            Models = [BaseBlock]

        return Models

    @property
    def block(self):
        def uniq_f7(seq):
            seen = set()
            seen_add = seen.add
            return [x for x in seq if not (x in seen or seen_add(x))]

        Models = uniq_f7(self.blocks())
        self.inherited = []

        self.files.reverse()
        self.files = uniq_f7(self.files)
        self.files.reverse()

        Block = type(self.name,
                     tuple(self.models),
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

    def log(self, message, *args):
        # Get the previous frame in the stack, otherwise it would
        # be this function
        func = currentframe().f_back.f_code
        anchor = "[%s:%i:%s] - " % (
            path.basename(path.dirname(func.co_filename)) + '/' + path.basename(func.co_filename),
            func.co_firstlineno,
            func.co_name
        )

        log.info(("%30s" % anchor) + str(self.name) + ' - ' + str(message), *args)
