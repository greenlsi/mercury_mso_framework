from typing import Dict
from xdevs.models import Coupled, Port
from mercury.config.aps import AccessPointConfig
from mercury.msg.network import EnableChannels, NodeLocation, PhysicalPacket
from .ap import AccessPoint


class AccessPoints(Coupled):
    def __init__(self, aps_config: Dict[str, AccessPointConfig]):
        """
        Access Points layer xDEVS module.
        :param aps_config: Access Points configuration list {AP ID: AP configuration}
        """
        super().__init__('aps')
        # Unwrap configuration parameters
        self.ap_ids = [a for a in aps_config]
        if len(self.ap_ids) != len(set(self.ap_ids)):
            raise ValueError('AP IDs must be unique')

        # Create submodules and add them to the coupled model
        aps = {ap_id: AccessPoint(ap_config) for ap_id, ap_config in aps_config.items()}

        [self.add_component(ap) for ap in aps.values()]

        # Handy ports
        self.input_repeat_pss = Port(str, 'input_repeat_pss')
        self.input_new_location = Port(NodeLocation, 'input_new_location')
        self.output_connected_ues = Port(EnableChannels, 'output_connected_ues')
        self.output_crosshaul = Port(PhysicalPacket, 'output_crosshaul')
        self.output_radio_bc = Port(PhysicalPacket, 'output_radio_bc')
        self.output_radio_control_dl = Port(PhysicalPacket, 'output_radio_control')
        self.output_radio_transport_dl = Port(PhysicalPacket, 'output_radio_transport')

        self.add_in_port(self.input_repeat_pss)
        self.add_in_port(self.input_new_location)
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
            self.add_coupling(self.input_new_location, ap.input_new_location)
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
