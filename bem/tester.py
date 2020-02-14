import importlib
import logging
from collections import defaultdict
from pathlib import Path
import inspect

from bem import Net

from bem import Block, Build, u_s
from .util import get_arg_units, get_minimum_period
from settings import BLOCKS_PATH, test_body_kit, test_sources

from .simulator import Simulate, set_spice_enviroment

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

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

    # Signal source configuration

    # def sources(self):
    #     # sources = test_sources
    #     sources = self._sources if hasattr(self, '_sources') and self._sources else test_sources

    #     gnd = ['gnd']
    #     if len(self.body_kit()) == 0:
    #         gnd.append('output')

    #     sources[0]['pins']['n'] = gnd

    #     return sources

    # def sources_circuit(self):
    #     sources =  self.sources()
    #     series_sources = defaultdict(list)
    #     series_sources_allready = []

    #     periods = []  # frequency, time, delay, duration
        
    #     # Get Series Source with same input
    #     for source in sources:
    #         pins = source['pins'].keys()
    #         hash_name = str(source['pins']['p']) + str(source['pins']['n'])
        
    #         for source_another_index, source_another in enumerate(sources):
    #             is_same_connection = True
    #             for source_pin in pins:
    #                 for index, pin in enumerate(source['pins'][source_pin]):
    #                     if source_another['pins'][source_pin][index] != pin:
    #                         is_same_connection = False
    #                         break
                
    #             if is_same_connection and source_another_index not in series_sources_allready:
    #                 series_sources_allready.append(source_another_index)
    #                 series_sources[hash_name].append(source_another)

        
    #     for series in series_sources.keys():
    #         last_source = None

    #         for source in series_sources[series]:
    #             part_name = source['name'].split('_')[0]
    #             # part = get_part(part_name)
    #             part = Build(part_name).spice
    #             args = {}
    #             for arg in source['args'].keys():
    #                 if source['args'][arg]['value']:
    #                     try: 
    #                         args[arg] = float(source['args'][arg]['value']) @ get_arg_units(part, arg)
    #                     except:
    #                         try:
    #                             args[arg] = float(source['args'][arg]['value'])
    #                             if args[arg] == int(source['args'][arg]['value']):
    #                                 args[arg] = int(args[arg])
    #                         except:
    #                             args[arg] = source['args'][arg]['value'] 

    #             signal = Build(part_name).spice(ref='V' + source['name'], **args)

    #             if not last_source:
    #                 for pin in source['pins']['n']:
    #                     signal['n'] += getattr(self.block, pin)
    #             else:
    #                 last_source['p'] += signal['n']

    #             last_source = signal
            
    #         for pin in source['pins']['p']:
    #             signal['p'] += getattr(self.block, pin)

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
            LoadBlock = Build(body_kit['name'], **mods, ref=ref).block
            args = LoadBlock.parse_arguments(body_kit['args'])
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
