from importlib import import_module
from os import getenv
from os.path import dirname
from pathlib import Path
from inspect import getmro

def bem_blocks_path():
    module_path = dirname(__file__)
    blocks_path = str(Path(module_path).parent / Path('blocks'))

    return blocks_path

def lookup_block_class(name, libraries=[]):
    bem_blocks = bem_blocks_path()
    libraries += getenv('BEM_LIBRARIES') or ['blocks']
    libraries.append(bem_blocks)

    block_dir = name.replace('.', '/')
    base_file = block_class = module_path = None

    for lib in libraries:
        base_file = Path(lib) / block_dir / ('__init__.py')

        if base_file.exists():
            if lib == bem_blocks:
                module_path = 'bem.blocks'
            else:
                module_path = lib

            break


    if base_file and base_file.exists():
        block_class = import_module(module_path + '.' + name).Base
    else:
        return None, None

    return base_file, block_class


def mods_from_dict(kwargs):
    mods = {}

    for mod, value in kwargs.items():
        if isinstance(value, list):
            mods[mod] = value
        else:
            if isinstance(value, str):
                value = value.split(',')
            else:
                value = [value]

            mods[mod] = value

    return mods

def mods_predefined(base):
    mods = {}

    classes = list(getmro(base))[:-1]
    # Clear builder duplicates
    classes = [cls for cls in classes if 'builder' not in str(cls)]
    classes.reverse()

    if hasattr(classes, 'mods'):
        for mod, value in base.mods.items():
            if not mods.get(mod, None):
                mods[mod] = value

    return mods

def lookup_mod_classes(name, selected_mods, libraries=[]):
    bem_blocks = bem_blocks_path()
    libraries += getenv('BEM_LIBRARIES') or ['blocks']
    libraries.append(bem_blocks)

    block_dir = name.replace('.', '/')
    mod_file = module_path = None
    classes = []
    files = []
    mods = {}

    for mod, values in selected_mods.items():
        if not isinstance(values, list):
            values = [str(values)]

        for value in values:
            for lib in libraries:
                mod_file = Path(lib) / block_dir / ('_' + mod) / (str(value) + '.py')
                if mod_file.exists():
                    if lib == bem_blocks:
                        module_path = 'bem.blocks'
                    else:
                        module_path = lib

                    break

            if mod_file and mod_file.exists():
                mod_file = Path(lib) / block_dir / ('_' + mod) / (str(value) + '.py')
                Module = import_module(module_path + '.' + block_dir.replace('/', '.') + '._' + mod + '.' + value)
                classes.append(Module.Modificator)

                if hasattr(Module.Modificator, 'files'):
                    files += Module.Modificator.files
                    files.append(str(mod_file))

                instance_mods = Module.Modificator.mods if hasattr(Module.Modificator, 'mods') else {}
                mods = {
                    **instance_mods,
                    mod: values
                }


    return files, classes, mods


def hierarchy(Block):
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