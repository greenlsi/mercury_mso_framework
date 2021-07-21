from xdevs.models import Port
from typing import Set
from mercury.msg.network import NetworkPacket
from ...common import Multiplexer


class UEServiceMux(Multiplexer):

    def __init__(self, ue_id: str, services: Set[str]):
        self.service_ids = services

        self.input_network = Port(NetworkPacket, 'input_network')
        self.outputs_network = {service: Port(NetworkPacket, 'output_network_' + service) for service in services}

        super().__init__('iot_devices_{}_srv_mux'.format(ue_id), services)

        self.add_in_port(self.input_network)
        [self.add_out_port(port) for port in self.outputs_network.values()]

    def build_routing_table(self):
        """Fills the routing table with the correspondent links"""
        self.routing_table[self.input_network] = dict()
        for service_id in self.service_ids:
            self.routing_table[self.input_network][service_id] = self.outputs_network[service_id]

    def get_node_to(self, msg: NetworkPacket) -> str:
        """
        routes any service response message to the correspondent service
        :param msg: network packet
        """
        return msg.data.service_id
