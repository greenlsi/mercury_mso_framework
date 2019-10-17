from xdevs.models import Port
from ..common.network import Point2PointNetwork
from ..common.packet.physical import PhysicalPacket


class CrosshaulDownLink(Point2PointNetwork):
    """
    Crosshaul Downlink network xDEVS model
    :param str name: name of the xDEVS module
    :param dict aps_location: dictionary {AP_ID: AP location}
    :param dict edcs_location: dictionary {EDC ID: EDC location}
    :param dict amf_location: dictionary {AMF ID: AMF location} (size 1)
    :param dict sdn_controller_location: dictionary {SDN controller ID: SDN controller location} (size 1)
    :param Attenuator dl_attenuator: attenuator to use for the crosshaul_config downlink
    :param float prop_speed: downlink propagation speed
    :param float penalty_delay: downlink penalty delay
    """
    def __init__(self, name, aps_location, edcs_location, amf_location, sdn_controller_location, dl_frequency,
                 dl_attenuator=None, prop_speed=0, penalty_delay=0):

        self.aps_location = aps_location

        self.input_crosshaul_dl = Port(PhysicalPacket, name + '_input_crosshaul_dl')
        self.output_ap_dl = Port(PhysicalPacket, name + '_output_ap_dl')

        nodes_location = {**aps_location, **edcs_location, **amf_location, **sdn_controller_location}
        super().__init__(name, nodes_location, dl_frequency, dl_attenuator, prop_speed, penalty_delay)

        self.add_in_port(self.input_crosshaul_dl)
        self.add_out_port(self.output_ap_dl)

    def get_lookup_keys(self, phys_msg):
        return phys_msg.node_to, phys_msg.node_from

    def build_routing_table(self):
        for ap_id in self.aps_location:
            self.routing_table[ap_id] = self.output_ap_dl
