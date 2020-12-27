const dagre = require('dagre')
const fs = require('fs')
const pcbmodeDefault = require('./pcbmode.json')

const {
   SVGPlotter,
    PCBPlotter,
    Pcb,
} = require("./kicad-utils/js/kicad-utils.js")

const args = process.argv.slice(2)

const netlistFilename = args[0]
const netlist = require(netlistFilename)

const kicadModuleDir = '/Library/Application\ Support/kicad/modules/'

class PCBmm extends Pcb.PCB {
    parseBoardUnits (expected) {
        return this.parseFloat(expected)
    }
}

class PCBmodePlotter extends PCBPlotter {
    plotModuleLayer(mod, layer) {
        for (let edge of mod.graphics) {
            if (edge instanceof Pcb.EdgeModule)
            {
                if (edge.layer == layer) {
                    this.plotEdgeModule(edge, mod);
                }
			}
		}
    }
    getModuleOutline(mod) {
        const outline = {
            width: { min: 0, max: 0 },
            height: { min: 0, max: 0 }
        }
        mod.graphics.forEach(graph => {
            const points = [graph.start, graph.end]
    
            points.forEach(el => {
                if (!el) return
                if (el.x < outline.width.min) outline.width.min = el.x;
                if (el.x > outline.width.max) outline.width.max = el.x;
                if (el.y < outline.height.min) outline.height.min = el.y;
                if (el.y > outline.height.max) outline.height.max = el.y;
            })
        })


        return outline 
    }
   
    loadComponent(footprintName) {
        const filename = kicadModuleDir + footprintName.replace(':', '.pretty/') + '.kicad_mod'
        const footprint = fs.readFileSync(filename).toString()
        module = PCBmm.load(footprint)
        const component = {
            pins: {},
            footprint: footprintName
        }

        const outline = this.getModuleOutline(module)
        
        const size = {
            width: (Math.abs(outline.width.min) + Math.abs(outline.width.max)),
            height: (Math.abs(outline.height.min) + Math.abs(outline.height.max))
        }
        component.size = size

        module.pads.forEach((pad, index) => {
            const pin = {
                location: [pad.pos.x, pad.pos.y]
            }
            const pad_name = pad.name || '_' + index.toString()

            component.pins[pad_name] = pin

        })
        
        return component
    }
}


const plotter = new SVGPlotter();
const pcbPlotter = new PCBmodePlotter(plotter)

const pcb = {
    components: {}
}
const parts = netlist.components

const root = {
    name: '',
    pins: 0
}


const components = Object.keys(parts).reduce((components, part) => {
    const component = pcbPlotter.loadComponent(parts[part].footprint)
   
    const pins_length = Object.keys(parts[part].pins).length
    if (pins_length > root.pins) {
        root.name = part
        root.pins = pins_length
    }
    
    components[part] = {
		...component
	}

	Object.keys(component.pins).forEach(pin => {
		const original_pin = components[part].pins[pin]
		components[part].pins[pin] = {
			...original_pin,
			...parts[part].pins[pin]
		}
	})

    return components
}, {})


// Arrange
let graph = new dagre.graphlib.Graph()
graph.setGraph({ 
    rankdir: 'TB', 
    edgesep: 1, 
    nodesep: 2, 
    ranksep: 1,
})
graph.setDefaultEdgeLabel(_ => ({}))

Object.keys(components).forEach(origin => {
    const part = components[origin]
    const pins = netlist.components[origin].pins
    const rotate = 0 //getRandomArbitrary(0, 360)
    components[origin].rotate = rotate
    const rotate_rad = Math.PI / rotate
    const size = {
        width: part.size.width, // Math.abs(part.size.width * Math.sin(rotate)) + Math.abs(part.size.height * Math.cos(rotate)),
        height: part.size.height, //Math.abs(part.size.width * Math.cos(rotate)) + Math.abs(part.size.height * Math.sin(rotate))
    }
    graph.setNode(origin, { width: size.width, height: size.height })

    componentEdge(origin)
})

function componentEdge(name) {
    const root_component = netlist.components[name]
    const root_pins = Object.keys(components[name].pins)
    
    root_pins.filter(pin => root_component.pins[pin] && netlist.netlist[root_component.pins[pin].net]).map(pin => {
        const net_name = root_component.pins[pin].net
        const net = netlist.netlist[net_name]

        Object.keys(net).forEach(related_component => {
            graph.setEdge(name, related_component, { labeloffset: 0 }) 
        })
    
    })
}

function getRandomArbitrary(min, max) {
    return Math.random() * (max - min) + min;
}
  
dagre.layout(graph)

pcb.width = graph.graph().width + 5 
pcb.height = graph.graph().height + 5

graph.nodes().forEach(function (name) {
    const node = graph.node(name)
    pcb.components[name] = {
        footprint: components[name].footprint,
        layer: 'top',
        location: [node.x  , node.y],
        rotate: components[name].rotate,//0, //getRandomArbitrary(0, 180),
        ...components[name]
    }
});

graph.edges().forEach(function (e, index) {
    const edge = graph.edge(e)
    const value = edge.points.reduce((value, point, index) => {
        command = 'L'
        if (index == 0) {
            command = 'M'
        } 
        value.push(command + (point.x ) + ' ' + (point.y))

        return value
    }, []).join(' ')
});

console.log(JSON.stringify(pcb))
