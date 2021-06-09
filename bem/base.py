from inspect import currentframe, getargspec, getmembers, isroutine
from os import path
from sys import _getframe, setprofile
from types import FunctionType
from typing import List, Set, Dict, Tuple, Optional

from codenamize import codenamize

from .utils.args import parse_arguments, value_to_round, value_to_strict
from .utils.logger import logger_init, block_params
from .utils.parser import (block_params_description, inspect_code,
                           inspect_comments, inspect_ref)

log = logger_init(__name__)


class Block:
    # Reference to global BEM scope
    scope = []

    # Current active block
    owner = [None]
    refs: List[str] = []

    # Sources used in block building
    files: List[str] = ['bem/base.py']

    # Inherited block classes
    # Another block could be inherited in different maniere:
    # * Inherit certain modification `class SomeBlock(InheritedBlock(mod='certain'))`
    # * inherited prop add ability to use any iherited modification
    inherited = []

    # Methods that used for parameters description extraction
    doc_methods: List[str] = ['willMount', 'circuit']

    def __init__(self, *args, **kwargs):
        # Build scope
        # Previous block, if they didn't release, owner of current
        self.scope.append((self.owner[-1], self))
        self.owner.append(self)

        self.notes: List[str] = []
        self.__pretty_name = None

        # Disable tracing
        # Tracing usage also in: abastract/Electrical/__init__.py
        setprofile(None)

        # Grab name of variable used for instance of this Block
        # Traversal through call stack frames for search the same instance
        deph = 0
        ref: str = None
        while ref is None:
            frame = _getframe(deph)
            context = inspect_code(self, frame)
            ref = context['ref']

            if context.get('comment_line_start', None) is not None:
                self.notes = inspect_comments(
                    context['source'],
                    context['comment_line_start'],
                    context['comment_line_end'])

            self.context = {
                'caller': context['caller'],
                'code': context['code']
            }

            deph += 1

        # Assign passed or assigned property to Block
        arguments = getattr(self, 'arguments', {})
        default_arguments = getattr(self, 'defaults', {})
#        if hasattr(self, 'spice_params'):
#            default_arguments = { **default_arguments, **{ k: v['value']
#                                                          for k, v in self.spice_params.items()}}
        arguments = parse_arguments(arguments, kwargs, default_arguments)
        for prop, value in arguments.items():
            setattr(self, prop, value)

        # Default V and Load from caller Block
        caller = self.context['caller']
        if not kwargs.get('V', False) and (hasattr(caller, 'V')
                                           or ref.get('V', None)):
            V_parent = ref.get('V', caller and caller.V)
            self.V = kwargs['V'] = V_parent

        if not kwargs.get('Load', False) and hasattr(caller, 'Load'):
            self.Load = kwargs['Load'] = caller.Load

        # Do all building routines
        self.mount(*args, **kwargs)

        # Some difference in arguments saving
        for arg in arguments.keys():
            is_default_argument_method = isinstance(getattr(self, arg), FunctionType)
            is_passed_argument_method = isinstance(kwargs.get(arg, None), FunctionType)

            if hasattr(self, arg) and is_default_argument_method:
                value = getattr(self, arg)(self)
                setattr(self, arg, value)
            elif is_passed_argument_method:
                value = kwargs[arg](self)
                setattr(self, arg, value)

    def __str__(self):
        if hasattr(self, '__pretty_name'):
            return self.__pretty_name

        name: List[str] = []
        for word in getattr(self, 'name', '').split('.'):
            name.append(word.capitalize())

        for key, value in getattr(self, 'mods', {}).items():
            # TODO: Fix hack for network mod
            if key == 'port':
                continue

            name.append(' '.join([key.capitalize()] + [str(el).capitalize()
                                                       for el in value]))

        block_name: str = codenamize(id(self), 0)
        name.append('#' + block_name)

        self.__pretty_name = ' '.join(name)

        return self.__pretty_name

    def __repr__(self):
        return str(self)

    def willMount(self):
        pass

    def mount(self, *args, **kwargs):
        # Last class is object
        classes = getattr(self, 'classes', [])
        classes = classes[:-1]
        # FIXME: Clear builder duplicates
        classes = [cls for cls in classes if 'builder' not in str(cls)]
        # Call .willMount from all inherited classes
        for cls in classes:
            if hasattr(cls, 'willMount'):
                mount_args_keys = getargspec(cls.willMount).args
                mount_kwargs = kwargs.copy()
                if len(mount_args_keys) == 1:
                    args = []

                mount_args = {key: value for key, value in mount_kwargs.items()
                              if key in mount_args_keys}
                cls.willMount(self, *args, **mount_args)

        if DEBUG:
            self.log(' ; '.join([key + '=' + str(getattr(self, key))
                                 for key, value in kwargs.items()]))

    def release(self):
        self.owner.pop()

        if DEBUG:
            self.log(block_params(self) + '\n')

    def finish(self):
        pass

    def error(self, raise_type, message):
        self.log(message)
        raise raise_type(message)

    def log(self, message, *args):
        if not DEBUG:
            return

        # Get the previous frame in the stack, otherwise it would
        # be this function
        func = currentframe().f_back.f_code
        anchor = "[%s:%i:%s] - " % (
            path.basename(path.dirname(func.co_filename)) + '/' + path.basename(func.co_filename),
            func.co_firstlineno,
            func.co_name
        )

        log.info(("%30s" % anchor) + str(self) + ' - ' + str(message), *args)

