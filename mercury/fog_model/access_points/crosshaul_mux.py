from xdevs.models import Port
from ..common import Multiplexer
from ..common.packet.physical import PhysicalPacket


class AccessPointCrosshaulMultiplexer(Multiplexer):
    """
    Access Points-Crosshaul layers multiplexer XDEVS module
    :param str name: Access-Crosshaul multiplexer module name
    :param list ap_ids: list of IDs of the APs that compose the access_points_config layer
    """
    def __init__(self, name, ap_ids):
        self.input_crosshaul_dl = Port(PhysicalPacket, name + '_input_crosshaul_dl')
        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.outputs_crosshaul_dl = {ap: Port(PhysicalPacket, name + '_output_crosshaul_dl_' + ap) for ap in ap_ids}
        self.outputs_crosshaul_ul = {ap: Port(PhysicalPacket, name + '_output_crosshaul_ul_' + ap) for ap in ap_ids}

        super().__init__(name, ap_ids)

        self.add_in_port(self.input_crosshaul_dl)
        self.add_in_port(self.input_crosshaul_ul)
        [self.add_out_port(port) for port in self.outputs_crosshaul_dl.values()]
        [self.add_out_port(port) for port in self.outputs_crosshaul_ul.values()]

    def build_routing_table(self):
        self.routing_table[self.input_crosshaul_dl] = dict()
        self.routing_table[self.input_crosshaul_ul] = dict()
        for ap_id in self.node_id_list:
            self.routing_table[self.input_crosshaul_dl][ap_id] = self.outputs_crosshaul_dl[ap_id]
            self.routing_table[self.input_crosshaul_ul][ap_id] = self.outputs_crosshaul_ul[ap_id]

    def get_node_to(self, msg):
        return msg.node_to
