from __future__ import annotations
from abc import ABC
from ..packet import Packet


class AppPacket(Packet, ABC):
    def __init__(self, node_from: str, node_to: str | None, data: int, header: int, t_gen: float):
        """
        Application layer-based data packet abstract base class.
        :param node_from: ID of the sender node.
        :param node_to: ID of the receiver node.
        :param data: size (in bits) of the content of the application data packet.
        :param header: size (in bits) of the header of the application data packet.
        :param t_gen: time (in seconds) when the packet was generated.
        """
        super().__init__(node_from, node_to, data, header, t_gen)
