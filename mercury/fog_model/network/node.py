import logging
from typing import Any, Dict
from xdevs.models import Port, INFINITY
from ..common import Stateless, logging_overhead
from .mobility import NodeLocation, MobilityFactory


class TransceiverConfiguration:
    def __init__(self, tx_power: float = None, gain: float = 0, noise_name: str = None, noise_conf: Dict = None,
                 default_eff: float = 1, mcs_table: Dict[Any, float] = None):
        """
        :param tx_power: Transmitting power (in dBm)
        :param gain: Transmitting/receiving gain (in dB)
        :param noise_name:
        :param noise_conf:
        :param default_eff:
        :param mcs_table:
        """
        self.tx_power = tx_power
        self.gain = gain
        self.noise_name = noise_name
        if noise_conf is None:
            noise_conf = dict()
        self.noise_config = noise_conf
        self.default_eff = default_eff
        self.mcs_table = mcs_table


class NodeConfiguration:

    mobility_factory = MobilityFactory()

    def __init__(self, node_id: str, node_trx: TransceiverConfiguration = None, node_mobility_name: str = 'still',
                 **kwargs):
        """
        :param node_id:
        :param node_trx:
        :param node_mobility_name:
        :param node_mobility_config:
        """
        self.node_id = node_id
        self.node_trx = node_trx

        self.node_mobility = self.mobility_factory.create_mobility(node_mobility_name, **kwargs)
        self.initial_location = self.node_mobility.position

    def unpack(self):
        return self.node_id, self.initial_location, self.node_trx


class Nodes(Stateless):

    LOGGING_OVERHEAD = ""

    def __init__(self, name, nodes_config: Dict[str, NodeConfiguration]):
        """

        :param name:
        :param nodes_config:
        """
        self.nodes_mobility = dict()
        for node_id, node_config in nodes_config.items():
            self.nodes_mobility[node_id] = node_config.node_mobility

        self.nodes_location = dict()
        self.nodes_next_change = dict()
        for node_id, mobility in self.nodes_mobility.items():
            self.nodes_location[node_id] = mobility.position
            self.nodes_next_change[node_id] = mobility.get_next_sigma(0)

        super().__init__(self.get_next_event(0), name)

        self.input_repeat_location = Port(str, 'input_repeat_location')
        self.output_node_location = Port(NodeLocation, 'output_node_location')
        self.add_in_port(self.input_repeat_location)
        self.add_out_port(self.output_node_location)

    def clear_state(self):
        for node_id in self.nodes_next_change:
            if self.nodes_next_change[node_id] <= self._clock:
                self.nodes_location[node_id] = self.nodes_mobility[node_id].get_location_and_advance()
                self.nodes_next_change[node_id] = self._clock + self.nodes_mobility[node_id].get_next_sigma(self._clock)

    def check_in_ports(self):
        for node_id in self.input_repeat_location.values:
            self.add_msg_to_queue(self.output_node_location, NodeLocation(node_id, self.nodes_location[node_id]))

    def process_internal_messages(self):
        clock = self._clock
        # clock = self._clock + self.sigma  TODO cambiar a esto
        overhead = logging_overhead(clock, self.LOGGING_OVERHEAD)
        for node_id in self.nodes_next_change:
            if self.nodes_next_change[node_id] <= clock:
                logging.info(overhead + '{} moved to location {}'.format(node_id, self.nodes_location[node_id]))
                self.add_msg_to_queue(self.output_node_location, NodeLocation(node_id, self.nodes_location[node_id]))

    def get_next_event(self, t):
        return min([next_change - t for next_change in self.nodes_next_change.values()], default=INFINITY)

    def get_next_timeout(self):
        return 0 if not self.msg_queue_empty() else self.get_next_event(self._clock)
