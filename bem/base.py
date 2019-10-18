import inspect
import logging

from PySpice.Unit import FrequencyValue, PeriodValue
from PySpice.Unit.Unit import UnitValue
from copy import copy
from types import FunctionType
import inspect
import sys
import re

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

logger = logging.getLogger(__name__)


class Block:
    name = ''
    mods = {}
    props = {}

    files = []
    inherited = []

    doc_methods = ['willMount']

    def parse_argument(self, value):
        if callable(value):
            return value(self)

        return value

    def __init__(self, *args, **kwargs):
        sys.setprofile(None)

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

                self.context = {
                    'caller': frame_locals.get('self', None),
                    'code': inspect.getsourcelines(frame.f_code)[0][frame.f_lineno - frame.f_code.co_firstlineno]
                }

            deph += 1

        for prop in kwargs.keys():
            if hasattr(self, prop):
                setattr(self, prop, kwargs[prop])

        self.mount(*args, **kwargs)

    def mount(self, *args, **kwargs):
        def uniq_f7(seq):
            seen = set()
            seen_add = seen.add
            return [x for x in seq if not (x in seen or seen_add(x))]

        classes = list(inspect.getmro(self.__class__))
        classes.reverse()
        classes = uniq_f7(classes)
        for cls in classes:
            if hasattr(cls, 'willMount'):
                mount_args_keys = inspect.getargspec(cls.willMount).args

                for arg in mount_args_keys:
                    if hasattr(self, arg) and isinstance(getattr(self, arg), FunctionType):
                        value = getattr(self, arg)(self)
                        setattr(self, arg, value)
                        kwargs[arg] = value
                    elif isinstance(kwargs.get(arg, None), FunctionType):
                        kwargs[arg] = kwargs[arg](self)

                mount_args = {key: value for key, value in kwargs.items() if key in mount_args_keys}


                cls.willMount(self, *args, **mount_args)

    def willMount(self):
        pass

    # Title and Description
    # def __instance__name__(self):
    #     return [k for k,v in globals().items() if v is self]
    @property
    def SIMULATION(self):
        if hasattr(builtins, 'SIMULATION'):
            return builtins.SIMULATION
        else:
            return False

    def __str__(self):
        body = [self.name]
        for key, value in self.mods.items():
            body.append(key + ' = ' + str(value))

        return '\n'.join(body)

    def title(self):
        # input = self.input
        # output = self.output

        # input_name = f'{input.part.name}_{input.name}' if hasattr(input, 'part') else f'{input.name}' if input else "NC"
        # output_name = f'{output.part.name}_{output.name}' if hasattr(output, 'part') else f'{output.name}' if output else "NC"

        # input_name = input_name.replace(self.name, '')
        # output_name = output_name.replace(self.name, '')

        # return label_prepare(input_name) + ' ⟶ ' + self.name + ' ⟶ ' + label_prepare(output_name)
        return self.name

    def get_description(self):
        description = []
        for doc in [cls.__doc__ for cls in inspect.getmro(self) if cls.__doc__ and cls != object]:
            doc = '\n'.join([line.strip() for line in doc.split('\n')])
            description.append(doc)

        return description

    def get_params_description(self):
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
    def get_arguments(self):
        # Instance = self if isinstance(self, type(self)) else self.__class__
        arguments = {}
        args = []

        classes = []
        try:
            classes += list(inspect.getmro(self))
        except:
            pass

        classes += list(inspect.getmro(self.__class__))

        classes.reverse()
        for cls in classes:
            if hasattr(cls, 'willMount'):
                args += inspect.getargspec(cls.willMount).args

        for arg in args:
            if arg in ['self']:
                continue

            default = getattr(self, arg)
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
                # arguments[arg] = {
                #     'value': default.value * default.scale
                #     'unit': {
                #         'name': default.unit.unit_name,
                #         'suffix': default.unit.unit_suffix
                #     }
                # }
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
    def parse_arguments(self, args):
        arguments = self.get_arguments(self)
        props = {}
        for attr in arguments:
            props[attr] = copy(getattr(self, attr))
            if type(props[attr]) == list:
                props[attr] = props[attr][0]
            arg = args.get(attr, None)
            if arg: 
                if type(arg) == dict:
                    arg = arg.get('value', None)
                if type(props[attr]) in [int, float]:
                    props[attr] = float(arg)
                elif type(props[attr]) == str:
                    props[attr] = arg
                elif type(props[attr]) == list:
                    props[attr] = props[attr][0]
                elif isinstance(arg, Block):
                    props[attr] = arg
                elif not type(props[attr]) == type(None):
                    props[attr]._value = float(arg)

        return props


    def get_ref(self):
        name = self.name.split('.')[-1]
        code = self.context['code']

        assign_pos = code.find('=')
        and_pos = code.find('&')
        or_pos = code.find('|')
        ref = code[:assign_pos].strip().replace('self', '')
        ref = re.sub("[\(\[].*?[\)\]]", "", ref).strip()
        ref = ref.capitalize()
        value = code[assign_pos:]
        ref = ''.join([word.capitalize() for word in ref.replace('_', '.').split('.')])

        if assign_pos == -1 or code.find('return') != -1 or (and_pos != -1 and assign_pos > and_pos) or (or_pos != -1 and assign_pos > or_pos) or value == code:
            ref = name

        if self.context['caller'] and hasattr(self.context['caller'], 'name'):
            ref = self.context['caller'].name.split('.')[-1] + '_' + ref

        return ref


    def get_params(self):
        params_default = inspect.getmembers(self, lambda a: not (inspect.isroutine(a)))

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
            elif type(default) == str and param not in ['title', 'name', '__module__']:
                params[param] = {
                    'value': default,
                    'unit': {
                        'name': 'string'
                    }
                }

        return params

    def log(self, message):
        logger.info(self.title() + ' - ' + str(message))


