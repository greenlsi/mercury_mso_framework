from xdevs.models import Port
from mercury.fog_model.common import Multiplexer
from ...common.packet.apps.service import ServiceResponse
from ...common.packet.packet import NetworkPacket


class UEServiceMux(Multiplexer):

    def __init__(self, name, service_ids):
        self.service_ids = service_ids

        self.input_network = Port(NetworkPacket, name + '_input_network')
        self.outputs_network = {service: Port(NetworkPacket, name + '_output_network_' + service)
                                for service in service_ids}

        super().__init__(name, service_ids)

        self.add_in_port(self.input_network)
        [self.add_out_port(port) for port in self.outputs_network.values()]

    def build_routing_table(self):
        """Fills the routing table with the correspondent links"""
        self.routing_table[self.input_network] = dict()
        for service_id in self.service_ids:
            self.routing_table[self.input_network][service_id] = self.outputs_network[service_id]

    def get_node_to(self, msg):
        """
        routes any service response message to the correspondent service
        :param NetworkPacket msg: network packet
        """
        app_msg = msg.data
        assert isinstance(app_msg, ServiceResponse)
        return app_msg.service_id
