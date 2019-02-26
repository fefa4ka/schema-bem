from bem import Block, Build
from skidl import Circuit, set_default_tool, KICAD

try:
    import __builtin__ as builtins
except ImportError:
    import builtins
    
class Print:
    block = None
    kit = []
    scheme = None

    def __init__(self, Block, props, kit=[]):
        set_default_tool(KICAD) 
        builtins.DEBUG = False
        
        self.scheme = Circuit()
        builtins.default_circuit.reset(init=True)
        del builtins.default_circuit
        builtins.default_circuit = self.scheme
        builtins.NC = self.scheme.NC

        self.block = Block(**props)
        self.kit = kit
    
    def netlist(self):
        for device in self.kit:
            device_name = device['library'] + ':' + device['name'][:device['name'].rfind('_')]
            DeviceBlock = Build(device_name, footprint=device['footprint']).element
            
            for device_pin_name in device['pins'].keys():
                for pin in device['pins'][device_pin_name]:
                    device_pin = getattr(DeviceBlock, device_pin_name)
                    device_pin += getattr(self.block, pin)

        self.scheme.ERC()
        
        return self.sscheme.generate_netlist()

    @classmethod    
    def additional_devices(self, block):
        pins = block.get_pins()
        connected = [pin for pin in pins.keys() if len(pins[pin]) > 0]
        
        pin_head = {
            'library': 'Connector_Generic',
            'name': 'Conn_01x02',
            'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical'
        }

        devices = [{
            **pin_head,
            'name': 'Conn_01x02_V',
            'pins': {
                'Pin_1': ['v_ref'] if block.v_ref  else [],
                'Pin_2': ['gnd']
            }
        }]

        if 'input_n' in connected:
            devices.append({
                **pin_head,
                'name': 'Conn_01x02_I',
                'pins': {
                    'Pin_1': ['input'],
                    'Pin_2': ['input_n']
                }
            })

        if 'output_n' in connected:
            devices.append({
                **pin_head,
                'name': 'Conn_01x02_O',
                'pins': {
                    'Pin_1': ['output'],
                    'Pin_2': ['output_n']
                }
            })

        if not ('output_n' in connected and 'input_n' in connected):
            devices.append({
                **pin_head,
                'name': 'Conn_01x02_IO',
                'pins': {
                    'Pin_1': ['input'],
                    'Pin_2': ['output']
                }
            })

        other = [pin for pin in connected if pin not in ['input', 'output', 'input_n', 'output_n', 'v_ref', 'gnd']]
        other_len = str(len(other))
        other_pin_head = {
            **pin_head,
            'name': 'Conn_01x0' + other_len + '_0',
            'footprint': 'Connector_PinHeader_2.54mm:PinHeader_1x0' + other_len + '_P2.54mm_Vertical',
            'pins': { index + 1: [pin] for index, pin in enumerate(other) }
        }

        return devices
   