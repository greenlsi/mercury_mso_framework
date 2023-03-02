from typing import TypeVar
from .packet import Packet
from .app_packet import AppPacket
from .net_packet import NetworkPacket
from .phys_packet import PhysicalPacket

PacketInterface = TypeVar('PacketInterface', AppPacket, NetworkPacket, PhysicalPacket)
