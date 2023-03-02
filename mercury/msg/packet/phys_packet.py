from __future__ import annotations
from abc import ABC
from mercury.config.packet import PacketConfig
from .net_packet import Packet, NetworkPacket


class PhysicalPacket(Packet, ABC):
    data: NetworkPacket

    def __init__(self, node_from: str, node_to: str, data: NetworkPacket, header: int):
        """Physical layer-based data packet abstract base class."""
        super().__init__(node_from, node_to, data, header, data.t_sent[-1])
        self.send(self.t_gen)

        self.power: float | None = None
        self.bandwidth: float | None = None
        self.mcs: float | None = None
        self.frequency: float | None = None
        self.noise: float | None = None

    @property
    def snr(self) -> float | None:
        return self.power if self.noise is None else self.power - self.noise

    def expanse_packet(self) -> tuple[str, NetworkPacket]:
        return self.node_from, self.data


class CrosshaulPacket(PhysicalPacket):
    def __init__(self, node_from: str, node_to: str, data: NetworkPacket):
        super().__init__(node_from, node_to, data, PacketConfig.PHYS_XH_HEADER)


class RadioPacket(PhysicalPacket):
    def __init__(self, node_from: str, node_to: str, data: NetworkPacket, wired: bool):
        header = PacketConfig.PHYS_ACC_WIRED_HEADER if wired else PacketConfig.PHYS_ACC_WIRELESS_HEADER
        super().__init__(node_from, node_to, data, header)
