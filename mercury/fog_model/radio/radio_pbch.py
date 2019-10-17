from xdevs.models import Port
from ..common.network import BroadcastNetwork, Attenuator
from ..common.packet.physical import PhysicalPacket


class PhysicalBroadcastChannel(BroadcastNetwork):
    """
    Radio PBCH xDEVS model
    :param str name: name of the xDEVS module
    :param dict aps_location: dictionary {AP_ID: AP location}
    :param dict ues_location: dictionary {UE ID: UE location}
    :param float frequency: carrier frequency used by the PBCH
    :param Attenuator attenuator: attenuator to use for the radio channel
    :param float prop_speed: radio propagation speed
    :param float penalty_delay: radio penalty delay
    """
    def __init__(self, name, aps_location, ues_location, frequency, attenuator=None, prop_speed=0,
                 penalty_delay=0):
        self.ues_location = ues_location
        nodes_location = {**aps_location, **ues_location}

        self.input_radio_bc = Port(PhysicalPacket, name + '_input_radio_bc')
        self.output_radio_bc = Port(PhysicalPacket, name + '_output_radio_bc')

        super().__init__(name, nodes_location, ues_location, frequency, attenuator, prop_speed, penalty_delay)

        self.add_in_port(self.input_radio_bc)
        self.add_out_port(self.output_radio_bc)

    def get_lookup_keys(self, phys_msg):
        return phys_msg.node_to, phys_msg.node_from

    def build_routing_table(self):
        for ue_id in self.ues_location:
            self.routing_table[ue_id] = self.output_radio_bc
