import importlib
import logging
from collections import defaultdict
from pathlib import Path
import inspect

from bem import Net

from bem import Block, Build, u_s
from .util import get_arg_units, get_minimum_period

from .simulator import Simulate, set_spice_enviroment

import builtins

BLOCKS_PATH = 'blocks'

test_body_kit = [{
    'name': 'basic.RLC',
    'mods': {
        'series': ['R']
    },
    'args': {
        'R_series': {
            'value': 1000,
            'unit': {
                'name': 'ohm',
                'suffix': 'Ω'
            }
        }
    },
    'pins': {
        'input': ['output'],
        'output': ['gnd']
    }
}, {
    'name': 'basic.source.VS',
    'mods': {
        'flow': ['SINEV']
    },
    'args': {
        'V': {
            'value': 12,
            'unit': {
                'name': 'volt',
                'suffix': 'V'
            }
        },
        'frequency': {
            'value': 60,
            'unit': {
                'name': 'herz',
                'suffix': 'Hz'
            }
        }
    },
    'pins': {
        'input': ['input'],
        'output': ['gnd']
    }
}]


class Test:
    builder = None
    block = None

    def __init__(self, builder):
        set_spice_enviroment()

        self.builder = builder

    def cases(self):
        methods = inspect.getmembers(self, predicate=inspect.ismethod)
        methods = [method for method in methods if method[0][0].isupper()]
        cases = {}

        for name, method in methods:
            cases[name] = [arg for arg in inspect.getargspec(method).args if arg not in ['self', 'args']]

        return cases

    def description(self, method):
        description = getattr(self, method).__doc__.strip()

        return description

    # Load configuration
    def body_kit(self):
        body_kit = self._body_kit if hasattr(self, '_body_kit') and self._body_kit else test_body_kit

        return body_kit

    def body_kit_circuit(self):
        for index, body_kit in enumerate(self.body_kit()):
            mods = {}
            if body_kit.get('mods', None):
                mods = body_kit['mods']

            ref = body_kit['name'].split('.')[-1] + '_' + str(index)
            print("\nBody Kit Create")
            LoadBlock = Build(body_kit['name'], **mods, ref=ref).block
            args = LoadBlock.parse_arguments(body_kit['args'])
            print(args, index, body_kit)
            Load = LoadBlock(**args)

            for body_kit_pin in body_kit['pins'].keys():
                for pin in body_kit['pins'][body_kit_pin]:
                    Load_pin = getattr(Load, body_kit_pin)
                    Load_pin += getattr(self.block, pin)

    # Circuit for simulation
    def circuit(self, args):
        props = self.builder.parse_arguments(args)
        self.block = self.builder(**props)

        gnd = Net('0')
        gnd.fixed_name = True
        self.block.gnd += gnd

        self.body_kit_circuit()

    def simulate(self, args, end_time=None, step_time=None):
        self.circuit(args)

        if not (end_time and step_time):
            period = get_minimum_period(self.body_kit())
            end_time = period * 4
            step_time = period / 50

        simulation = Simulate(self.block)
        data = simulation.transient(end_time=end_time @ u_s, step_time=step_time @ u_s)

        return {
            'data': data,
            'circuit': str(simulation.circuit),
            'erc': simulation.ERC
        }


def BuildTest(Block, *args, **kwargs):
        name = Block.name
        mods = {}
        tests = []

        block_dir = name.replace('.', '/')

        base_file = Path(BLOCKS_PATH) / block_dir / ('__init__.py')
        base = base_file.exists() and importlib.import_module(BLOCKS_PATH + '.' + name).Base

        base_test = Path(BLOCKS_PATH) / block_dir / ('test.py')
        BaseTest = base_test.exists() and importlib.import_module(BLOCKS_PATH + '.' + name + '.test')
        if BaseTest:
            tests.append(BaseTest.Case)
        elif name.find('.') != -1:
            parent = name.split('.')[0]
            base_test = Path(BLOCKS_PATH) / parent / ('test.py')
            BaseTest = base_test.exists() and importlib.import_module(BLOCKS_PATH + '.' + parent + '.test')
            if BaseTest:
                tests.append(BaseTest.Case)

        if base:
            for mod, value in kwargs.items():
                if type(value) == list:
                    mods[mod] = value
                else:
                    value = str(value)
                    mods[mod] = value.split(',')

            for mod, value in base.mods.items():
                if not mods.get(mod, None):
                    mods[mod] = value

            for mod, values in mods.items():
                if type(values) != list:
                    values = [str(values)]

                for value in values:
                    test_file = Path(BLOCKS_PATH) / block_dir / ('_' + mod) / (value + '_test.py')
                    if test_file.exists():
                        ModTest = importlib.import_module(BLOCKS_PATH + '.' + name + '._' + mod + '.' + value + '_test')
                        tests.append(ModTest.Case)

        if len(tests):
            Tests = tests
            # Tests.reverse()
            Tests = tuple(set(tests))
        else:
            Tests = (Test,)

        return type(name + 'Test', Tests, {})(Block)
