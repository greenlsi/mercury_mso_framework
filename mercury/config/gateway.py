from __future__ import annotations
from typing import ClassVar
from .packet import PacketConfig
from .network.network import TransceiverConfig, StaticNodeConfig, \
    GatewayNodeConfig, WiredGatewayNodeConfig, WirelessGatewayNodeConfig


class GatewayConfig:
    def __init__(self, gateway_id: str, location: tuple[float, ...], wired: bool,
                 xh_trx: TransceiverConfig | None = None, acc_trx: TransceiverConfig | None = None):
        """
        Gateway model configuration.
        :param gateway_id: ID of the gateway
        :param location: Gateway location coordinates <x, y> (in meters)
        :param wired: if true, gateway is wired. Otherwise, gateway is wireless.
        :param xh_trx: Transceiver for crosshaul communications
        :param acc_trx: Transceiver for Radio communications
        """
        self.gateway_id: str = gateway_id
        self.location: tuple[float, ...] = location
        self.wired: bool = wired
        self.xh_node: StaticNodeConfig = StaticNodeConfig(self.gateway_id, self.location, xh_trx)
        acc_node = WiredGatewayNodeConfig if self.wired else WirelessGatewayNodeConfig
        self.acc_node: GatewayNodeConfig = acc_node(self.gateway_id, self.location, acc_trx)


class GatewaysConfig:

    GATEWAYS_LITE: ClassVar[str] = 'gws_lite'
    PSS_WINDOW: ClassVar[float] = 1
    COOL_DOWN: ClassVar[float] = 0

    def __init__(self, pss_window: float = 1, cool_down: float = 0, app_ran_header: int = 0):
        if pss_window <= 0:
            raise ValueError('pss_window must be greater than 0')
        if cool_down < 0:
            raise ValueError('cool_down must be greater than or equal to 0')
        if app_ran_header < 0:
            raise ValueError('ran_header must be greater than or equal to 0')
        GatewaysConfig.PSS_WINDOW = pss_window
        GatewaysConfig.COOL_DOWN = cool_down
        PacketConfig.RAN_HEADER = app_ran_header
        self.gateways: dict[str, GatewayConfig] = dict()

    def add_gateway(self, gateway_id: str, location: tuple[float, ...], wired: bool,
                    xh_trx: TransceiverConfig | None = None, acc_trx: TransceiverConfig | None = None):
        if gateway_id in self.gateways:
            raise ValueError(f'Gateway {gateway_id} already defined')
        self.gateways[gateway_id] = GatewayConfig(gateway_id, location, wired, xh_trx, acc_trx)
