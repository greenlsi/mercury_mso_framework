from xdevs.models import Port
from ..common import Multiplexer
from ..common.packet.physical import PhysicalPacket


class AccessPointRadioMultiplexer(Multiplexer):
    """
    Access Points-Radio layers Multiplexer
    :param str name: Access Layer-Radio Multiplexer name
    :param list ap_ids: ID of the Access Point module
    """
    def __init__(self, name, ap_ids):
        self.input_control_ul = Port(PhysicalPacket, name + '_input_control_ul')
        self.input_transport_ul = Port(PhysicalPacket, name + '_input_transport_ul')
        self.outputs_control_ul = {ap: Port(PhysicalPacket, name + '_output_control_ul_' + ap) for ap in ap_ids}
        self.outputs_transport_ul = {ap: Port(PhysicalPacket, name + '_output_transport_ul_' + ap) for ap in ap_ids}

        super().__init__(name, ap_ids)

        self.add_in_port(self.input_control_ul)
        self.add_in_port(self.input_transport_ul)
        [self.add_out_port(port) for port in self.outputs_control_ul.values()]
        [self.add_out_port(port) for port in self.outputs_transport_ul.values()]

    def build_routing_table(self):
        self.routing_table[self.input_control_ul] = dict()
        self.routing_table[self.input_transport_ul] = dict()
        for ap_id in self.node_id_list:
            self.routing_table[self.input_control_ul][ap_id] = self.outputs_control_ul[ap_id]
            self.routing_table[self.input_transport_ul][ap_id] = self.outputs_transport_ul[ap_id]

    def get_node_to(self, msg):
        return msg.node_to
