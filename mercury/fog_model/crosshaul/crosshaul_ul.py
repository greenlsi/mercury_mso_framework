from xdevs.models import Port
from ..common.network import Point2PointNetwork, Attenuator
from ..common.packet.physical import PhysicalPacket


class CrosshaulUpLink(Point2PointNetwork):
    """
    Crosshaul Uplink network xDEVS model
    :param str name: name of the xDEVS module
    :param dict aps_location: dictionary {AP_ID: AP location}
    :param dict edcs_location: dictionary {EDC ID: EDC location}
    :param dict fed_controller_location: dictionary {fed controller ID: fed controller location} (size 1)
    :param dict amf_location: dictionary {AMF ID: AMF location} (size 1)
    :param dict sdn_controller_location: dictionary {SDN controller ID: SDN controller location} (size 1)
    :param Attenuator ul_attenuator: attenuator to use for the crosshaul_config uplink
    :param float prop_speed: uplink propagation speed
    :param float penalty_delay: uplink penalty delay
    """
    def __init__(self, name, aps_location, edcs_location, fed_controller_location, amf_location,
                 sdn_controller_location, ul_frequency, ul_attenuator=None, prop_speed=0, penalty_delay=0):

        self.aps_location = aps_location
        self.edcs_location = edcs_location
        self.fed_controller_location = fed_controller_location
        self.amf_location = amf_location
        self.sdn_controller_location = sdn_controller_location

        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.output_ap_ul = Port(PhysicalPacket, name + '_output_ap_ul')
        self.output_edc_ul = Port(PhysicalPacket, name + '_output_edc_ul')
        self.output_fed_controller_ul = Port(PhysicalPacket, name + '_output_fed_controller_ul')
        self.output_amf_ul = Port(PhysicalPacket, name + '_output_amf_ul')
        self.output_sdn_controller_ul = Port(PhysicalPacket, name + '_output_sdn_controller_ul')

        nodes_location = {**aps_location, **edcs_location, **fed_controller_location, **amf_location,
                          **sdn_controller_location}
        super().__init__(name, nodes_location, ul_frequency, ul_attenuator, prop_speed, penalty_delay)

        self.add_in_port(self.input_crosshaul_ul)
        self.add_out_port(self.output_ap_ul)
        self.add_out_port(self.output_edc_ul)
        self.add_out_port(self.output_fed_controller_ul)
        self.add_out_port(self.output_amf_ul)
        self.add_out_port(self.output_sdn_controller_ul)

    def get_lookup_keys(self, phys_msg):
        return phys_msg.node_from, phys_msg.node_to

    def build_routing_table(self):
        for ap_id in self.aps_location:
            self.routing_table[ap_id] = self.output_ap_ul
        for edc_id in self.edcs_location:
            self.routing_table[edc_id] = self.output_edc_ul
        for fed_controller_id in self.fed_controller_location:
            self.routing_table[fed_controller_id] = self.output_fed_controller_ul
        for amf_id in self.amf_location:
            self.routing_table[amf_id] = self.output_amf_ul
        for sdn_controller_id in self.sdn_controller_location:
            self.routing_table[sdn_controller_id] = self.output_sdn_controller_ul
