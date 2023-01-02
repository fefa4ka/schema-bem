![](logo.svg)

# schema-bem

`schema-bem` is a Python library built on top of `skidl` that allows you to design and layout electronic circuits for printed circuit boards using the **BEM** (Block, Element, Modifier) methodology. BEM is a methodology that introduces terms for defining components: blocks, elements, and modifiers.

In circuit design, abstractions or black boxes allow you to _hide complexities_ and operate only with input data, transform function, and result, excluding implementation details from analysis. Abstract models are useful for planning, high-level design, and the calculation of parameters of electronic circuits with specific physical components.

In the context of electrical circuits and the `schema-bem` library, the following levels of abstraction have been formed:

-   `base.py`: The base class ensures the functionality of the BEM methodology, including the declarative and parametric approach.
-   `abstract.Electrical`: The electrical abstraction processes electrical characteristics, provides simulation and compilation of the circuit.
-   `abstract.Network`: The network abstraction handles connections of blocks of different topologies.
-   `abstract.Physical`: The physical abstraction selects the appropriate real component from the available options.

## Key Features

-   **Declarative design**: schema-bem makes it easy to create electronic schematics by allowing you to design simple blocks for each subsystem in your device, and then compose your system using these functional components. The declarative definition makes your schematic simpler to understand and easier to modify.
-   **Component-based**: schema-bem allows you to build encapsulated components that manage their own properties, and then compose them to create complex devices. Since the component logic is written in Python instead of graphic schematics, you can easily pass rich data through your components and control valuable parameters.
-   **Export options**: Programmed circuits created with schema-bem can be exported to a variety of formats, including netlist for PCB routing (**KiCAD Pcbnew**), **SPICE** simulation, and **graphic schematics**.

## BEM Concept in Circuit Design

### Voltage Divider

Let’s build a simple voltage divider scheme and illustrate the search for suitable terminology for the name of the abstraction, modifiers, and parameters.

We could create a block by calling `Divider(type='resistive')`, where `type` defines the use of resistors as impedance. Using the parametric approach, we can specify the input voltage `V`, the desired output voltage `V_out`, and the desired current `Load`. For example:

```python
stiff = Divider(type='resistive')(
V=10 @ u_V,
V_out=3 @ u_V,
Load=1 @ u_mA
)
```

The block will automatically calculate the necessary parameters of the components (resistance, permissible power, etc.) to create a voltage divider from the input to the output voltage.

### Voltage Regulator

Regulator is a block that can be implemented using various components, such as a zener diode `Regulator(via='zener')` or an integrated circuit `Regulator(via='ic')`.

For reliable operation, you can add a filter and let the current flow through a transistor `Regulator(via='zener', stability=['lowpass', 'bipolar'])`.

Using the parametric approach, we can specify the input voltage `V`, the desired output voltage `V_out`, and the maximum current Load that the regulator should be able to handle. For example:

```python
Vcc = Regulator(via=‘ic’)(
V=20 @ u_V,
V_out=10 @ u_V,
Load=0.5 @ u_A
```

### Connecting blocks

The connection of the blocks is carried out explicitly and documents itself. Connecting the stable voltage from the regulator to the divider `Vcc & stiff` is simple and inherited from skid.

## Voltage amplifier

Let's add more active components to the scheme.

Connect the transistor `Transistor`, for example, we will use the `npn` type `Transistor(type='npn')'`.

We will make a voltage amplifier, for this purpose a connection with a common emitter is used.

```
amplifier = Transistor(
type='npn',
follow='collector',
common='emitter'
)
```

To amplify the current, you need to make an emitter repeater and connect a resistor `Resistor` with a resistance `R_e` to the emitter.

```python
R_e = 10 @ u_Ohm

amplifier = Transistor(
type='npn',
follow='emitter',
common='emitter'
)(
emitter=Resistor()(R_e)
)
```

We use a simple way of working with abstractions, the output from the voltage divider is connected to the input of the amplifier `stiff & amplifier` simply, while we take into account all the details of the real connection take into account black boxes.

This is enough to make an amplifier unit on the `Amplifier` transistor, which, based on the reference voltage `V_ref`, would amplify the current signal with voltage `V`.

Up to this point, we did not think about and did not choose the physical components that will fall on the circuit.

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

## Credits

This software uses the following open source packages:

-   [Python 3](https://www.python.org/)
-   [skidl](https://github.com/xesscorp/skidl) for describing the interconnection of electronic circuits
-   [PySpice](https://github.com/FabriceSalvaire/PySpice) and [ngspice](http://ngspice.sourceforge.net/) for simulation
-   KiCAD [symbols](https://github.com/KiCad/kicad-symbols) and [footprints](https://github.com/KiCad/kicad-footprints) for schematics and PCB routing
