from xdevs.models import Port
from .fsm import ExtendedAtomic
from abc import ABC, abstractmethod


class Multiplexer(ExtendedAtomic, ABC):
    def __init__(self, name: str, nodes_ids: set):
        super().__init__(name=name)
        self.node_ids = nodes_ids
        self.routing_table = dict()
        self.build_routing_table()

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        """Processes incoming messages"""
        for in_port in self.in_ports:
            for msg in in_port.values:
                node_to = self.get_node_to(msg)
                try:
                    out_port = self.routing_table[in_port][node_to]
                except KeyError:    # If mux cannot find a right output port, we try to catch the exception
                    out_port = self.catch_out_port_error(in_port, node_to)
                self.add_msg_to_queue(out_port, msg)
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def catch_out_port_error(self, in_port: Port, node_to: str) -> Port:
        """If mux cannot find the right out port, user can define what to do. By default, it throws an exception"""
        raise KeyError

    @abstractmethod
    def build_routing_table(self):
        """Build the routing table like this: {in_port: {node_to: {out_port}}"""
        pass

    @abstractmethod
    def get_node_to(self, msg):
        """Subtracts from routing message the node to ID"""
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
