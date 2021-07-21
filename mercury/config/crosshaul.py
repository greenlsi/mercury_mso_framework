from typing import Optional, Dict
from .network import PacketConfig, LinkConfig, NodeConfig, TransceiverConfig


class CrosshaulConfig:
    def __init__(self, base_link_config: Optional[LinkConfig] = None,
                 base_trx_config: Optional[TransceiverConfig] = None, header: int = 0):
        """
        Crosshaul Network Layer configuration.
        :param base_link_config: Base Network link configuration.
        :param base_trx_config: Base Network transceiver configuration.
        :param header: size (in bits) of the physical packets of the crosshaul network.
        """
        self.base_link_config: LinkConfig = LinkConfig() if base_link_config is None else base_link_config
        self.base_trx_config: TransceiverConfig = TransceiverConfig() if base_trx_config is None else base_trx_config
        PacketConfig.PHYS_XH_HEADER = header

        self.groups = ['edcs', 'aps', 'core']
        self.nodes = None
        self.built = False

        self.base_topology = {node_from: {node_to: self.base_link_config for node_to in self.groups}
                              for node_from in self.groups}

        self.detailed_topology = dict()

        self.built_topology = None

    def add_custom_config_from_group(self, group_from: str, link: Optional[LinkConfig]):
        for group_to in self.groups:
            self.add_custom_config_from_group_to_group(group_from, group_to, link)

    def add_custom_config_to_group(self, group_to: str, link: Optional[LinkConfig]):
        for group_from in self.groups:
            self.add_custom_config_from_group_to_group(group_from, group_to, link)

    def add_custom_config_from_group_to_group(self, group_from: str, group_to: str, link_config: Optional[LinkConfig]):
        if self.built:
            raise ValueError("Network is already built")
        self._check_groups(group_from, group_to)
        self.base_topology[group_from][group_to] = link_config

    def define_nodes(self, aps: Dict[str, NodeConfig], edcs: Dict[str, NodeConfig], core: Dict[str, NodeConfig]):
        if self.nodes is not None:
            raise ValueError("Nodes are already defined")
        self.nodes = {'aps': aps, 'edcs': edcs, 'core': core}
        for nodes in self.nodes.values():
            for node_config in nodes.values():
                if node_config.node_trx is None:
                    node_config.node_trx = self.base_trx_config
        # Enforce that there are no self-connections
        for node_id in (*aps, *edcs, *core):
            self.add_custom_config_from_node_to_node(node_id, node_id, None)

    def add_custom_config_from_node(self, node_from: str, link: Optional[LinkConfig]):
        for group, nodes in self.nodes.items():
            for node_to in nodes:
                if node_from != node_to:
                    self.add_custom_config_from_node_to_node(node_from, node_to, link)

    def add_custom_config_to_node(self, node_to: str, link: Optional[LinkConfig]):
        for group, nodes in self.nodes.items():
            for node_from in nodes:
                if node_from != node_to:
                    self.add_custom_config_from_node_to_node(node_from, node_to, link)

    def add_custom_config_from_node_to_group(self, node_from: str, group_to: str, link: Optional[LinkConfig]):
        self._check_groups(group_to)
        for node_to in self.nodes[group_to]:
            if node_from != node_to:
                self.add_custom_config_from_node_to_node(node_from, node_to, link)

    def add_custom_config_from_group_to_node(self, group_from: str, node_to: str, link: Optional[LinkConfig]):
        self._check_groups(group_from)
        for node_from in self.nodes[group_from]:
            if node_from != node_to:
                self.add_custom_config_from_node_to_node(node_from, node_to, link)

    def add_custom_config_from_node_to_node(self, node_from: str, node_to: str, link: Optional[LinkConfig]):
        if self.built:
            raise ValueError("Network is already built")
        self._check_nodes(node_from, node_to)
        if node_from == node_to and link is not None:
            raise ValueError("Self-connections are forbidden")
        if node_from not in self.detailed_topology:
            self.detailed_topology[node_from] = dict()
        self.detailed_topology[node_from][node_to] = link

    def _check_groups(self, *args: str):
        for arg in args:
            if arg not in self.groups:
                raise ValueError('Group not found. It must be either "edcs" (Edge Data Centers), '
                                 '"aps" (Access Points), or "core" (Any Core network function)')

    def _check_nodes(self, *args: str):
        for arg in args:
            hit = False
            for group_id, nodes in self.nodes.items():
                for node_id in nodes:
                    if node_id == arg:
                        hit = True
                        break
                if hit:
                    break
            if not hit:
                raise ValueError("Node not found. It must be defined either as an EDC, an AP, or a CNF")

    def build_network(self):
        node_list = list()
        for group_id, nodes in self.nodes.items():
            for node_id in nodes:
                if node_id in node_list:
                    raise ValueError("Node IDs must be unique")
                node_list.append(node_id)

        self.built_topology = {node_from: {node_to: None for node_to in node_list} for node_from in node_list}

        for group_from, nodes_from in self.nodes.items():
            for group_to, nodes_to in self.nodes.items():
                for node_from in nodes_from:
                    for node_to in nodes_to:
                        if node_from in self.detailed_topology and node_to in self.detailed_topology[node_from]:
                            self.built_topology[node_from][node_to] = self.detailed_topology[node_from][node_to]
                        else:
                            self.built_topology[node_from][node_to] = self.base_topology[group_from][group_to]
        # Remove empty links
        for node_from in node_list:
            for node_to in node_list:
                if self.built_topology[node_from][node_to] is None:
                    self.built_topology[node_from].pop(node_to)
            if not self.built_topology[node_from]:
                self.built_topology.pop(node_from)

    def get_built_network(self):
        if not self.built:
            self.build_network()
        return self.built_topology
