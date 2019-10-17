from xdevs.models import Port
from ..common import Multiplexer
from ..common.packet.physical import PhysicalPacket


class EdgeDataCenterMultiplexer(Multiplexer):
    """
    Multiplexer for Edge Data Centers incoming messages
    :param str name: Name of the xDEVS module
    :param list edc_ids: list of Edge Data Centers IDs
    """

    def __init__(self, name, edc_ids):
        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul')
        self.outputs_crosshaul_ul = {edc: Port(PhysicalPacket, name + '_output_crosshaul_ul_' + edc) for edc in edc_ids}

        super().__init__(name, edc_ids)

        self.add_in_port(self.input_crosshaul_ul)
        [self.add_out_port(port) for port in self.outputs_crosshaul_ul.values()]

    def build_routing_table(self):
        self.routing_table[self.input_crosshaul_ul] = dict()
        for edc_id in self.node_id_list:
            self.routing_table[self.input_crosshaul_ul][edc_id] = self.outputs_crosshaul_ul[edc_id]

    def get_node_to(self, msg):
        return msg.node_to
