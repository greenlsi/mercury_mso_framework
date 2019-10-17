from xdevs.models import Port
from ..common import Multiplexer
from ..common.packet.physical import PhysicalPacket


class UserEquipmentMultiplexer(Multiplexer):
    """
    User Equipment multiplexer xDEVS module

    :param str name: Name of the xDEVS module
    :param list ue_id_list: ID list of all the UEs that comprise the scenario
    """

    def __init__(self, name, ue_id_list):
        self.ue_ids = ue_id_list

        self.input_radio_bc = Port(PhysicalPacket, name + '_input_radio_bc')
        self.input_radio_control_dl = Port(PhysicalPacket, name + '_input_radio_control_dl')
        self.input_radio_transport_dl = Port(PhysicalPacket, name + '_input_radio_transport_dl')
        self.outputs_radio_bc = {ue_id: Port(PhysicalPacket, name + '_output_radio_bc_' + ue_id)
                                 for ue_id in ue_id_list}
        self.outputs_radio_control_dl = {ue_id: Port(PhysicalPacket, name + '_output_radio_control_dl_' + ue_id)
                                         for ue_id in ue_id_list}
        self.outputs_radio_transport_dl = {ue_id: Port(PhysicalPacket, name + '_output_radio_transport_dl_' + ue_id)
                                           for ue_id in ue_id_list}

        super().__init__(name, ue_id_list)

        self.add_in_port(self.input_radio_bc)
        self.add_in_port(self.input_radio_control_dl)
        self.add_in_port(self.input_radio_transport_dl)
        [self.add_out_port(port) for port in self.outputs_radio_bc.values()]
        [self.add_out_port(port) for port in self.outputs_radio_control_dl.values()]
        [self.add_out_port(port) for port in self.outputs_radio_transport_dl.values()]

    def build_routing_table(self):
        self.routing_table[self.input_radio_bc] = dict()
        self.routing_table[self.input_radio_control_dl] = dict()
        self.routing_table[self.input_radio_transport_dl] = dict()
        for ue_id in self.ue_ids:
            self.routing_table[self.input_radio_bc][ue_id] = self.outputs_radio_bc[ue_id]
            self.routing_table[self.input_radio_control_dl][ue_id] = self.outputs_radio_control_dl[ue_id]
            self.routing_table[self.input_radio_transport_dl][ue_id] = self.outputs_radio_transport_dl[ue_id]

    def get_node_to(self, msg):
        return msg.node_to
