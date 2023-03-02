from __future__ import annotations
from abc import ABC
from typing import Any


class LinkConfig:
    def __init__(self, bandwidth: float = 0, carrier_freq: float = 0, prop_speed: float = 0, penalty_delay: float = 0,
                 loss_prob: float = 0, att_id: str | None = None, att_config: dict[str, Any] | None = None,
                 noise_id: str | None = None, noise_config: dict[str, Any] | None = None):
        """
        Configuration of a communication link.
        :param bandwidth: Total available bandwidth of the link (in Hz).
        :param carrier_freq: Carrier Frequency used for transmitting messages (in Hz).
        :param prop_speed: Physical propagation speed of the link (in m/s).
        :param penalty_delay: Fixed delay to be applied to messages sent through the link (in s).
        :param loss_prob: Packet loss probability (0 if no loss occurs, 1 if all the packets are lost).
        :param att_id: Name of the attenuation function to be applied to messages sent through the link.
        :param att_config: Attenuation function configuration parameters.
        :param noise_id: Name of the noise function to be applied to messages sent through the link.
        :param noise_config: Noise function configuration parameters.
        """
        if bandwidth < 0:
            raise ValueError(f'Invalid value for bandwidth({bandwidth})')
        if carrier_freq < 0:
            raise ValueError(f'Invalid value for carrier_freq ({carrier_freq})')
        if prop_speed < 0:
            raise ValueError(f'Invalid value for prop_speed ({prop_speed})')
        if penalty_delay < 0:
            raise ValueError(f'Invalid value for penalty_delay ({penalty_delay})')
        if 0 > loss_prob > 1:
            raise ValueError(f'Invalid value for loss_prob ({loss_prob})')
        self.bandwidth: float = bandwidth
        self.carrier_freq: float = carrier_freq
        self.prop_speed: float = prop_speed
        self.penalty_delay: float = penalty_delay
        self.loss_prob: float = loss_prob
        self.att_id: str | None = att_id
        self.att_config: dict[str, Any] = dict() if att_config is None else att_config
        self.noise_id: str | None = noise_id
        self.noise_config: dict[str, Any] = dict() if noise_config is None else noise_config


class TransceiverConfig:
    def __init__(self, tx_power: float | None = None, gain: float | None = 0, noise_id: str | None = None,
                 noise_config: dict[str, Any] = None, mcs_list: list[float] | None = None):
        """
        Configuration of network transceiver.
        :param tx_power: Transmitting power (in dBm).
        :param gain: Transmitting/receiving gain (in dB).
        :param noise_id: Name of the noise function to be applied to messages sent through the link.
        :param noise_config: Noise function configuration parameters.
        :param mcs_list: Available Modulation and Codification Schemes. If None, it uses the maximum theoretical limit.
        """
        self.tx_power: float | None = tx_power
        self.gain: float | None = gain
        self.noise_id: str | None = noise_id
        self.noise_config: dict[str, Any] = dict() if noise_config is None else noise_config
        self.mcs_table: list[float] | None = mcs_list


class NetworkNodeConfig(ABC):
    def __init__(self, node_id: str, location: tuple[float, ...], trx_config: TransceiverConfig | None = None):
        """
        Configuration of network node.
        :param node_id: ID of the node.
        :param location: Physical location in (x, y) of the network node.
        :param trx_config: Network node transceiver configuration.
        """
        self.node_id: str = node_id
        self.location: tuple[float, ...] = location
        self.trx: TransceiverConfig | None = trx_config

    def unpack(self) -> tuple[str, tuple[float, ...], TransceiverConfig]:
        return self.node_id, self.location, self.trx


class StaticNodeConfig(NetworkNodeConfig):
    pass


class GatewayNodeConfig(StaticNodeConfig, ABC):
    pass


class WiredGatewayNodeConfig(GatewayNodeConfig):
    pass


class WirelessGatewayNodeConfig(GatewayNodeConfig):
    pass


class DynamicNodeConfig(NetworkNodeConfig, ABC):
    def __init__(self, node_id: str, t_start: float, t_end: float, location: tuple[float, ...],
                 trx_config: TransceiverConfig | None = None, keep_connected: bool = True):
        if t_end <= t_start < 0:
            raise ValueError(f'invalid values for t_start ({t_start}) and t_end ({t_end})')
        super().__init__(node_id, location, trx_config)
        self.t_start: float = t_start
        self.t_end: float = t_end
        self.keep_connected: bool = keep_connected

    @property
    def wireless(self) -> bool:
        return isinstance(self, WirelessNodeConfig)


class WiredNodeConfig(DynamicNodeConfig):
    def __init__(self, node_id: str, gateway_id: str, t_start: float, t_end: float, location: tuple[float, ...],
                 trx_config: TransceiverConfig | None = None,
                 dl_link_config: LinkConfig | None = None, ul_link_config: LinkConfig | None = None):
        super().__init__(node_id, t_start, t_end, location, trx_config)
        self.gateway_id: str = gateway_id
        self.dl_link_config: LinkConfig | None = dl_link_config
        self.ul_link_config: LinkConfig | None = ul_link_config


class WirelessNodeConfig(DynamicNodeConfig):
    def __init__(self, node_id: str, t_start: float, t_end: float, mobility_id: str, mobility_config: dict[str, Any],
                 trx_config: TransceiverConfig | None = None, keep_connected: bool = True):
        from mercury.plugin import AbstractFactory, NodeMobility
        mobility_config = {**mobility_config, 't_start': t_start, 't_end': t_end}
        self.mobility: NodeMobility = AbstractFactory.create_mobility(mobility_id, **mobility_config)
        super().__init__(node_id, t_start, t_end, self.mobility.location, trx_config, keep_connected)


class NetworkConfig:
    def __init__(self, network_id: str, default_trx: TransceiverConfig | None = None,
                 default_link: LinkConfig | None = None):
        self.network_id: str = network_id
        self.default_trx: TransceiverConfig = TransceiverConfig() if default_trx is None else default_trx
        self.default_link: LinkConfig = LinkConfig() if default_link is None else default_link
        self.nodes: dict[str, StaticNodeConfig] = dict()
        self.links: dict[str, dict[str, LinkConfig]] = dict()

    def add_node(self, node: StaticNodeConfig):
        if node.node_id in self.nodes:
            raise ValueError(f'Network node with ID {node.node_id} already exists in network {self.network_id}')
        if node.trx is None:
            node.trx = self.default_trx
        self.nodes[node.node_id] = node

    def add_link(self, node_from: str, node_to: str, link_config: LinkConfig | None = None):
        if node_from not in self.nodes:
            raise ValueError(f'Node {node_from} does not exist in network {self.network_id}')
        if node_to not in self.nodes:
            raise ValueError(f'Node {node_to} does not exist in network {self.network_id}')
        if node_from == node_to:
            raise ValueError(f'Links from one node to itself are not allowed')
        if link_config is None:
            link_config = self.default_link
        if node_from not in self.links:
            self.links[node_from] = dict()
        self.links[node_from][node_to] = link_config

    def remove_link(self, node_from: str, node_to: str):
        if node_from in self.links and node_to in self.links[node_from]:
            self.links[node_from].pop(node_to)
            if not self.links[node_from]:
                self.links.pop(node_from)

    def connect_all(self, link_config: LinkConfig | None = None):
        if link_config is None:
            link_config = self.default_link
        node_list = list(self.nodes)
        for i in range(len(node_list)):
            for j in range(i + 1, len(node_list)):
                self.add_link(node_list[i], node_list[j], link_config)
                self.add_link(node_list[j], node_list[i], link_config)
