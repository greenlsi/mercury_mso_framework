from typing import Dict
from ..network import EnableChannels
from xdevs.models import Coupled, Port
from ..common.packet.packet import PhysicalPacket, NetworkPacketConfiguration
from ..common.packet.apps.ran import RadioAccessNetworkConfiguration
from .ap import AccessPoint, AccessPointConfiguration


class AccessPoints(Coupled):
    """
    Access Points layer xDEVS module.

    :param name: name of the DEVS module
    :param aps_config: Access Points configuration list {AP ID: AP configuration}
    :param amf_id: ID of the AMF core function
    :param rac_config: radio pxcch network configuration
    :param network_config: network packet configuration
    """
    def __init__(self, name: str, aps_config: Dict[str, AccessPointConfiguration], amf_id: str,
                 rac_config: RadioAccessNetworkConfiguration, network_config: NetworkPacketConfiguration):
        super().__init__(name)
        # Unwrap configuration parameters
        self.ap_ids = [a for a in aps_config]
        if len(self.ap_ids) != len(set(self.ap_ids)):
            raise ValueError('AP IDs must be unique')

        # Create submodules and add them to the coupled model
        aps = {ap_id: AccessPoint(name + '_ap_' + ap_id, ap_config, amf_id, rac_config, network_config)
               for ap_id, ap_config in aps_config.items()}

        [self.add_component(ap) for ap in aps.values()]

        # Handy ports
        self.input_repeat_pss = Port(str, 'input_new_ue_location')
        self.output_connected_ues = Port(EnableChannels, 'output_connected_ues')
        self.output_crosshaul = Port(PhysicalPacket, 'output_crosshaul')
        self.output_radio_bc = Port(PhysicalPacket, 'output_radio_bc')
        self.output_radio_control_dl = Port(PhysicalPacket, 'output_radio_control')
        self.output_radio_transport_dl = Port(PhysicalPacket, 'output_radio_transport')

        self.add_in_port(self.input_repeat_pss)
        self.add_out_port(self.output_connected_ues)
        self.add_out_port(self.output_crosshaul)
        self.add_out_port(self.output_radio_bc)
        self.add_out_port(self.output_radio_control_dl)
        self.add_out_port(self.output_radio_transport_dl)

        # Crosshaul-related input/output ports
        self.inputs_crosshaul = dict()
        # Radio-related input/output ports
        self.inputs_radio_control_ul = dict()
        self.inputs_radio_transport_ul = dict()

        for ap_id, ap in aps.items():
            assert isinstance(ap, AccessPoint)
            self.add_coupling(self.input_repeat_pss, ap.input_resend_pss)
            self.add_coupling(ap.output_connected_ues, self.output_connected_ues)

            self.inputs_crosshaul[ap_id] = Port(PhysicalPacket, 'input_crosshaul_' + ap_id)
            self.inputs_radio_control_ul[ap_id] = Port(PhysicalPacket, 'input_radio_control_ul_' + ap_id)
            self.inputs_radio_transport_ul[ap_id] = Port(PhysicalPacket, 'input_radio_transport_ul_' + ap_id)

            self.add_in_port(self.inputs_crosshaul[ap_id])
            self.add_in_port(self.inputs_radio_control_ul[ap_id])
            self.add_in_port(self.inputs_radio_transport_ul[ap_id])

            self.add_coupling(self.inputs_crosshaul[ap_id], ap.input_crosshaul)
            self.add_coupling(ap.output_crosshaul, self.output_crosshaul)
            self.add_coupling(self.inputs_radio_control_ul[ap_id], ap.input_radio_control_ul)
            self.add_coupling(self.inputs_radio_transport_ul[ap_id], ap.input_radio_transport_ul)
            self.add_coupling(ap.output_radio_bc, self.output_radio_bc)
            self.add_coupling(ap.output_radio_control_dl, self.output_radio_control_dl)
            self.add_coupling(ap.output_radio_transport_dl, self.output_radio_transport_dl)
