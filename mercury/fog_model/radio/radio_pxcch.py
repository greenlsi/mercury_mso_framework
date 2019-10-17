from xdevs.models import Port
from ..common.network import Point2PointNetwork, Attenuator
from ..common.packet.physical import PhysicalPacket


class PhysicalControlChannel(Point2PointNetwork):
    """
    Radio PUCCH and PDCCH xDEVS model
    :param str name: name of the xDEVS module
    :param dict aps_location: dictionary {AP_ID: AP location}
    :param dict ues_location: dictionary {UE ID: UE location}
    :param float frequency: carrier frequency used by the PXCCH
    :param Attenuator attenuator: attenuator to use for the radio channels
    :param float prop_speed: radio propagation speed
    :param float penalty_delay: radio penalty delay
    """
    def __init__(self, name, aps_location, ues_location, frequency, attenuator=None, prop_speed=0,
                 penalty_delay=0):
        self.ues_location = ues_location
        self.aps_location = aps_location
        nodes_location = {**aps_location, **ues_location}

        self.input_radio_pxcch = Port(PhysicalPacket, name + '_input_radio_pxcch')
        self.output_radio_pucch = Port(PhysicalPacket, name + '_output_radio_pucch')
        self.output_radio_pdcch = Port(PhysicalPacket, name + '_output_radio_pdcch')

        super().__init__(name, nodes_location, frequency, attenuator, prop_speed, penalty_delay)

        self.add_in_port(self.input_radio_pxcch)
        self.add_out_port(self.output_radio_pucch)
        self.add_out_port(self.output_radio_pdcch)

    def get_lookup_keys(self, phys_msg):
        if phys_msg.node_from in self.ues_location:
            return phys_msg.node_from, phys_msg.node_to
        else:
            return phys_msg.node_to, phys_msg.node_from

    def build_routing_table(self):
        for ue_id in self.ues_location:
            self.routing_table[ue_id] = self.output_radio_pdcch
        for ap_id in self.aps_location:
            self.routing_table[ap_id] = self.output_radio_pucch
