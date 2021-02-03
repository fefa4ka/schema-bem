![](logo.svg)

# schema-bem
`schema-bem` is a Python library on top of [skidl](https://github.com/xesscorp/skidl) for building electronic circuits using [BEM](https://en.bem.info/) (Block, Element, Modifier) methodology.

The idea behind it is to divide the electronic circuit into independent blocks.

* **Declarative**: `schema-bem` makes it painless to create electronic schematics. Design simple blocks for each subsystem in your device, and compose system using this functional components. The declarative definition makes your schematic simpler to understand and easier to modify.
* **Component-Based**: Build encapsulated components that manage their properties, then compose them to make complex devices. Since component logic is written in Python instead of graphic schematics, you can easily pass rich data through your components and control valuable parameters.

Programmed circuits could be exported to:
* Netlist for PCB routing (KiCAD Pcbnew)
* SPICE simulation
* Graphic schematics

## Credits
This software uses the following open source packages:
* [Python 3](https://www.python.org/)
* [skidl](https://github.com/xesscorp/skidl) for describing the interconnection of electronic circuits
* [PySpice](https://github.com/FabriceSalvaire/PySpice) and [ngspice](http://ngspice.sourceforge.net/) for simulation
* KiCAD [symbols](https://github.com/KiCad/kicad-symbols) and [footprints](https://github.com/KiCad/kicad-footprints) for schematics and PCB routing

## Installation
```
pip3 install https://github.com/fefa4ka/schema-bem
```

## Usage Example

Use following structure for blocks storage:
```
blocks/
    category/
        SimpleBlock/
            __init__.py
        ComplexBlock/
            _mod/
                minimal.py
                cheap.py
                extended.py
```

Define `ComplexBlock/__init__.py`:
```
from bem import Block, u_V, u_s

class Block:
    def willMount(self, someArg):
        # some params preparation
```

Define modificator for `ComplexBlock/_mod/minimal.py`:
```
class Modificator:
    def willMount(self, extendedArg):
        pass
```

Now you able export and build block:
```
from bem.category import ComplexBlock

block = ComplexBlock(mod='minimal')(
    someArg='hello', 
    extendedArg='world'
)

```

### More Examples
[Complete library](https://github.com/fefa4ka/schema-library) of complex electronics blocks based on "Art of Electronics" book.



