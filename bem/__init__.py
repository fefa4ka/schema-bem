import sys
import os
import glob
import importlib
from pathlib import Path
from collections import defaultdict

from settings import BLOCKS_PATH
from .base import Block
from .util import u, is_tolerated
from .builder import Build
from .stockman import Stockman
from PySpice.Unit import *
from skidl import Net, set_default_tool, set_backup_lib, KICAD
set_backup_lib('.')
set_default_tool(KICAD)

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

builtins.SIMULATION = False


def bem_scope(root=BLOCKS_PATH):
    blocks = defaultdict(dict)

    # Get Blocks from current root scopes
    scopes = [ name for name in os.listdir(root) if os.path.isdir(os.path.join(root, name)) ]
    scopes = [ name for name in scopes if name[0].islower() ]

    for scope in scopes:
        # Get Blocks from current root
        scope_root = root + '/' + scope
        for file in glob.glob(scope_root + '/*/__init__.py'):
            tail = file.split('/') 
            element = tail[-2]
            if element[0].isupper() == False:
                continue

            blocks[scope][element] = defaultdict(list)

            for mod_type, mod_value in [(mod.split('/')[-2], mod.split('/')[-1]) for mod in glob.glob(scope_root + '/%s/_*/*.py' % element)]:
                if mod_value.find('_test.py') != -1:
                    continue

                mod_type = mod_type[1:]
                mod_value = mod_value.replace('.py', '')

                blocks[scope][element][mod_type].append(mod_value)

        inner_blocks = bem_scope(scope_root)
        blocks[scope] = {
            **blocks[scope],
            **inner_blocks
        }

    return blocks


def bem_scope_module(scopes, root=''):
    blocks = defaultdict(dict)

    # Get Blocks from current root scopes
    scopes_keys = [ name for name in scopes.keys() if name[0].islower() ]
    blocks_keys = [ name for name in scopes.keys() if name[0].isupper() ]

    for scope in scopes_keys:
        bem_scope_module(scopes[scope], '.'.join([root, scope]))

    for block in blocks_keys:
        def build(name=root[1:] + '.' + block, *arg, **kwarg):
            return Build(name, *arg, **kwarg).block

        blocks[block] = build 

    if root:
        sys.modules[__name__ + root] = type(root, (object,), blocks)


root = bem_scope()
bem_scope_module(root)


# Digital Units
from PySpice.Unit.Unit import Unit
from PySpice.Unit import u_Degree, _build_unit_shortcut
class Byte(Unit):
    __unit_name__ = 'byte'
    __unit_suffix__ = 'B'
    __quantity__ = 'byte'
    __default_unit__ = False 

_build_unit_shortcut(Byte())

