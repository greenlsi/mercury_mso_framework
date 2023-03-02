from __future__ import annotations
from mercury.config.packet import PacketConfig
from .packet import Packet
from .app_packet import AppPacket


class NetworkPacket(Packet):
    data: AppPacket | NetworkPacket

    def __init__(self, data: AppPacket | NetworkPacket, node_from: str):
        """Session and network layer-based data packet. It emulates TCP-IP communication"""
        header = PacketConfig.SESSION_HEADER
        header += PacketConfig.NETWORK_HEADER

        if isinstance(data, AppPacket):
            # node_from = data.node_from
            node_to = data.node_to
            t_gen = data.t_sent[-1]
        else:
            # node_from = data.node_to
            node_to = data.node_from
            t_gen = data.t_rcv
        self.ack: NetworkPacket | None = None
        self.timeout: float | None = None
        super().__init__(node_from, node_to, data, header, t_gen)

    @property
    def size(self) -> int:
        return self.header if isinstance(self.data, NetworkPacket) else super().size

    @property
    def t_round_trip(self) -> float | None:
        if self.t_rcv is not None and isinstance(self.data, NetworkPacket):
            return self.t_trip + self.data.t_trip

    def send(self, t: float, set_node_to: bool = False, node_to: str | None = None):
        super().send(t, set_node_to, node_to)
        self.timeout = t + PacketConfig.SESSION_TIMEOUT
        if isinstance(self.data, NetworkPacket):
            self.data.ack = self

    def expanse_packet(self) -> tuple[str, AppPacket | NetworkPacket]:
        return self.node_from, self.data
