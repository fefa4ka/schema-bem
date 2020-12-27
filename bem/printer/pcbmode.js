const dagre = require('dagre')
const fs = require('fs')
const pcbmodeDefault = require('../pcbmode.json')

const {
    Color,
    SVGPlotter,
    PCBPlotter,
    Pcb,
} = require("kicad-utils")
const { PadShape } = Pcb
const { PCB_LAYER_ID } = Pcb

const args = process.argv.slice(2)

const board = args[0]
const boardDir = 'boards/' + board.replace(/./g, '/')
const componentsDir = boardDir + '/components'

const netlistFilename = args[1]
const netlist = require(netlistFilename)

fs.mkdirSync(componentsDir, { recursive: true }, (err) => {
    if (err) throw err;
})

const kicadModuleDir = 'kicad/modules/'

class PCBmm extends Pcb.PCB {
    parseBoardUnits (expected) {
        return this.parseFloat(expected)
    }
}

class PCBmodePlotter extends PCBPlotter {
    plotModuleLayer(mod, layer) {
        for (let edge of mod.graphics) {
            // console.log(EdgeModule)o
            // this.plotter.outpu
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
        const filename = kicadModuleDir + `${footprintName.replace(':', '.pretty/')}.kicad_mod`
        const footprint = fs.readFileSync(filename).toString()
        module = PCBmm.load(footprint)
        const component = {
            pins: {},
            layout: {
                silkscreen: {},
                assembly: {}
            },
            pads: {},
            module
        }

        const outline = this.getModuleOutline(module)
        
        const size = {
            width: Math.abs(outline.width.min) + Math.abs(outline.width.max),
            height: Math.abs(outline.height.min) + Math.abs(outline.height.max)
        }
        component.size = size

        module.pads.forEach((pad, index) => {
            // pad.name = pad.name !== '' ?

            const pin = {
                layout: {
                    pad: 'pad',
                    location: [pad.pos.x, pad.pos.y],
                    'show-label': true
                }
            }
            const pad_name = pad.name || '_' + index.toString()

            component.pins[pad_name] = pin

            const shape = {
                type: '',
                layers: ['top', 'bottom'],
                location: [0, 0]
            }

            if (pad.shape === PadShape.CIRCLE) {
                shape.type = 'circle'
                shape.outline = [0, 0]
                shape.diameter = pad.size.width
            } else
                if (pad.shape === PadShape.RECT) {
                    shape.type = 'rect'
                    shape.width = pad.size.width
                    shape.height = pad.size.height
                } else
                    if (pad.shape === PadShape.OVAL) {
                        shape.type = 'rect'
                        shape.width = pad.size.width
                        shape.height = pad.size.height
                        const radii = (shape.width + shape.height) / 4
                        shape.radii = {
                            tl: radii,
                            bl: radii,
                            tr: radii,
                            br: radii
                        }
                        // } else
                        // if (pad.shape === PadShape.TRAPEZOID) {
                    } else
                        if (pad.shape === PadShape.ROUNDRECT) {
                            shape.type = 'rect'
                            const radii = pad.roundRectRatio
                            shape.width = pad.size.width
                            shape.height = pad.size.height
                            shape.radii = {
                                tl: radii,
                                bl: radii,
                                tr: radii,
                                br: radii
                            }
                        }
            shape.offset = 0


            const footprint = {
                shapes: [{ ...shape }],
                drills: pad.drillSize.width ? [{
                    diameter: pad.drillSize.width
                }] : []
            }

            Object.keys(component.pads).forEach(pad => {
                const compared = JSON.stringify(component.pads[pad])
                if (compared === JSON.stringify(footprint)) {
                    pin.layout.pad = pad
                }
            })

            if (pin.layout.pad === 'pad') {
                pin.layout.pad = pad_name
                component.pads[pad_name] = footprint
            }

        })
        
        return component
    }
}


const plotter = new SVGPlotter();
const pcbPlotter = new PCBmodePlotter(plotter)


const parts = netlist.components

const pcbmode = {
    ...pcbmodeDefault
}

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
    
    components[part] = component
    return components
}, {})


// Arrange
let graph = new dagre.graphlib.Graph()
graph.setGraph({ edgesep: 1, nodesep: 10, ranksep: 10})
graph.setDefaultEdgeLabel(_ => ({}))

Object.keys(components).forEach(origin => {
    const part = components[origin]
    const pins = netlist.components[origin].pins
    const rotate = 0 //getRandomArbitrary(0, 360)
    components[origin].rotate = rotate
    const rotate_rad = Math.PI / rotate
    const size = {
        width: Math.abs(part.size.width * 10 * Math.sin(rotate_rad)) + Math.abs(part.size.height * 10 * Math.cos(rotate_rad)),
        height: Math.abs(part.size.width * 10 * Math.cos(rotate_rad)) + Math.abs(part.size.height * 10 * Math.sin(rotate_rad))
    }
    graph.setNode(origin, { width: part.size.width * 10, height: part.size.height * 10 })

    componentEdge(origin)

    const component = {
        ...part
    }
    delete component.module
    delete component.size
    
    const json_component = JSON.stringify(component, null, 4)
    let used_footprint = netlist.components[origin].footprint

    fs.writeFileSync(`${components_dir}/${used_footprint}.json`, json_component)
    components[origin].footprint = used_footprint
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

pcbmode.outline.shape.width = graph.graph().width/10
pcbmode.outline.shape.height = graph.graph().height / 10
const graph_size = pcbmode.outline.shape
graph.nodes().forEach(function (name) {
    const node = graph.node(name)
    pcbmode.components[name] = {
        footprint: components[name].footprint,
        layer: 'top',
        location: [node.x /10 - graph_size.width/2 , node.y/ 10 - graph_size.height/2],
        rotate: components[name].rotate,//0, //getRandomArbitrary(0, 180),
        show: true,
        silkscreen: {
            refdef: {
                location: [0, 0],
                show: true
            }
        },
        shapes: {
            show: true
        }

    }
});


const routes = {
    "bottom": {
    }
}

graph.edges().forEach(function (e, index) {
    const edge = graph.edge(e)
    const value = edge.points.reduce((value, point, index) => {
        command = 'L'
        if (index == 0) {
            command = 'M'
        } 
        value.push(command + (point.x / 10) + ' ' + (point.y / 10))

        return value
    }, []).join(' ')
    routes.bottom[index] = {
        "stroke-width": 0.3,
        "style": "stroke",
        "type": "path",
        value
    }
});

fs.writeFileSync(boadDir + '/' + board + '.json', JSON.stringify(pcbmode, null, 4))
fs.writeFileSync(boardDir + '/' + board + '_routing.json', JSON.stringify(routes, null, 4))