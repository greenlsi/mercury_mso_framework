from __future__ import annotations
from typing import Any, ClassVar
from .network import TransceiverConfig, LinkConfig, NetworkConfig
from ..packet import PacketConfig
from ..gateway import GatewayConfig


class AccessNetworkConfig:

    DEFAULT_WIRED_TRX: ClassVar[TransceiverConfig] = TransceiverConfig()
    DEFAULT_WIRED_LINK: ClassVar[LinkConfig] = LinkConfig()

    # Wireless channels cannot be set to None, as clients measure the SNR to connect to the most suitable one
    DEFAULT_WIRELESS_DL_TRX: ClassVar[TransceiverConfig] = TransceiverConfig(tx_power=50)
    DEFAULT_WIRELESS_UL_TRX: ClassVar[TransceiverConfig] = TransceiverConfig(tx_power=30)
    DEFAULT_WIRELESS_LINK: ClassVar[LinkConfig] = LinkConfig(carrier_freq=33e9, att_id='fspl')

    def __init__(self, network_id: str, phys_wired_header: int | None = None, phys_wireless_header: int | None = None,
                 wired_dl_trx: TransceiverConfig | None = None, wired_ul_trx: TransceiverConfig | None = None,
                 wired_dl_link: LinkConfig | None = None, wired_ul_link: LinkConfig | None = None,
                 wireless_dl_trx: TransceiverConfig = None, wireless_ul_trx: TransceiverConfig = None,
                 wireless_dl_link: LinkConfig = None, wireless_ul_link: LinkConfig = None,
                 wireless_div_id: str | None = None, wireless_div_config: dict[str, Any] = None):
        from mercury.plugin import AbstractFactory, ChannelDivision

        if phys_wired_header is not None and phys_wired_header < 0:
            raise ValueError('phys_wired_header must be greater than or equal to 0')
        if phys_wireless_header is not None and phys_wireless_header < 0:
            raise ValueError('phys_wireless_header must be greater than or equal to 0')
        if phys_wired_header is not None:
            PacketConfig.PHYS_ACC_WIRED_HEADER = phys_wired_header
        if phys_wireless_header is not None:
            PacketConfig.PHYS_ACC_WIRELESS_HEADER = phys_wireless_header

        self.wired_dl_trx = self.DEFAULT_WIRED_TRX if wired_dl_trx is None else wired_dl_trx
        self.wired_ul_trx = self.DEFAULT_WIRED_TRX if wired_ul_trx is None else wired_ul_trx
        self.wired_dl_link = self.DEFAULT_WIRED_LINK if wired_dl_link is None else wired_dl_link
        self.wired_ul_link = self.DEFAULT_WIRED_LINK if wired_ul_link is None else wired_ul_link

        self.wireless_dl_trx = self.DEFAULT_WIRELESS_DL_TRX if wireless_dl_trx is None else wireless_dl_trx
        self.wireless_ul_trx = self.DEFAULT_WIRELESS_UL_TRX if wireless_ul_trx is None else wireless_ul_trx
        self.wireless_dl_link = self.DEFAULT_WIRELESS_LINK if wireless_dl_link is None else wireless_dl_link
        self.wireless_ul_link = self.DEFAULT_WIRELESS_LINK if wireless_ul_link is None else wireless_ul_link

        self.network_id: str = network_id
        self.wired_config: NetworkConfig = NetworkConfig(f'{network_id}_wired', self.wired_dl_trx, self.wired_dl_link)
        self.wireless_config: NetworkConfig = NetworkConfig(f'{network_id}_wireless', self.wireless_dl_trx, self.wireless_dl_link)
        self.wireless_div: ChannelDivision | None = None
        if wireless_div_id is not None:
            wireless_div_config = dict() if wireless_div_config is None else dict()
            self.wireless_div = AbstractFactory.create_network_channel_division(wireless_div_id, **wireless_div_config)

    def add_gateway(self, gw_config: GatewayConfig):
        if gw_config.gateway_id in self.wired_config.nodes or gw_config.gateway_id in self.wireless_config.nodes:
            raise ValueError(f'Gateway with ID {gw_config.gateway_id} already defined')
        net_config = self.wired_config if gw_config.wired else self.wireless_config
        net_config.add_node(gw_config.acc_node)
