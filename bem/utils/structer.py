from importlib import import_module
from os import getenv
from os.path import dirname
from pathlib import Path
from inspect import getmro
from skidl import Part

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
                    **mods,
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

def hierarchy_joined(Block):
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

            key_scope = list(hierarchy[key].keys())
            if len(key_scope) == 0 or (len(key_scope) == 1 and key_scope[0] == key):
                hierarchy[key] = ''

        return hierarchy

    root = traverse({}, graph, roots)

    return root['_']


def contents(Block):
    def block_ref(block):
        if not hasattr(block, 'part') and block:
            return block.ref
        else:
            return ' ' + getattr(block, 'ref', '_')

    lst = []
    parts = {}

    for builder, entry in Block.scope:
        lst.append((block_ref(builder), block_ref(entry)))
        if isinstance(entry, Part):
            parts[block_ref(entry)] = entry

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
            key_scope = list(hierarchy[key].keys())

            # If in scope only element with the same name
            if len(key_scope) == 0 or (len(key_scope) == 1 and key_scope[0] == key):
                # There are empty structure if no mods for block selected
                if key in parts: 
                    hierarchy[key] = parts[key]

            if len(key_scope) > 1:
                # Join lonely parts with first most related heap
                moved = []
                for sub_key, value in hierarchy[key].items():
                    if isinstance(value, Part):
                        related = related_heap(hierarchy[key], value)

                        if related:
                            hierarchy[key][related][sub_key] = value
                            moved.append(sub_key)

                for sub_key in moved:
                    del hierarchy[key][sub_key]

        return hierarchy

    root = traverse({}, graph, roots)



    return root['_']

def related_heap(scope, part):
    pins_number = len(part.pins)
    most_connected_heap = None
    most_connected_heap_pins = []

    for key, heap in scope.items():
        if isinstance(heap, dict):
            connected_pins = connected_pins_to_heap(heap, part)
            if len(connected_pins) > len(most_connected_heap_pins):
                most_connected_heap = key
                most_connected_heap_pins = connected_pins

            if len(connected_pins) == pins_number:
                return most_connected_heap

    return most_connected_heap


def connected_pins_to_heap(heap, part):
    connected_pins = []
    for pin in part.pins:
        connected = False
        if pin in connected_pins:
            break

        for key, value in heap.items():
            if isinstance(value, dict):
                value_conneted_pins = connected_pins_to_heap(value, part)
                connected_pins += value_conneted_pins
                connected_pins = list(set(connected_pins))

                if pin in value_conneted_pins:
                    connected = True
                    break
            else:
                for related_pin in value.pins:
                    if pin.is_attached(related_pin):
                        connected = True
                        connected_pins.append(pin)
                        break

            if connected:
                break

    return connected_pins
