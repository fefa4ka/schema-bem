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
} = require("./kicad-utils/js/kicad-utils.js")

const DrawPin = Lib.DrawPin

const args = process.argv.slice(2)
const [library_name, device_name, unit, rotate, ref, value] = args


const device = fs.readFileSync('/Library/Application\ Support/kicad/library/' + library_name + '.lib').toString()

const lib = Lib.Library.load(device)

const component = lib.findByName(device_name);
const rect = component.draw.getBoundingRect();
if (ref) component.field.reference = ref
if (value) component.fields[0].name = value

const TEXT_SIZE = 8;
let scale = 0.3

const PADDING = 0


class SkinPlotter extends SVGPlotter {
    output = ''
    startPlot() {
    }
    endPlot() {
    }
    startG(props, transform) {
        let tagProps = Object.keys(props).map(prop => `s:${prop}="${props[prop]}"`).join(' ')

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
        let tagProps = Object.keys(props).map(prop => `s:${prop}="${props[prop]}"`).join(' ')

        this.output += this.xmlTag `\n<g ${transform ? 'transform="${transform}"' : ''} ${tagProps}/>\n`
    }
    value(
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

        const x = orientation === 0 ? p.x : p.y
        const y = orientation === 0 ? p.y : p.x

        this.output += this.xmlTag `\n<text 
            style="font-size:${size}px;" 
            class="nodevalue $cell_id" 
            transform="rotate(${orientation === 0 ? '0' : '-90'}, ${p.x}, ${p.y})" 
            x="${p.x}" y="${p.y}" ${text ? '' : 's:attribute="value"'}>${text}</text>\n`
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

        const x = orientation === 0 ? p.x : p.y
        const y = orientation === 0 ? p.y : p.x


        this.output += this.xmlTag `\n<text class="nodelabel $cell_id" style="font-size:${size}px;" transform="rotate(${orientation === 0 ? '0' : '-90'}, ${p.x}, ${p.y})" x="${p.x}" y="${p.y}" s:attribute="ref">${text}</text>\n`
	}
}


class SchSkinPlotter extends SchPlotter {
    plotDrawPin(draw, component, transform) {
        draw.lineWidth = config.lineWidth 
        draw.length *= scale

        this.plotDrawPinReference(draw, component, transform)

		if (!draw.visibility) return;

		this.plotDrawPinTexts(draw, component, transform);
        this.plotDrawPinSymbol(draw, component, transform);

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

            const text = 'Very_Long_Name_Block'
			let width  = 0;// this.plotter.font.computeTextLineSize(text, component.fields[0].textSize * scale / 4, config.lineWidth) / 2;
			let height = 0; //this.plotter.font.getInterline(component.fields[0].textSize * scale / 4, config.lineWidth);
            let px = width / 2, py = height / 2;

            if(orientation != 0) {
                px = height
                py = width
            }
            
            this.plotter.label(
                Point.add({ x: px, y: py}, pos),
                '',
                component.field.reference || {},
                orientation,
                component.field.textSize * scale,
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

            const text = '100 mOhm'
			let width  = 0;//this.plotter.font.computeTextLineSize(text, component.fields[0].textSize * scale / 4, config.lineWidth) / 2;
			let height = 0;//this.plotter.font.getInterline(component.fields[0].textSize * scale / 4, config.lineWidth);
            let px = width / 2, py = height / 2;

            if(orientation != 0) {
                px = height
                py = width
            }

			this.plotter.value(
				Point.add({ x: px, y: py }, pos),
			    '',	
				component.fields[0].reference || '',
				orientation,
				component.fields[0].textSize * scale,
				TextHjustify.CENTER,
				TextVjustify.CENTER,
				config.lineWidth,
				component.fields[0].italic,
				component.fields[0].bold
			);
		}
    }

}

const config = {
    lineWidth: 1,
    lineWidthBus: 2,
    fill: Fill.NO_FILL,
    color: Color.BLACK,
    scale
}

const svgPlotter = new SkinPlotter(config)
const schSvgPlotter = new SchSkinPlotter(svgPlotter)
const type = library_name + ':' + device_name


const width = rect.width * scale + PADDING, height = rect.height * scale + PADDING;
// 
// if(rotate == 0) transform = new Transform(1, 0, 0, -1) // Base
// if(rotate == 90) transform = new Transform(0, 1, -1, 0) // 90
// if(rotate == 180) transform = new Transform(-1, 0, 0, 1) // 180 
// if(rotate == 270 || rotate == -90) transform = new Transform(0, -1, 1, 0) // 270
const x_mirror = 1
const y_mirror = 1
if(rotate == 0) transform = new Transform(scale * x_mirror, 0, 0, y_mirror * scale * -1) // Base
if(rotate == 90) transform = new Transform(0, scale, -1 * scale, 0) // 90
if(rotate == 180) transform = new Transform(-1 * scale, 0, 0, scale) // 180 
if(rotate == 270 || rotate == -90) transform = new Transform(0, -1 * scale, 1 * scale, 0) // 270
// GND
pos = rect.pos1

scale = 1
transform = transform.translate(pos.x * x_mirror * -1, pos.y * y_mirror ) 
//transform = transform.translate(1 / scale, 0) 

svgPlotter.startPlot()
svgPlotter.startG({ type, width: rect.width * scale, height: rect.height * scale }, '')
svgPlotter.addTag('s:alias', { val: type })
schSvgPlotter.plotLibComponent(component, parseInt(unit), 1, transform)
schSvgPlotter.plotLibComponentField(component, parseInt(unit), 1, transform)
svgPlotter.endG()
svgPlotter.endPlot()
console.log(JSON.stringify({
	svg: schSvgPlotter.plotter.output,
    port_orientation: component.draw.objects
        .filter(item => item instanceof DrawPin)
        .map(pin => ({
            pin: pin.num,  
            orientation: schSvgPlotter.pinDrawOrientation(pin, transform)
        })).reduce((pins, pin) => {
            pins[pin.pin] = pin.orientation

            return pins
        }, {})
}))


//console.log(schSvgPlotter.plotter.output) //.replace(/\n/g, ''))


