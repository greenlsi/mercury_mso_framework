from xdevs.models import Coupled, Port
from .network import NodeLocation, Network, LinkConfiguration, TransceiverConfiguration, NodeConfiguration,\
    NetworkLinkReport, Nodes
from .common.packet.packet import PhysicalPacket
from typing import Union, Dict


class CrosshaulConfiguration:
    def __init__(self, base_link_config: LinkConfiguration = None, base_trx_config: TransceiverConfiguration = None):
        """

        :param base_link_config:
        :param base_trx_config:
        """
        if base_link_config is None:
            base_link_config = LinkConfiguration()
        self.base_link_config = base_link_config
        self.header = self.base_link_config.header

        if base_trx_config is None:
            base_trx_config = TransceiverConfiguration()
        self.base_transceiver_config = base_trx_config

        self.groups = ['edcs', 'aps', 'core']
        self.nodes = None
        self.built = False

        self.base_topology = {node_from: {node_to: self.base_link_config for node_to in self.groups}
                              for node_from in self.groups}

        self.detailed_topology = dict()

        self.built_topology = None

    def add_custom_config_from_group(self, group_from: str, link: Union[LinkConfiguration, None]):
        for group_to in self.groups:
            self.add_custom_config_from_group_to_group(group_from, group_to, link)

    def add_custom_config_to_group(self, group_to: str, link: Union[LinkConfiguration, None]):
        for group_from in self.groups:
            self.add_custom_config_from_group_to_group(group_from, group_to, link)

    def add_custom_config_from_group_to_group(self, group_from: str, group_to: str,
                                              link_config: Union[LinkConfiguration, None]):
        if self.built:
            raise ValueError("Network is already built")
        self._check_groups(group_from, group_to)
        self.base_topology[group_from][group_to] = link_config

    def define_nodes(self, aps: Dict[str, NodeConfiguration], edcs: Dict[str, NodeConfiguration],
                     core: Dict[str, NodeConfiguration]):
        if self.nodes is not None:
            raise ValueError("Nodes are already defined")
        self.nodes = {'aps': aps, 'edcs': edcs, 'core': core}
        for nodes in self.nodes.values():
            for node_config in nodes.values():
                if node_config.node_trx is None:
                    node_config.node_trx = self.base_transceiver_config
        # Enforce that there are no self-connections
        for node_id in (*aps, *edcs, *core):
            self.add_custom_config_from_node_to_node(node_id, node_id, None)

    def add_custom_config_from_node(self, node_from: str, link: Union[None, LinkConfiguration]):
        for group, nodes in self.nodes.items():
            for node_to in nodes:
                if node_from != node_to:
                    self.add_custom_config_from_node_to_node(node_from, node_to, link)

    def add_custom_config_to_node(self, node_to: str, link: Union[None, LinkConfiguration]):
        for group, nodes in self.nodes.items():
            for node_from in nodes:
                if node_from != node_to:
                    self.add_custom_config_from_node_to_node(node_from, node_to, link)

    def add_custom_config_from_node_to_group(self, node_from: str, group_to: str,
                                             link: Union[None, LinkConfiguration]):
        self._check_groups(group_to)
        for node_to in self.nodes[group_to]:
            if node_from != node_to:
                self.add_custom_config_from_node_to_node(node_from, node_to, link)

    def add_custom_config_from_group_to_node(self, group_from: str, node_to: str,
                                             link: Union[None, LinkConfiguration]):
        self._check_groups(group_from)
        for node_from in self.nodes[group_from]:
            if node_from != node_to:
                self.add_custom_config_from_node_to_node(node_from, node_to, link)

    def add_custom_config_from_node_to_node(self, node_from: str, node_to: str, link: Union[None, LinkConfiguration]):
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
                raise ValueError("Node not found. It must be defined either as an EDC, an AP, or a Core Network Function")

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


class Crosshaul(Coupled):  # TODO ver cómo hacer la red custom
    def __init__(self, name: str, crosshaul_config: CrosshaulConfiguration, aps: Dict[str, NodeConfiguration],
                 edcs: Dict[str, NodeConfiguration], core: Dict[str, NodeConfiguration]):
        """
        Crosshaul Layer xDEVS module

        :param name: Crosshaul layer module name
        :param crosshaul_config: Crosshaul Layer configuration
        :param aps: Information regarding APs
        :param edcs: Information regarding EDCs
        :param core: Information regarding Core Network Functions
        """

        super().__init__(name)

        nodes = {**aps, **edcs, **core}
        assert len(nodes) == len(aps) + len(edcs) + len(core)

        default_link = crosshaul_config.base_link_config
        default_transceiver = crosshaul_config.base_transceiver_config
        if default_transceiver is None:
            default_transceiver = TransceiverConfiguration()
        for node_config in nodes.values():
            if node_config.node_trx is None:
                node_config.node_trx = default_transceiver

        crosshaul_config.define_nodes(aps, edcs, core)
        topology = crosshaul_config.get_built_network()

        # Check that there are not isolated nodes
        for node_id in nodes:
            assert node_id in topology
        nodes_id = list(nodes.keys())
        for node_from, links in topology.items():
            for node_to in links:
                if node_to in nodes_id:
                    nodes_id.remove(node_to)
        assert not nodes_id

        self.input_repeat_location = Port(str, "input_repeat_location")
        self.input_data = Port(PhysicalPacket, "input_data")
        self.output_node_location = Port(NodeLocation, "output_node_location")
        self.output_link_report = Port(NetworkLinkReport, "output_link_report")
        self.add_in_port(self.input_repeat_location)
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_node_location)
        self.add_out_port(self.output_link_report)
        self.outputs_node_to = dict()
        for node_id in nodes:
            self.outputs_node_to[node_id] = Port(PhysicalPacket, "output_to_" + node_id)
            self.add_out_port(self.outputs_node_to[node_id])

        # Components
        links = Network(name + '_links', nodes, default_link, topology)
        nodes_mobility = Nodes(name + '_nodes', nodes)
        self.add_component(links)
        self.add_component(nodes_mobility)

        self.add_coupling(nodes_mobility.output_node_location, links.input_node_location)

        self.add_coupling(self.input_repeat_location, nodes_mobility.input_repeat_location)
        self.add_coupling(self.input_data, links.input_data)
        self.add_coupling(nodes_mobility.output_node_location, self.output_node_location)
        self.add_coupling(links.output_link_report, self.output_link_report)

        for node_id in nodes:
            self.add_coupling(links.outputs_node_to[node_id], self.outputs_node_to[node_id])
