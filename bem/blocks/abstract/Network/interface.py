from . import Base
from types import MethodType
from hashlib import md5

class Interfaced:
    interfaces = []
    pins = {
        'v_ref': True,
        'gnd': True
    }

    def __and__(self, instance):
        if issubclass(type(instance), Base):
            self.__interface__(instance)

            return instance

        if isinstance(instance, MethodType):
            return instance(self)

        raise Exception

    def __rand__(self, instance):
        if issubclass(type(instance), Base):
            instance.__interface__(self)

            return instance

        if isinstance(instance, MethodType):
            return instance(self)

        raise Exception

    def __or__(self, instance):
        self.log("FIXME: Implement parallel interface connection")
        raise Exception

    def __interface__(self, instance):
        def power_crc(instance):
            crc = str(instance.v_ref.get_pins()) + str(instance.gnd.get_pins()) + str(instance.v_ref.get_nets()) + str(instance.gnd.get_nets())
            return md5(crc.encode()).hexdigest()

        # If power net will not changed, we connect power bus in generic way
        # FIXME: if new connection with single pin net
        instance_power_crc = power_crc(instance)

        instance_interfaces = instance.mods.get('interface', None) or instance.props.get('interface', None) or []
        for protocol in instance_interfaces:
            self_interfaces = self.mods.get('interface', None) or self.props.get('interface', None) or []
            if protocol in self_interfaces:
                interface = getattr(self, protocol)
                interface(instance)

        if power_crc(self) == power_crc(instance):
            self.connect_power_bus(instance)

    def get_interface_pins(self, protocol):
        pins = {}
        for pin in getattr(self, protocol.upper()):
            pins[pin] = self[pin]

        return pins

    def interface(self, protocol, instance):
        for pin in getattr(self, protocol.upper()):
            self[pin] & instance[pin]

# cpu.spi & Display --  cpu.spi(Display) cpu.interface(spi, Display.interfaces['spi'])
