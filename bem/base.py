import inspect

import re
import sys
from copy import copy
from types import FunctionType
import logging

from PySpice.Unit import FrequencyValue, PeriodValue
from PySpice.Unit.Unit import UnitValue
import re

import builtins

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = logging.FileHandler('bem.log')
log_handler.setFormatter(formatter)
log.addHandler(log_handler)

class Block:
    scope = []
    owner = [None]
    refs = []

    files = ['bem/base.py']
    inherited = []

    doc_methods = ['willMount'] # Methods that used for parameters description extraction

    def parse_argument(self, value):
        if callable(value):
            return value(self)

        return value

    def __init__(self, *args, **kwargs):
        self.log('init')
        self.scope.append((self.owner[-1], self))
        self.owner.append(self)

        sys.setprofile(None)

        # Grab name of variable used for instance of this Block
        # Traversal through call stack frames for search the same instance
        deph = 0
        ref = None
        while ref == None:
            frame = sys._getframe(deph)
            frame_locals = frame.f_locals

            local_self = frame_locals.get('self', None)
            if local_self != self:
                ref = frame_locals
                for key, value in frame_locals.items():
                    if type(self) == type(value) and self == value:
                        ref = key
                        break

                try:
                    code = inspect.getsourcelines(frame.f_code)[0]
                except OSError:
                    # If code runned from shell
                    self.context = {
                        'caller': None,
                        'code': ''
                    }
                    break

                code_line = frame.f_lineno - frame.f_code.co_firstlineno

                self.context = {
                    'caller': frame_locals.get('self', None),
                    'code': code[code_line]
                }

                parentheses_open_pos = self.context['code'].find('(')
                parentheses_close_pos = self.context['code'].find(')')

                # In code there aren't method call, lookup code for local variable
                code_part = [line.replace(' ', '') for line in code[0:code_line]]
                code_part.reverse()

                if parentheses_open_pos == -1 or (parentheses_open_pos > parentheses_close_pos):
                    local_vars = frame.f_code.co_varnames[1:]

                    for line in code_part:
                        parentheses_open_pos = line.find('(')
                        parentheses_close_pos = line.find(')')

                        # Block constructed from local method
                        if line.find('return') == 0:
                            ref = None
                            break

                        # Block assigned as local variable
                        for var in local_vars:
                            if var + '=' in line:
                                self.context['code'] = line
                                break
                        else:
                            continue

                        break
                    else:
                        self.context['code'] = ''
                elif self.context['code'].find('=') == -1 or self.context['code'].find('return') != -1:
                    for line in code_part:
                        if line.find('def') == 0:
                            self.context['code'] = line[3:line.find('(')] + '=()'
                            break

            deph += 1

        arguments = self.parse_arguments(kwargs)
        for prop in arguments.keys():
            value = arguments[prop]
            setattr(self, prop, value)

        # Default V and Load from caller
        caller = self.context['caller']
        if not kwargs.get('V', False) and hasattr(caller, 'V'):
            self.V = kwargs['V'] = caller.V

        if not kwargs.get('Load', False) and hasattr(caller, 'Load'):
            self.Load = kwargs['Load'] = caller.Load

        self.mount(*args, **kwargs)

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
            return block.ref if not hasattr(block, 'part') and block else ' ' + getattr(block, 'ref', '_')

        blocks = {}

        for pair in Block.scope:
            if issubclass(pair[1].__class__, block_type or Block):
                block = pair[1]
                blocks[block_ref(block)] = block

        return blocks

    @classmethod
    def hierarchy(cls):
        def block_ref(block):
            if not hasattr(block, 'part') and block:
                return block.ref
            else:
                return ' ' + getattr(block, 'ref', '_')

        lst = [(block_ref(item[0]), block_ref(item[1])) for item in Block.scope]
        graph = {name: set() for tup in lst for name in tup}
        has_parent = {name: False for tup in lst for name in tup}
        for parent, child in lst:
            graph[parent].add(child)
            has_parent[child] = True

        # All names that have absolutely no parent:
        roots = [name for name, parents in has_parent.items() if not parents]

        # traversal of the graph (doesn't care about duplicates and cycles)
        def traverse(hierarchy, graph, names):
            for name in names:
                key = name
                if name[0] == ' ':
                    key = name[1:]
                hierarchy[key] = traverse({}, graph, graph[name])
            return hierarchy

        root = traverse({}, graph, roots)
        return root['_'] 

    def mount(self, *args, **kwargs):
        # Last class is object
        classes = list(inspect.getmro(self.__class__))[:-1]
        # Clear builder duplicates
        classes = [cls for cls in classes if 'builder' not in str(cls)]
        classes.reverse()
        # Call .willMount from all inherited classes
        for cls in classes:
            if hasattr(cls, 'willMount'):
                mount_args_keys = inspect.getargspec(cls.willMount).args
                mount_kwargs = kwargs.copy()
                if len(mount_args_keys) == 1:
                    args = []

                mount_args = {key: getattr(self, key) for key, value in mount_kwargs.items() if key in mount_args_keys}
                cls.willMount(self, *args, **mount_args)

    def willMount(self):
        pass

    def release(self):
        self.owner.pop()

    @property
    def SIMULATION(self):
        if hasattr(builtins, 'SIMULATION'):
            return builtins.SIMULATION
        else:
            return False

    def __str__(self):
        name = []
        for key, value in self.mods.items():
            name.append(' '.join([str(el).capitalize() for el in value]) + ' ' + key.capitalize())

        for word in self.name.split('.'):
            name.append(word.capitalize())

        return ' '.join(name)

    def get_description(self):
        """
        From docsting of classes builded from.
        """
        description = []
        for doc in [cls.__doc__ for cls in inspect.getmro(self) if cls.__doc__ and cls != object]:
            doc = '\n'.join([line.strip() for line in doc.split('\n')])
            description.append(doc)

        return description

    def get_params_description(self):
        """
        Get documentation from docstring of methods in `self.doc_methods` using pattern 'some_arg -- description'
        """
        def is_proper_cls(cls):
            if cls == object:
                return False

            for method in self.doc_methods:
                if hasattr(cls, method) and cls.willMount.__doc__:
                    return True

            return False

        def extract_doc(cls):
            doc = ''

            for method in self.doc_methods:
                doc_str = hasattr(cls, method) and cls.willMount.__doc__
                if doc_str:
                    doc += doc_str

            return doc

        params = {}

        docs = [extract_doc(cls) for cls in inspect.getmro(self) if is_proper_cls(cls) ]
        docs.reverse()

        for doc in docs:
            terms = [line.strip().split(' -- ') for line in doc.split('\n') if len(line.strip())]
            for term, description in terms:
                params[term.strip()] = description.strip()

        return params


    # Virtual Part
    @classmethod
    def get_default_arguments(cls):
        args = []
        defaults = {}

        classes = []
        try:
            classes += list(inspect.getmro(cls))
        except:
            pass

        classes += list(inspect.getmro(cls.__class__))

        classes.reverse()
        for cls in classes:
            if hasattr(cls, 'willMount'):
                args += inspect.getargspec(cls.willMount).args
                signature = inspect.signature(cls.willMount)
                defaults = { **defaults,
                         **{
                            k: v.default
                            for k, v in signature.parameters.items()
                        }
                }

        args = list(set([arg for arg in args if arg != 'self']))

        return args, defaults

    def get_arguments(self):
        arguments = {}
        args, defaults = self.get_default_arguments()

        for arg in args:
            default = getattr(self, arg) if hasattr(self, arg) else defaults.get(arg, None)
            if type(default) in [UnitValue, PeriodValue, FrequencyValue]:
                arguments[arg] = {
                    'value': default.value * default.scale,
                    'unit': {
                        'name': default.unit.unit_name,
                        'suffix': default.unit.unit_suffix
                    }
                }
            elif type(default) in [int, float]:
                arguments[arg] = {
                    'value': default,
                    'unit': {
                        'name': 'number'
                    }
                }
            elif type(default) == str:
                arguments[arg] = {
                    'value': default,
                    'unit': {
                        'name': 'string'
                    }
                }
            elif arg == 'Load' and type(default) == list and len(default) > 0:
                default = default[0]

                arguments[arg] = {
                    'value': default.value * default.scale,
                    'unit': {
                        'name': default.unit.unit_name,
                        'suffix': default.unit.unit_suffix
                    }
                }
            elif type(default) == type(None):
                arguments[arg] = {
                    'unit': {
                        'name': 'network'
                    }
                }

        return arguments

    @classmethod
    def parse_arguments(cls, args):
        arguments, defaults = cls.get_default_arguments()
        props = {}
        for attr in arguments:
            props[attr] = copy(defaults.get(attr, None)) #copy(getattr(cls, attr))
            arg = args.get(attr, None)
            if arg:
                if type(arg) == dict:
                    arg = arg.get('value', None)
                if type(props[attr]) in [int, float]:
                    props[attr] = float(arg)
                #elif type(props[attr]) in [str, bool]:
                #    props[attr] = arg
                # elif type(props[attr]) == list:
                #    props[attr] = props[attr][0]
                # elif isinstance(arg, Block):
                #     props[attr] = arg
                # elif isinstance(arg, FunctionType):
                #     props[attr] = arg
                elif type(props[attr]) in [UnitValue, PeriodValue, FrequencyValue]:
                    if type(arg) in [UnitValue, PeriodValue, FrequencyValue]:
                        props[attr] = arg
                    else:
                        props[attr]._value = float(arg)
                else:
                    props[attr] = arg

        return props


    def get_ref(self):
        """
        Ref extracted from code variable name
        """
        name = self.ref if hasattr(self, 'ref') and self.ref else self.name
        name = name.split('.')[-1]
        code = self.context['code']

        assign_pos = code.find('=')
        and_pos = code.find('&')
        or_pos = code.find('|')
        parentheses_pos = code.find('(')
        ref = code[:assign_pos].strip().replace('self', '')
        ref = re.sub("[\(\[].*?[\)\]]", "", ref)
        ref = re.sub('[(){}<>]', '', ref)
        ref = ref.strip().capitalize()
        value = code[assign_pos:]
        ref = ''.join([word.capitalize() for word in ref.replace('_', '.').split('.')])

        if assign_pos > parentheses_pos:
            ref = name

        if assign_pos == -1 or code.find('return') != -1 or (and_pos != -1 and assign_pos > and_pos) or (or_pos != -1 and assign_pos > or_pos) or value == code:
            ref = name

        if self.context['caller'] and hasattr(self.context['caller'], 'name'):
            block_name = self.context['caller'].ref.split('.')[-1]
            if block_name not in ref:
                ref = block_name + '_' + ref

        return ref


    def get_params(self):
        params_default = inspect.getmembers(self, lambda a: not (inspect.isroutine(a)))

        # from PySpice.Unit import u_W, u_A, u_Ohm
        # params = [('units', ''),
        #           ('P', 1 @ u_W), ('I', 1 @ u_A), ('Z', 1 @ u_Ohm)]

        # params_default += params 

        params = {}
        for param, default in params_default:
            if param in inspect.getargspec(self.willMount).args:# or arguments.get(param, None):
                continue

            if type(default) in [UnitValue, PeriodValue, FrequencyValue]:
                default = default.canonise()
                params[param] = {
                    'value': round(default.value, 1),
                    'unit': {
                        'name': default.unit.unit_name,
                        'suffix': default.prefixed_unit.str() #unit.unit_suffix
                    }
                }
            elif type(default) in [int, float]:
                params[param] = {
                    'value': default if type(default) == int else round(default, 3),
                    'unit': {
                        'name': 'number'
                    }
                }
            elif type(default) == str and param not in ['name', '__module__']:
                params[param] = {
                    'value': default,
                    'unit': {
                        'name': 'string'
                    }
                }

        return params

    @classmethod
    def log(cls, message, *args):
        log.info(hex(id(cls)) + ' ' + cls.name + ': ' + message, *args)
