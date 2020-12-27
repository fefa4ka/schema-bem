const netlistsvg = require('netlistsvg')

const fs = require('fs')

const {
	Transform,
    Color,
    Fill,
    Point,
    TextAngle,
    SVGPlotter,
    SchPlotter,
    PCBPlotter,
    Pcb,
    Lib,
    PinOrientation
} = require("kicad-utils")


const canvas2svg = require('canvas2svg')

const { createCanvas } = require('canvas')
const canvas = createCanvas(150, 150);

const args = process.argv.slice(2)
const [library_name, device_name, rotate] = args

const device = fs.readFileSync('/Users/fefa4ka/Development/schema.vc/kicad/library/' + library_name + '.lib').toString()

const lib = Lib.Library.load(device)

const component = lib.findByName(device_name);
const rect = component.draw.getBoundingRect();


const PADDING = 500;
const width = rect.width + PADDING, height = rect.height + PADDING;


const scale = Math.min(canvas.width / width, canvas.height / height);

class SkinPlotter extends SVGPlotter {
    output = ''
    startPlot() {
    }
    endPlot() {
    }
    startG(props, transform) {
        let tagProps = Object.keys(props).map(prop => `s:${prop}="${props[prop]}"`).join(' ')

        this.output += this.xmlTag `<g ${transform ? 'transform="${transform}"' : ''} ${tagProps}>`
    }
    endG() {
        this.output += this.xmlTag `</g>`
    }
	addTag(tag, props) {
		let tagProps = Object.keys(props).map(prop => `${prop}="${props[prop]}"`).join(' ')
		this.output += `<${tag} ${tagProps}/>`
	}
    g(props, transform) {
        let tagProps = Object.keys(props).map(prop => `s:${prop}="${props[prop]}"`).join(' ')

        this.output += this.xmlTag `<g ${transform ? 'transform="${transform}"' : ''} ${tagProps}/>`
    }

    label(
		p,
		color,
		text,
		orientation,
		size,
		hjustfy,
		vjustify,
		width,
		italic,
		bold,
		multiline
	) {
        this.output += this.xmlTag `<text class="nodelabel $cell_id" x="${p.x}" y="${p.y}" s:attribute="ref">${text}</text>`
	}
}


class SchSkinPlotter extends SchPlotter {
    plotDrawPin(draw, component, transform) {
		if (!draw.visibility) return;
		this.plotDrawPinTexts(draw, component, transform);
        this.plotDrawPinSymbol(draw, component, transform);
        this.plotDrawPinReference(draw, component, transform)
    }

    plotDrawPinReference(draw, component, transform) {
		const pos = transform.transformCoordinate(draw.pos);
		const orientation = this.pinDrawOrientation(draw, transform);
        
        const props = {
            pid: draw.num,
            position: '',
            x: pos.x,
            y: pos.y
        }

        if (orientation === PinOrientation.UP) {
            props.position = 'bottom'
		} else
		if (orientation === PinOrientation.DOWN) {
			props.position = 'top'
		} else
		if (orientation === PinOrientation.LEFT) {
			props.position = 'right'
		} else
		if (orientation === PinOrientation.RIGHT) {
			props.position = 'left'
		}

		this.plotter.g(props);
    }
    
    plotLibComponentField(component, unit, convert, transform) {
        if (component.field && component.field.visibility) {
            const pos = transform.transformCoordinate(component.field.pos);
            let orientation = component.field.textOrientation;
            if (transform.y1) {
                if (orientation === TextAngle.HORIZ) {
                    orientation = TextAngle.VERT;
                } else {
                    orientation = TextAngle.HORIZ;
                }
            }
            let text  = component.field.reference;
			const width  = 0;//this.plotter.font.computeTextLineSize(text, component.field.textSize, DEFAULT_LINE_WIDTH);
			const height = 0;//this.plotter.font.getInterline(component.field.textSize, DEFAULT_LINE_WIDTH);

            this.plotter.label(
                Point.add({ x: width / 2, y: height / 2 }, pos),
                '',
                text,
                orientation,
                component.field.textSize,
                '',
                '',
                '',
                component.field.italic,
                component.field.bold,
            );
        }
    }

}

const DEFAULT_LINE_WIDTH = 2;  

const svgPlotter = new SkinPlotter()
const schSvgPlotter = new SchSkinPlotter(svgPlotter)
svgPlotter.lineWidth = 2 
const type = library_name + ':' + device_name
radian = rotate * Math.PI / 180

if(rotate == 0) transform = new Transform(1, 0, 0, -1) // Base
if(rotate == 90) transform = new Transform(0, 1, -1, 0) // 90
if(rotate == 180) transform = new Transform(-1, 0, 0, 1) //180 
if(rotate == 270) transform = new Transform(0, -1, -1, 0) // 90

svgPlotter.startPlot()
svgPlotter.startG({ type, width, height }, '')
svgPlotter.addTag('s:alias', { val: type })
schSvgPlotter.plotLibComponent(component, 1, 1, transform)// new Transform().rotate(radian))
schSvgPlotter.plotLibComponentField(component, 1, 1, transform)// new Transform(0, 0, 1, 0))// new Transform().rotate(radian))
svgPlotter.endG()
svgPlotter.endPlot()

console.log('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:s="https://github.com/nturley/netlistsvg" viewBox="0 0 10000 10000">')
console.log(schSvgPlotter.plotter.output)
console.log('</svg>')

