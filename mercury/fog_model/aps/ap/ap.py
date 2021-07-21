from xdevs.models import Coupled, Port
from mercury.config.aps import AccessPointConfig
from mercury.config.radio import RadioAccessNetworkConfig
from mercury.msg.network import EnableChannels, NodeLocation, PhysicalPacket
from .signaling import SignalingBroadcast
from .access_and_control import AccessAndControl
from .transport import Transport
from .ap_antenna import AccessPointAntenna
from .crosshaul_transceiver import CrosshaulTransceiver


class AccessPoint(Coupled):
    def __init__(self, ap_config: AccessPointConfig):
        """
        Access Point DEVS module.
        :param ap_config: Access Point Configuration
        """
        ap_id = ap_config.ap_id
        self.ap_id = ap_id
        super().__init__('aps_ap_{}'.format(self.ap_id))

        # Define components and add the to coupled model
        signaling = SignalingBroadcast(ap_id)
        access_control = AccessAndControl(ap_id)
        transport = Transport(ap_id)
        crosshaul = CrosshaulTransceiver(ap_id)
        antenna = AccessPointAntenna(ap_id)
        self.add_component(signaling)
        self.add_component(access_control)
        self.add_component(transport)
        self.add_component(crosshaul)
        self.add_component(antenna)

        # Define crosshaul_config-related input/output ports
        self.input_crosshaul = Port(PhysicalPacket, 'input_crosshaul')
        self.output_crosshaul = Port(PhysicalPacket, 'output_crosshaul')
        self.add_in_port(self.input_crosshaul)
        self.add_out_port(self.output_crosshaul)

        # Define radio-related input/output ports
        self.input_radio_control_ul = Port(PhysicalPacket, 'input_radio_control_ul')
        self.input_radio_transport_ul = Port(PhysicalPacket, 'input_radio_transport_ul')
        self.output_radio_bc = Port(PhysicalPacket, 'output_radio_bc')
        self.output_radio_control_dl = Port(PhysicalPacket, 'output_radio_control_dl')
        self.output_radio_transport_dl = Port(PhysicalPacket, 'output_radio_transport_dl')
        self.add_in_port(self.input_radio_control_ul)
        self.add_in_port(self.input_radio_transport_ul)
        self.add_out_port(self.output_radio_bc)
        self.add_out_port(self.output_radio_control_dl)
        self.add_out_port(self.output_radio_transport_dl)

        # Define handy ports
        self.input_resend_pss = Port(str, 'input_resend_pss')
        self.input_new_location = Port(NodeLocation, 'input_new_location')
        self.output_connected_ues = Port(EnableChannels, 'output_connected_ues')
        self.add_in_port(self.input_resend_pss)
        self.add_in_port(self.input_new_location)
        self.add_out_port(self.output_connected_ues)

        self._external_crosshaul(crosshaul)
        self._external_radio(antenna)
        self._external_access(access_control)
        self._external_signaling(signaling)

        self._internal_signaling_antenna(signaling, antenna)
        self._internal_access_antenna(access_control, antenna)
        self._internal_access_transport(access_control, transport)
        self._internal_transport_antenna(transport, antenna)
        self._internal_access_crosshaul(access_control, crosshaul)
        self._internal_transport_crosshaul(transport, crosshaul)

    def _external_crosshaul(self, crosshaul: CrosshaulTransceiver):
        self.add_coupling(self.input_crosshaul, crosshaul.input_crosshaul)
        self.add_coupling(crosshaul.output_crosshaul, self.output_crosshaul)

    def _external_radio(self, antenna: AccessPointAntenna):
        self.add_coupling(self.input_radio_control_ul, antenna.input_radio_control_ul)
        self.add_coupling(self.input_radio_transport_ul, antenna.input_radio_transport_ul)
        self.add_coupling(antenna.output_radio_bc, self.output_radio_bc)
        self.add_coupling(antenna.output_radio_control_dl, self.output_radio_control_dl)
        self.add_coupling(antenna.output_radio_transport_dl, self.output_radio_transport_dl)

    def _external_access(self, access_control: AccessAndControl):
        self.add_coupling(access_control.output_connected_ue_list, self.output_connected_ues)

    def _external_signaling(self, signaling: SignalingBroadcast):
        self.add_coupling(self.input_resend_pss, signaling.input_repeat)
        self.add_coupling(self.input_new_location, signaling.input_new_location)

    def _internal_signaling_antenna(self, signaling: SignalingBroadcast, antenna: AccessPointAntenna):
        self.add_coupling(signaling.output_pss, antenna.input_pss)

    def _internal_access_antenna(self, access_control: AccessAndControl, antenna: AccessPointAntenna):
        self.add_coupling(access_control.output_access_response, antenna.input_access_response)
        self.add_coupling(access_control.output_disconnect_response, antenna.input_disconnect_response)
        self.add_coupling(access_control.output_ho_started, antenna.input_ho_started)
        self.add_coupling(access_control.output_ho_finished, antenna.input_ho_finished)
        self.add_coupling(access_control.output_connected_ue_list, antenna.input_connected_ue_list)
        self.add_coupling(antenna.output_rrc, access_control.input_rrc)
        self.add_coupling(antenna.output_access_request, access_control.input_access_request)
        self.add_coupling(antenna.output_disconnect_request, access_control.input_disconnect_request)
        self.add_coupling(antenna.output_ho_ready, access_control.input_ho_ready)
        self.add_coupling(antenna.output_ho_response, access_control.input_ho_response)

    def _internal_access_transport(self, access_control: AccessAndControl, transport: Transport):
        self.add_coupling(access_control.output_connected_ue_list, transport.input_connected_ue_list)

    def _internal_transport_antenna(self, transport: Transport, antenna: AccessPointAntenna):
        self.add_coupling(transport.output_radio, antenna.input_to_radio_dl)
        self.add_coupling(antenna.output_from_radio_ul, transport.input_radio)

    def _internal_access_crosshaul(self, access_control: AccessAndControl, crosshaul: CrosshaulTransceiver):
        self.add_coupling(access_control.output_start_ho_request, crosshaul.input_start_ho_request)
        self.add_coupling(access_control.output_start_ho_response, crosshaul.input_start_ho_response)
        self.add_coupling(crosshaul.output_start_ho_request, access_control.input_start_ho_request)
        self.add_coupling(crosshaul.output_start_ho_response, access_control.input_start_ho_response)
        if not RadioAccessNetworkConfig.bypass_amf:
            self.add_coupling(access_control.output_create_path_request, crosshaul.input_create_path_request)
            self.add_coupling(access_control.output_remove_path_request, crosshaul.input_remove_path_request)
            self.add_coupling(access_control.output_switch_path_request, crosshaul.input_switch_path_request)
            self.add_coupling(crosshaul.output_create_path_response, access_control.input_create_path_response)
            self.add_coupling(crosshaul.output_remove_path_response, access_control.input_remove_path_response)
            self.add_coupling(crosshaul.output_switch_path_response, access_control.input_switch_path_response)

    def _internal_transport_crosshaul(self, transport: Transport, crosshaul: CrosshaulTransceiver):
        self.add_coupling(transport.output_crosshaul, crosshaul.input_to_crosshaul)
        self.add_coupling(crosshaul.output_from_crosshaul, transport.input_crosshaul)
