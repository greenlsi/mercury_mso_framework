from mercury.config.network import PacketConfig
from .packet import NetworkPacket, PhysicalPacket


class CrosshaulPacket(PhysicalPacket):
    def __init__(self, node_from: str, node_to: str, data: NetworkPacket):
        super().__init__(node_from, node_to, data, PacketConfig.PHYS_XH_HEADER)


class RadioPacket(PhysicalPacket):
    def __init__(self, node_from: str, node_to: str, data: NetworkPacket):
        super().__init__(node_from, node_to, data, PacketConfig.PHYS_RAD_HEADER)
