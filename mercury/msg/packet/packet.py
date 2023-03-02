from __future__ import annotations
from abc import ABC


class Packet(ABC):
    def __init__(self, node_from: str, node_to: str | None, data: Packet | int, header: int, t_gen: float):
        """
        Data packet abstract base class.
        :param node_from: node that sent the data.
        :param node_to: node that is the receiver of the data.
        :param data: data contained in the packet.
                     If integer, it refers to the size (in bits) of the content of the packet.
                     If it is a Packet, it refers to the packet that comprises the content of the packet.
        :param header: size (in bits) of the header of the packet.
        :param t_gen: time (in seconds) at which the packet was generated
        """
        self.node_from: str = node_from
        self.node_to: str | None = node_to
        self.data: Packet | int = data
        self.header: int = header
        self.t_gen: float = t_gen
        self.t_sent: list[float] = list()
        self.t_rcv: list[float] = list()

    @property
    def size(self) -> int:
        data = self.data.size if isinstance(self.data, Packet) else self.data
        return data + self.header

    @property
    def t_queue(self) -> float | None:
        return self.t_sent[0] - self.t_gen if self.t_sent else None

    @property
    def t_trip(self) -> float | None:
        return None if not self.t_rcv else self.t_rcv[-1] - self.t_sent[0]

    @property
    def n_sent(self) -> int:
        return len(self.t_sent)

    def send(self, t: float, set_node_to: bool = False, node_to: str | None = None):
        self.t_sent.append(t)
        if set_node_to:
            self.node_to = node_to

    def receive(self, t: float):
        self.t_rcv.append(t)
