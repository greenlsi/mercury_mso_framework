from __future__ import annotations
from math import inf
from mercury.config.network import DynamicNodeConfig, WirelessNodeConfig
from mercury.logger import logger as logging, logging_overhead
from mercury.msg.network import NewNodeLocation
from xdevs.models import Port
from ..common import ExtendedAtomic


class MobilityManager(ExtendedAtomic):
    LOGGING_OVERHEAD = ''

    def __init__(self):
        super().__init__(name='mobility_manager')
        self.wireless_nodes: dict[str, WirelessNodeConfig] = dict()
        self.input_create_node: Port[DynamicNodeConfig] = Port(DynamicNodeConfig, 'input_create_node')
        self.input_remove_node: Port[str] = Port(str, 'input_remove_node')
        self.output_new_location: Port[NewNodeLocation] = Port(NewNodeLocation, 'output_new_location')
        self.add_in_port(self.input_create_node)
        self.add_in_port(self.input_remove_node)
        self.add_out_port(self.output_new_location)

    def deltint_extension(self):
        next_t = inf
        for node_config in self.wireless_nodes.values():
            mobility = node_config.mobility
            if mobility.next_t <= self._clock < node_config.t_end:
                mobility.advance()
            if mobility.next_t < node_config.t_end:
                next_t = min(next_t, mobility.next_t)
        self.sigma = next_t - self._clock

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        for node_id in self.input_remove_node.values:
            self.remove_node(overhead, node_id)
        for node_config in self.input_create_node.values:
            self.create_node(overhead, node_config)
        next_t = inf
        for config in self.wireless_nodes.values():
            if config.mobility.next_t < config.t_end:
                next_t = min(next_t, config.mobility.next_t)
        self.sigma = next_t - self._clock

    def remove_node(self, overhead: str, node_id: str):
        self.wireless_nodes.pop(node_id, None)
        logging.info(f'{overhead}MOBILITY MANAGER: node {node_id} removed')

    def create_node(self, overhead: str, node_config: DynamicNodeConfig):
        node_id = node_config.node_id
        if isinstance(node_config, WirelessNodeConfig):
            if node_config.mobility.next_t != self._clock:
                next_t = node_config.mobility.next_t
                logging.error(f'{overhead}MOBILITY MANAGER: time coherence error in node {node_id} ({next_t})')
                raise AssertionError('time coherence error: new node was not created when required')
            self.wireless_nodes[node_config.node_id] = node_config
        logging.info(f'{overhead}MOBILITY MANAGER: node {node_id} created')

    def lambdaf_extension(self):
        clock = self._clock + self.sigma
        overhead = logging_overhead(clock, self.LOGGING_OVERHEAD)
        for node_id, node_config in self.wireless_nodes.items():
            mobility = node_config.mobility
            if mobility.next_t <= clock < node_config.t_end:
                while mobility.next_t <= clock:
                    mobility.advance()
                logging.info(f'{overhead}MOBILITY MANAGER: node {node_id} moved to location {mobility.location}')
                self.output_new_location.add(NewNodeLocation(node_id, mobility.location))

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
