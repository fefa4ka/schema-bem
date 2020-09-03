import builtins
import inspect
import logging
import re
import sys
from os import path
from copy import copy
from types import FunctionType

from PySpice.Unit import FrequencyValue, PeriodValue
from PySpice.Unit.Unit import UnitValue
from .utils import uniq_f7
from .utils.parser import inspect_code, inspect_comments, inspect_ref, block_params_description
from .utils.args import value_to_strict, value_to_round, default_arguments, parse_arguments
from .utils.logger import block_definition

from codenamize import codenamize

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
log_handler = logging.FileHandler('bem.log')
log_handler.setFormatter(formatter)
log.addHandler(log_handler)


class Block:
    # Reference to global BEM scope
    scope = []

    # Current active block
    owner = [None]
    refs = []

    # Sources used in block building
    files = ['bem/base.py']

    # Inherited block classes
    # Another block could be inherited in different maniere:
    # * Inherit certain modification `class SomeBlock(InheritedBlock(mod='certain'))`
    # * inherited prop add ability to use any iherited modification
    inherited = []

    # Methods that used for parameters description extraction
    doc_methods = ['willMount', 'circuit']

    def __init__(self, *args, **kwargs):
        self.log(block_definition(self, args, kwargs))

        # Build scope 
        # Previous block, if they didn't release, owner of current
        self.scope.append((self.owner[-1], self))
        self.owner.append(self)

        self.notes = []

        # Disable tracing
        # Tracing usage also in: abastract/Electrical/__init__.py
        sys.setprofile(None)

        # Grab name of variable used for instance of this Block
        # Traversal through call stack frames for search the same instance
        deph = 0
        ref = None
        while ref == None:
            frame = sys._getframe(deph)
            context = inspect_code(self, frame)
            ref = context['ref']

            if hasattr(context, 'comment_line_start'):
                self.notes = inspect_comments(
                    context['source'],
                    context['comment_line_start'],
                    context['comment_line_end'])

            self.context = {
                'caller': context['caller'],
                'code': context['code']
            }

            deph += 1

        arguments = parse_arguments(self.arguments, kwargs, self.defaults)
        for prop, value in arguments.items():
            setattr(self, prop, value)

        # Default V and Load from caller Block
        caller = self.context['caller']
        if not kwargs.get('V', False) and hasattr(caller, 'V'):
            self.V = kwargs['V'] = caller.V

        if not kwargs.get('Load', False) and hasattr(caller, 'Load'):
            self.Load = kwargs['Load'] = caller.Load

        # Do all building routines
        self.mount(*args, **kwargs)

        # Some difference in arguments saving  
        for arg in arguments.keys():
            if hasattr(self, arg) and isinstance(getattr(self, arg), FunctionType):
                value = getattr(self, arg)(self)
                setattr(self, arg, value)
            elif isinstance(kwargs.get(arg, None), FunctionType):
                value = kwargs[arg](self)
                setattr(self, arg, value)

    @classmethod
    def created(cls, block_type=None):
        def block_ref(block):
            return block.ref #if not hasattr(block, 'part') and block else ' ' + getattr(block, 'ref', '_')

        blocks = {}

        for pair in Block.scope:
            if issubclass(pair[1].__class__, block_type or Block):
                block = pair[1]
                blocks[block.ref] = block

        return blocks

    def mount(self, *args, **kwargs):
        # Last class is object
        classes = self.classes[:-1]
        # Clear builder duplicates
        classes = [cls for cls in classes if 'builder' not in str(cls)]
        # Call .willMount from all inherited classes
        for cls in classes:
            if hasattr(cls, 'willMount'):
                mount_args_keys = inspect.getargspec(cls.willMount).args
                mount_kwargs = kwargs.copy()
                if len(mount_args_keys) == 1:
                    args = []

                mount_args = {key: value for key, value in mount_kwargs.items() if key in mount_args_keys}
                cls.willMount(self, *args, **mount_args)

        params = self.get_params()

        self.log(', '.join([key + ' = ' + str(getattr(self, key)) for key, value in kwargs.items()]))

    def willMount(self):
        pass

    def release(self):
        self.owner.pop()

        params = self.get_params()
        self.log(', '.join([key + ' = ' + str(value['value']) + ' ' + value['unit'].get('suffix', '') for key, value in params.items()]) + '\n')

    def finish(self):
        pass

    def __str__(self):
        name = []
        for key, value in self.mods.items():
            #] TODO: Fix hack for network mod
            if key == 'port':
                continue

            name.append(' '.join([str(el).capitalize() for el in value]) + ' ' + key.capitalize())

        for word in self.name.split('.'):
            name.append(word.capitalize())

        return ' '.join(name)

    def get_arguments(self):
        arguments = {}
        description = block_params_description(self)

        for arg in self.arguments:
            default = getattr(self, arg) if hasattr(self, arg) else self.defaults.get(arg, None)
            is_list = arg == 'Load' and isinstance(default, list) and len(default) > 0
            if is_list:
                default = default[0]

            value = value_to_strict(default)
            if value:
                arguments[arg] = value
            if description.get(arg, None) and arguments.get(arg, None):
                arguments[arg]['description'] = description[arg]

        return arguments

    def get_ref(self):
        """
        Ref extracted from code variable name
        """
        name = self.ref if hasattr(self, 'ref') and self.ref else self.name
        name = name.split('.')[-1]

        context = self.context
        ref = inspect_ref(name, context['code'], context['caller']) or name

        return ref

    def get_params(self):
        params_default = inspect.getmembers(self, lambda a: not (inspect.isroutine(a)))

        try:
            description = block_params_description(self)
        except:
            description = block_params_description(self.__class__)

        params = {}
        for param, default in params_default:
            if param in self.arguments or param in ['name', '__module__']:
                continue

            value = value_to_round(default)

            if value:
                params[param] = value

            if description.get(param, None) and params.get(param, None):
                params[param]['description'] = description[param]

        return params

    def error(self, raise_type, message):
        self.log(message)
        raise raise_type(message)

    def log(self, message, *args):
        # Get the previous frame in the stack, otherwise it would
        # be this function
        func = inspect.currentframe().f_back.f_code
        anchor = "[%20s:%3i:%15s] - " % (
            path.basename(path.dirname(func.co_filename)) + '/' + path.basename(func.co_filename),
            func.co_firstlineno,
            func.co_name
        )
        block_name = codenamize(id(self), 0)

        log.info(anchor + self.name + '_' + block_name + ': ' + str(message), *args)

