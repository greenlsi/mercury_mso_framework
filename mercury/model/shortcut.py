from __future__ import annotations
from mercury.msg.packet import PacketInterface
from typing import Generic, Iterable, Type
from xdevs.models import Port
from .common import Multiplexer


class PacketMultiplexer(Multiplexer, Generic[PacketInterface]):
    def __init__(self, p_type: Type[PacketInterface], nodes: Iterable[str]):
        """
        Network communication layer multiplexer model
        :param p_type: data type of the input/output interface
        :param nodes: iterable with the IDs of all the fixed nodes in the scenario (e.g., APs, EDCs, or CNFs)
        """
        self.input_data: Port[PacketInterface] = Port(p_type, 'input_data')
        self.output_clients: Port[PacketInterface] = Port(p_type, 'output_data_clients')
        self.outputs_data: dict[str, Port[PacketInterface]] = dict()
        super().__init__('packet_mux')
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_clients)
        for node_id in nodes:
            self.outputs_data[node_id] = Port(p_type, f'output_data_{node_id}')
            self.add_out_port(self.outputs_data[node_id])

    def build_routing_table(self):
        self.routing_table[self.input_data] = self.outputs_data

    def get_node_to(self, msg: PacketInterface) -> str:
        return msg.node_to

    def catch_out_port_error(self, in_port: Port, node_to: str) -> Port:
        """If receiver node is not in the fixed nodes set, then the message is sent to the IoT devices layer"""
        return self.output_clients
