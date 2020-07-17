from .fsm import Stateless
from abc import ABC, abstractmethod


class Multiplexer(Stateless, ABC):
    def __init__(self, name, node_id_list):
        super().__init__(name=name)
        self.node_id_list = node_id_list
        self.routing_table = dict()
        self.build_routing_table()

    def check_in_ports(self):
        """Processes incoming messages"""
        for in_port in self.in_ports:
            for msg in in_port.values:
                node_to = self.get_node_to(msg)
                assert node_to in self.node_id_list
                # Add message to buffer
                out_port = self.routing_table[in_port][node_to]
                self.add_msg_to_queue(out_port, msg)

    def process_internal_messages(self):
        """Processes internal messages (dummy)"""
        pass

    @abstractmethod
    def build_routing_table(self):
        """Build the routing table like this: {in_port: {node_to: {out_port}}"""
        pass

    @abstractmethod
    def get_node_to(self, msg):
        """Subtracts from routing message the node to ID"""
        pass
