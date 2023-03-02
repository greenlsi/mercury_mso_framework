from __future__ import annotations
from .network import LinkConfig, TransceiverConfig, NetworkConfig
# from ..cloud import CloudConfig
# from ..edcs import EdgeFederationConfig
from ..gateway import GatewaysConfig
from ..packet import PacketConfig


# TODO revisar esta parte
class CrosshaulConfig:
    def __init__(self, header: int = 0, connect_all: bool = True,
                 default_trx: TransceiverConfig = None, default_link: LinkConfig = None):
        """
        Crosshaul Network Layer configuration.
        :param header: size (in bits) of the physical packets of the crosshaul network.
        :param connect_all: if True, all the nodes are interconnected using the default link configuration.
        :param default_trx: Base Network transceiver configuration.
        :param default_link: Base Network link configuration.
        """
        PacketConfig.PHYS_XH_HEADER = header
        self.connect_all: bool = connect_all
        self.net_config: NetworkConfig = NetworkConfig('xh', default_trx, default_link)
        self.links: dict[str, dict[str, LinkConfig | None]] = dict()

    def add_link(self, node_from: str, node_to: str, link_config: LinkConfig | None, duplex: bool = False):
        link_config = self.net_config.default_link if link_config is None else link_config
        if node_from not in self.links:
            self.links[node_from] = dict()
        self.links[node_from][node_to] = link_config
        if duplex:
            self.add_link(node_to, node_from, link_config)

    def remove_link(self, node_from: str, node_to: str, duplex: bool = False):
        if node_from not in self.links:
            self.links[node_from] = dict()
        self.links[node_from][node_to] = None
        if duplex:
            self.remove_link(node_to, node_from)

    # def define_gateways(self, gws_config):
    def define_gateways(self, gws_config: GatewaysConfig):
        for gw_id, gw_config in gws_config.gateways.items():
            self.net_config.add_node(gw_config.xh_node)

    # def define_edcs(self, edcs_config: EdgeFederationConfig):
    def define_edcs(self, edcs_config):
        for edc_id, edc_config in edcs_config.edcs_config.items():
            self.net_config.add_node(edc_config.xh_node)

    def define_cloud(self, cloud_config):
        self.net_config.add_node(cloud_config.xh_node)

    def build(self):
        if self.connect_all:
            self.net_config.connect_all()
        for node_from, links in self.links.items():
            for node_to, link in links.items():
                if link is None:
                    self.net_config.remove_link(node_from, node_to)
                else:
                    self.net_config.add_link(node_from, node_to, link)
