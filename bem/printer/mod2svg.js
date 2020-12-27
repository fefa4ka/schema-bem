const fs = require('fs')

const {
    Color,
    Fill,
    CanvasPlotter,
    SVGPlotter,
    PCBPlotter,
    Pcb,
} = require("./kicad-utils/js/kicad-utils.js")

const {
	LSET,
    PCB_LAYER_ID,
    TextModule
} = require("./kicad-utils/js/kicad_pcb.js")

const args = process.argv.slice(2)
const filename = args[0]
let value, ref = ''

if(args.length > 1) {
    ref = args[1]
}
if(args.length > 2) {
    value = args[2]
}

class FootprintPlotter extends SVGPlotter {
    startG(props, transform) {
        let tagProps = Object.keys(props).map(prop => `${prop}="${props[prop]}"`).join(' ')

        this.output += this.xmlTag `\n<g ${transform ? 'transform="${transform}"' : ''} ${tagProps}>`
    }
    endG() {
        this.output += this.xmlTag `</g>\n`
    }
	addTag(tag, props) {
		let tagProps = Object.keys(props).map(prop => `${prop}="${props[prop]}"`).join(' ')
		this.output += `\n<${tag} ${tagProps}/>\n`
	}
    g(props, transform) {
        let tagProps = Object.keys(props).map(prop => `${prop}="${props[prop]}"`).join(' ')

        this.output += this.xmlTag `\n<g ${transform ? 'transform="${transform}"' : ''} ${tagProps}/>\n`
    }
}

class ModulePlotter extends PCBPlotter {
    plotModule(mod) {
        for (let edge of mod.graphics) {
            if (edge instanceof Pcb.EdgeModule) {
                this.plotEdgeModule(edge, mod);
            }
        }
        for (let pad of mod.pads) {
            this.plotter.startG({ name: pad.name, class: 'part_pad' })

            this.plotPad(true, pad, Color.YELLOW, Fill.FILLED_SHAPE)

            this.plotter.endG()

            this.plotter.setColor(Color.WHITE)
            if (pad.drillSize.width) 
                this.plotOneDrillMark(pad.drillShape, pad.pos, pad.drillSize, pad.size, pad.orientation, 0)
        }

        this.plotAllTextModule(mod);
    }
    _plotTextModule(mod, text, color) {
    console.log('TEEXT', mod, text)
    }
    getModuleSize(mod) {
        const outline = {
            width: { min: 0, max: 0 },
            height: { min: 0, max: 0 }
        }
        mod.graphics.forEach(graph => {
            const points = [graph.start, graph.end]
    
            points.forEach(el => {
                if (!el) return
                if (el.x < outline.width.min) outline.width.min = el.x
                if (el.x > outline.width.max) outline.width.max = el.x
                if (el.y < outline.height.min) outline.height.min = el.y
                if (el.y > outline.height.max) outline.height.max = el.y
            })
        })


        return outline 
    }
}



const footprint = fs.readFileSync(filename).toString()
const mod = Pcb.PCB.load(footprint)

const plotter = new FootprintPlotter();
const pcbPlotter = new ModulePlotter(plotter)

if(value || ref) {
pcbPlotter.layerMask = new LSET(
			PCB_LAYER_ID.F_Cu,
			PCB_LAYER_ID.F_Adhes,
			PCB_LAYER_ID.F_Paste,
			PCB_LAYER_ID.F_SilkS,
			PCB_LAYER_ID.Dwgs_User,
			PCB_LAYER_ID.Edge_Cuts,
            PCB_LAYER_ID.F_Fab
		);
}

if(value)
    mod.value.text = '' 

if(ref)
    mod.reference.text = ref


for (let text of mod.graphics) {
    if (text instanceof TextModule) {
        if(text.text === '%R') {
            text.text = value
        }
    }
}



const outline = pcbPlotter.getModuleSize(mod)

plotter.pageInfo = {
    width: Math.abs(outline.width.min) + Math.abs(outline.width.max),
    height: Math.abs(outline.height.min) + Math.abs(outline.height.max)
}

plotter.startPlot();

plotter.save();
plotter.translate(outline.width.min * -1, outline.height.min * -1);
// plotter.setColor(Color.WHITE);
pcbPlotter.plotModule(mod) 

// plotter.restore();
plotter.endPlot();

console.log(plotter.output)


/*
const Canvas = require('canvas');

const scale = 1

width=plotter.pageInfo.width
height=plotter.pageInfo.height
	const canvas = Canvas.createCanvas ? Canvas.createCanvas(width * scale, height * scale) : new Canvas(width * scale, height * scale);
	const ctx = canvas.getContext('2d');
	console.log(scale, canvas);
	ctx.fillStyle = "#fff";
	ctx.fillRect(0, 0, canvas.width, canvas.height);
	ctx.translate(0, 0);
	ctx.scale(scale, scale);
	const _plotter = new CanvasPlotter(ctx);

const _pcbPlotter = new ModulePlotter(_plotter)
// console.log(outline)
_plotter.pageInfo = {
    width: Math.abs(outline.width.min) + Math.abs(outline.width.max),
    height: Math.abs(outline.height.min) + Math.abs(outline.height.max)
}

_plotter.startPlot();

_plotter.save();
_plotter.translate(outline.width.min * -1, outline.height.min * -1);
// plotter.setColor(Color.WHITE);
_pcbPlotter.plotModule(kicad) 

// plotter.restore();
_plotter.endPlot();


	const out = fs.createWriteStream('text.png'), stream = canvas.pngStream();

	stream.on('data', function (chunk) {
		out.write(chunk);
	});

	stream.on('end', function(){
		console.log('saved png');
	});
    */
