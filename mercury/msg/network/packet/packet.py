from __future__ import annotations
from abc import ABC
from mercury.config.network import PacketConfig
from typing import Any, Optional, Tuple, Union


class PacketData:
    def __init__(self, size: int = 0):
        self.size = size


class Packet(ABC):
    def __init__(self, data: Union[Packet, PacketData], header: int):
        """
        Data packet abstract base class.
        :param data: data contained in the packet.
        :param header: size (in bits) of the header of the packet.
        """
        self.data: Union[Packet, PacketData] = data
        self.header: int = header

    @property
    def size(self) -> int:
        return self.header + self.data.size


class ApplicationPacket(Packet, ABC):  # TODO add session layer capabilities (UDP and TCP)
    """Application and session layer-based data packet abstract base class."""
    data: PacketData


class NetworkPacket(Packet):

    data: ApplicationPacket

    def __init__(self, node_from: str, node_to: Optional[str], data: ApplicationPacket):
        """
        Network layer-based data packet (end-to-end logical addressing).
        :param node_from: node that sent the data.
        :param node_to: node that is the receiver of the data.
        :param data: application data packet to be encapsulated.
        """
        super().__init__(data, PacketConfig.NET_HEADER)
        self.node_from: str = node_from
        self.node_to: Optional[str] = node_to

    def expanse_packet(self) -> Tuple[str, ApplicationPacket]:
        return self.node_from, self.data


class PhysicalPacket(Packet, ABC):

    data: NetworkPacket

    def __init__(self, node_from: str, node_to: str, data: NetworkPacket, header: int):
        """
        Physical layer-based data packet (point-to-point physical addressing).
        :param node_from: node that sent the data.
        :param node_to: node that is the receiver of the data.
        :param data: network packet to be transmitted.
        :param header: number of bits included in the header of the message.
        """
        super().__init__(data, header)
        self.node_from: str = node_from
        self.node_to: str = node_to

        self.power: Optional[float] = None
        self.bandwidth: Optional[float] = None
        self.mcs: Optional[Tuple[Any, float]] = None
        self.frequency: Optional[float] = None

        self.noise: Optional[float] = None
        self.n_hops: int = 0  # TODO Number of hops in the network

    @property
    def snr(self) -> Optional[float]:
        return self.power if self.noise is None else self.power - self.noise

    def expanse_packet(self) -> Tuple[str, NetworkPacket]:
        return self.node_from, self.data
