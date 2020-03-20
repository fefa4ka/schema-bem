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
    TextHjustify,
	TextVjustify,
    PCBPlotter,
    Pcb,
    Lib,
    PinOrientation
} = require("kicad-utils")

const DEFAULT_LINE_WIDTH = 6
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
    lineWidth = 1
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
    text(
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
        this.output += this.xmlTag `<text style="font-size:${size}px;" class="nodevalue $cell_id" transform="rotate(${orientation === 0 ? '0' : '-90'})" x="${orientation === 0 ? p.x : p.y}" y="${orientation === 0 ? p.y : p.x}" s:attribute="value">${text}</text>`
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
        this.output += this.xmlTag `<text class="nodelabel $cell_id" style="font-size:${size}px;" transform="rotate(${orientation === 0 ? '0' : '-90'})" x="${orientation === 0 ? p.x : p.y}" y="${orientation === 0 ? p.y : p.x}" s:attribute="ref">${text}</text>`
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
            let text = 'Very_Long_Reference' //component.field.reference;
			const width  = 0 //this.plotter.font.computeTextLineSize(text, component.field.textSize, DEFAULT_LINE_WIDTH);
			const height = 0 //this.plotter.font.getInterline(component.field.textSize, DEFAULT_LINE_WIDTH);

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
        if (component.fields[0] && component.fields[0].visibility) {
			const pos = transform.transformCoordinate(component.fields[0].pos);
			let orientation = component.fields[0].textOrientation;
			if (transform.y1) {
				if (orientation === TextAngle.HORIZ) {
					orientation = TextAngle.VERT;
				} else {
					orientation = TextAngle.HORIZ;
				}
			}
			let text = '10 000 V'// component.fields[0].name;
			const width  = 0//this.plotter.font.computeTextLineSize(text, component.fields[0].textSize, DEFAULT_LINE_WIDTH);
			const height = 0//this.plotter.font.getInterline(component.fields[0].textSize, DEFAULT_LINE_WIDTH);
			this.plotter.text(
				Point.add({ x: width / 2, y: height / 2 }, pos),
			    '',	
				text,
				orientation,
				component.fields[0].textSize,
				TextHjustify.CENTER,
				TextVjustify.CENTER,
				DEFAULT_LINE_WIDTH,
				component.fields[0].italic,
				component.fields[0].bold
			);
		}
    }

}

const svgPlotter = new SkinPlotter()
const schSvgPlotter = new SchSkinPlotter(svgPlotter)
svgPlotter.lineWidth = 2 
const type = library_name + ':' + device_name

if(rotate == 0) transform = new Transform(1, 0, 0, -1) // Base
if(rotate == 90) transform = new Transform(0, 1, -1, 0) // 90
if(rotate == 180) transform = new Transform(-1, 0, 0, 1) // 180 
if(rotate == 270 || rotate == -90) transform = new Transform(0, -1, -1, 0) // 270

svgPlotter.startPlot()
svgPlotter.startG({ type, width, height }, '')
svgPlotter.addTag('s:alias', { val: type })
schSvgPlotter.plotLibComponent(component, 1, 1, transform)
schSvgPlotter.plotLibComponentField(component, 1, 1, transform)
svgPlotter.endG()
svgPlotter.endPlot()

console.log(JSON.stringify({
	svg: schSvgPlotter.plotter.output,
	component
}))


