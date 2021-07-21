from xdevs.models import Coupled, Port
from typing import Dict
from mercury.config.core import CoreConfig
from mercury.config.network import NodeConfig
from mercury.config.crosshaul import CrosshaulConfig
from mercury.msg.network import CrosshaulPacket, NetworkLinkReport
from .common import Multiplexer
from .network import Network


class CrosshaulMux(Multiplexer):
    def __init__(self, name, nodes):
        self.nodes = nodes
        self.input_data = Port(CrosshaulPacket, 'input_data')
        self.outputs_data = {node_id: Port(CrosshaulPacket, 'output_data_' + node_id) for node_id in self.nodes}
        super().__init__(name, self.nodes)
        self.add_in_port(self.input_data)
        [self.add_out_port(output_data) for output_data in self.outputs_data.values()]

    def build_routing_table(self):
        self.routing_table[self.input_data] = {node_id: self.outputs_data[node_id] for node_id in self.nodes}

    def get_node_to(self, msg):
        return msg.node_to


class Crosshaul(Coupled):  # TODO ver cómo hacer la red custom
    def __init__(self, crosshaul_config: CrosshaulConfig, aps: Dict[str, NodeConfig],
                 edcs: Dict[str, NodeConfig], core_config: CoreConfig):
        """
        Crosshaul Layer xDEVS module

        :param crosshaul_config: Crosshaul Layer configuration
        :param aps: Information regarding APs
        :param edcs: Information regarding EDCs
        :param core_config: Core Network configuration.
        """
        core_nodes = {CoreConfig.CORE_ID: core_config.node}

        nodes = {**aps, **edcs, **core_nodes}
        assert len(nodes) == len(aps) + len(edcs) + len(core_nodes)

        super().__init__('crosshaul')

        self.input_data = Port(CrosshaulPacket, 'input_data')
        self.output_link_report = Port(NetworkLinkReport, 'output_link_report')
        self.outputs_data = {node_id: Port(CrosshaulPacket, 'output_data_' + node_id) for node_id in nodes}

        self.add_in_port(self.input_data)
        self.add_out_port(self.output_link_report)
        [self.add_out_port(self.outputs_data[node_id]) for node_id in nodes]

        for node_config in nodes.values():
            if node_config.node_trx is None:
                node_config.node_trx = crosshaul_config.base_trx_config

        crosshaul_config.define_nodes(aps, edcs, core_nodes)
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

        network = Network(nodes, crosshaul_config.base_link_config, fixed_topology=topology, name='crosshaul')
        self.add_component(network)
        self.add_coupling(self.input_data, network.input_data)
        self.add_coupling(network.output_link_report, self.output_link_report)

        mux = CrosshaulMux('crosshaul_mux', nodes)
        self.add_component(mux)
        self.add_coupling(network.output_data, mux.input_data)
        [self.add_coupling(mux.outputs_data[node_id], self.outputs_data[node_id]) for node_id in nodes]
