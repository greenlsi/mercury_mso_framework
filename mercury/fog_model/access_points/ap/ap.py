from xdevs.models import Coupled, Port
from ...common.packet.physical import PhysicalPacket
from ...common.packet.network import NetworkPacketConfiguration
from ...common.packet.application.ran import RadioAccessNetworkConfiguration
from ...common.packet.application.ran.ran_access import NewUpLinkMCS
from ...common.mobility import NewLocation
from ...common.crosshaul import CrosshaulConfiguration
from ...common.radio import RadioConfiguration
from ...common.access_points import AccessPointConfiguration
from .signaling import SignalingBroadcast
from .access_and_control import AccessAndControl
from .transport import Transport
from .ap_antenna import AccessPointAntenna
from .crosshaul_transceiver import CrosshaulTransceiver


class AccessPoint(Coupled):
    """
    Access Point DEVS module.
    :param str name: name of the DEVS module
    :param AccessPointConfiguration ap_config: Access Point Configuration
    :param str amf_id: ID of the AMF core function
    :param RadioAccessNetworkConfiguration rac_config: radio pxcch network configuration
    :param NetworkPacketConfiguration network_config: network packet configuration
    :param CrosshaulConfiguration crosshaul_config: crosshaul_config configuration
    :param RadioConfiguration radio_config: radio interface configuration
    """
    def __init__(self, name, ap_config, amf_id, rac_config, network_config, crosshaul_config, radio_config):

        super().__init__(name)

        # Unwrap configuration parameters
        ap_id = ap_config.ap_id
        crosshaul_transceiver = ap_config.crosshaul_transceiver_config
        radio_antenna_config = ap_config.radio_antenna_config
        self.ap_id = ap_id

        # Define components and add the to coupled model
        signaling = SignalingBroadcast(name + '_signaling', ap_id, rac_config)
        access_control = AccessAndControl(name + '_access_control', ap_id, rac_config)
        transport = Transport(name + '_transport', ap_id)
        crosshaul = CrosshaulTransceiver(name + '_crosshaul_transceiver', ap_id, crosshaul_transceiver, network_config,
                                         crosshaul_config, amf_id)
        antenna = AccessPointAntenna(name + '_antenna', ap_id, network_config, radio_config, radio_antenna_config)
        self.add_component(signaling)
        self.add_component(access_control)
        self.add_component(transport)
        self.add_component(crosshaul)
        self.add_component(antenna)

        # Define crosshaul_config-related input/output ports
        self.input_crosshaul_dl = Port(PhysicalPacket, name + '_input_crosshaul_dl')
        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.output_crosshaul_dl = Port(PhysicalPacket, name + '_output_crosshaul_dl')
        self.output_crosshaul_ul = Port(PhysicalPacket, name + '_output_crosshaul_ul')
        self.add_in_port(self.input_crosshaul_dl)
        self.add_in_port(self.input_crosshaul_ul)
        self.add_out_port(self.output_crosshaul_dl)
        self.add_out_port(self.output_crosshaul_ul)

        # Define radio-related input/output ports
        self.input_radio_control_ul = Port(PhysicalPacket, name + '_input_radio_control_ul')
        self.input_radio_transport_ul = Port(PhysicalPacket, name + '_input_radio_transport_ul')
        self.output_radio_bc = Port(PhysicalPacket, name + '_output_radio_bc')
        self.output_radio_control_dl = Port(PhysicalPacket, name + '_output_radio_control_dl')
        self.output_radio_transport_dl = Port(PhysicalPacket, name + '_output_radio_transport_dl')
        self.add_in_port(self.input_radio_control_ul)
        self.add_in_port(self.input_radio_transport_ul)
        self.add_out_port(self.output_radio_bc)
        self.add_out_port(self.output_radio_control_dl)
        self.add_out_port(self.output_radio_transport_dl)

        # Define handy ports
        self.input_new_ue_location = Port(NewLocation, name + '_input_new_ue_location')
        self.output_ul_mcs = Port(NewUpLinkMCS, name + '_output_new_ul_mcs')
        self.add_in_port(self.input_new_ue_location)
        self.add_out_port(self.output_ul_mcs)

        self._external_crosshaul(crosshaul)
        self._external_radio(antenna)
        self._external_signaling(signaling)

        self._internal_signaling_antenna(signaling, antenna)
        self._internal_access_antenna(access_control, antenna)
        self._internal_access_transport(access_control, transport)
        self._internal_transport_antenna(transport, antenna)
        self._internal_access_crosshaul(access_control, crosshaul)
        self._internal_transport_crosshaul(transport, crosshaul)

    def _external_crosshaul(self, crosshaul):
        """:param CrosshaulTransceiver crosshaul: crosshaul_config transceiver"""
        self.add_coupling(self.input_crosshaul_dl, crosshaul.input_crosshaul_dl)
        self.add_coupling(self.input_crosshaul_ul, crosshaul.input_crosshaul_ul)
        self.add_coupling(crosshaul.output_crosshaul_dl, self.output_crosshaul_dl)
        self.add_coupling(crosshaul.output_crosshaul_ul, self.output_crosshaul_ul)

    def _external_radio(self, antenna):
        """:param AccessPointAntenna antenna: AP antenna"""
        self.add_coupling(self.input_radio_control_ul, antenna.input_radio_control_ul)
        self.add_coupling(self.input_radio_transport_ul, antenna.input_radio_transport_ul)
        self.add_coupling(antenna.output_radio_bc, self.output_radio_bc)
        self.add_coupling(antenna.output_radio_control_dl, self.output_radio_control_dl)
        self.add_coupling(antenna.output_radio_transport_dl, self.output_radio_transport_dl)
        self.add_coupling(antenna.output_ul_mcs, self.output_ul_mcs)

    def _external_signaling(self, signaling):
        """:param SignalingBroadcast signaling: pbch module"""
        self.add_coupling(self.input_new_ue_location, signaling.input_new_ue_location)

    def _internal_signaling_antenna(self, signaling, antenna):
        """
        :param SignalingBroadcast signaling:
        :param AccessPointAntenna antenna:
        """
        self.add_coupling(signaling.output_pss, antenna.input_pss)

    def _internal_access_antenna(self, access_control, antenna):
        """
        :param AccessAndControl access_control:
        :param AccessPointAntenna antenna:
        """
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

    def _internal_access_transport(self, access_control, transport):
        """
        :param AccessAndControl access_control:
        :param Transport transport:
        """
        self.add_coupling(access_control.output_connected_ue_list, transport.input_connected_ue_list)

    def _internal_transport_antenna(self, transport, antenna):
        """
        :param Transport transport:
        :param AccessPointAntenna antenna:
        """
        self.add_coupling(transport.output_service_routing_response, antenna.input_service_routing_response)
        self.add_coupling(transport.output_radio, antenna.input_to_radio_dl)
        self.add_coupling(antenna.output_service_routing_request, transport.input_service_routing_request)
        self.add_coupling(antenna.output_from_radio_ul, transport.input_radio)

    def _internal_access_crosshaul(self, access_control, crosshaul):
        """
        :param AccessAndControl access_control:
        :param CrosshaulTransceiver crosshaul:
        """
        self.add_coupling(access_control.output_start_ho_request, crosshaul.input_start_ho_request)
        self.add_coupling(access_control.output_start_ho_response, crosshaul.input_start_ho_response)
        self.add_coupling(access_control.output_create_path_request, crosshaul.input_create_path_request)
        self.add_coupling(access_control.output_remove_path_request, crosshaul.input_remove_path_request)
        self.add_coupling(access_control.output_switch_path_request, crosshaul.input_switch_path_request)
        self.add_coupling(crosshaul.output_start_ho_request, access_control.input_start_ho_request)
        self.add_coupling(crosshaul.output_start_ho_response, access_control.input_start_ho_response)
        self.add_coupling(crosshaul.output_create_path_response, access_control.input_create_path_response)
        self.add_coupling(crosshaul.output_remove_path_response, access_control.input_remove_path_response)
        self.add_coupling(crosshaul.output_switch_path_response, access_control.input_switch_path_response)

    def _internal_transport_crosshaul(self, transport, crosshaul):
        """
        :param Transport transport:
        :param CrosshaulTransceiver crosshaul:
        """
        self.add_coupling(transport.output_crosshaul, crosshaul.input_to_crosshaul)
        self.add_coupling(crosshaul.output_from_crosshaul, transport.input_crosshaul)
        self.add_coupling(crosshaul.output_new_sdn_path, transport.input_new_sdn_path)
