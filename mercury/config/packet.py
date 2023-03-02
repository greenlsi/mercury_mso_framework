from __future__ import annotations
from typing import ClassVar


class PacketConfig:
    """Network Packet data and header configurations."""
    PHYS_ACC_WIRELESS_HEADER: ClassVar[int] = 16             # TODO research NR header
    PHYS_ACC_WIRED_HEADER: ClassVar[int] = 16                # TODO research NR header
    PHYS_XH_HEADER: ClassVar[int] = 112                      # Ethernet header is 14 bytes

    NETWORK_HEADER: ClassVar[int] = 160                      # IP header is 20 bytes
    SESSION_HEADER: ClassVar[int] = 160                      # TCP header is 20 bytes
    SESSION_TIMEOUT: ClassVar[float] = 1                     # TCP delay is 1 second by default

    RAN_HEADER: ClassVar[int] = 0                            #

    EDGE_FED_MGMT_HEADER: ClassVar[int] = 0                  #
    EDGE_FED_MGMT_CONTENT: ClassVar[int] = 0                 #

    SRV_PACKET_HEADERS: ClassVar[dict[str, int]] = dict()    #
    SRV_PACKET_SRV_REQ: ClassVar[dict[str, int]] = dict()    #
    SRV_PACKET_SRV_RES: ClassVar[dict[str, int]] = dict()    #
    SRV_PACKET_OPEN_REQ: ClassVar[dict[str, int]] = dict()   #
    SRV_PACKET_OPEN_RES: ClassVar[dict[str, int]] = dict()   #
    SRV_PACKET_CLOSE_REQ: ClassVar[dict[str, int]] = dict()  #
    SRV_PACKET_CLOSE_RES: ClassVar[dict[str, int]] = dict()  #

    @staticmethod
    def reset_srv():
        PacketConfig.SRV_PACKET_HEADERS = dict()
        PacketConfig.SRV_PACKET_SRV_REQ = dict()
        PacketConfig.SRV_PACKET_SRV_RES = dict()
        PacketConfig.SRV_PACKET_OPEN_REQ = dict()
        PacketConfig.SRV_PACKET_OPEN_RES = dict()
        PacketConfig.SRV_PACKET_CLOSE_REQ = dict()
        PacketConfig.SRV_PACKET_CLOSE_RES = dict()
