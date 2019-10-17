from xdevs.models import Port
from ...common import TransmissionDelayer
from ...common.radio import RadioConfiguration, RadioAntenna, RadioAntennaConfig
from ...common.packet.physical import PhysicalPacket
from ...common.packet.network import NetworkPacketConfiguration, NetworkPacket
from .internal_interfaces import ConnectedAccessPoint, ExtendedPSS, AntennaPowered
from ...common.packet.application.ran.ran_access import AccessRequest, AccessResponse, RadioResourceControl, \
    DisconnectRequest, DisconnectResponse, NewDownLinkMCS, NewUpLinkMCS
from ...common.packet.application.ran.ran_handover import HandOverStarted, HandOverReady, HandOverFinished, \
    HandOverResponse

UL_MCS = 'ul_mcs_list'
DL_MCS = 'dl_mcs_list'
BANDWIDTH = 'bandwidth'


class UserEquipmentAntenna(TransmissionDelayer):
    """
    xDEVS module that models the behavior of a User Equipment antenna.

    :param str name: Name of the antenna DEVS module
    :param str ue_id: ID of the UE with the antenna
    :param NetworkPacketConfiguration network_config: network packets configuration
    :param RadioConfiguration radio_config: Radio configuration
    :param RadioAntennaConfig antenna_config: float
    """
    def __init__(self, name, ue_id, network_config, radio_config, antenna_config):

        super().__init__(name)
        self.ue_id = ue_id
        self.network_config = network_config
        self.radio_config = radio_config
        self.antenna = RadioAntenna(antenna_config)

        self.potential_ul_mcs = radio_config.dl_mcs_list[0]
        self.potential_bandwidth = radio_config.bandwidth
        self.min_dl_mcs = radio_config.dl_mcs_list[0]
        self.min_ul_mcs = radio_config.ul_mcs_list[0]

        self.connected_ap = None
        self.powered = False
        self.connection_parameters = dict()

        # Radio-antenna ports
        self.input_radio_bc = Port(PhysicalPacket, name + '_input_radio_bc')
        self.input_radio_control_dl = Port(PhysicalPacket, name + '_input_radio_control_dl')
        self.input_radio_transport_dl = Port(PhysicalPacket, name + '_input_radio_transport_dl')
        self.output_radio_control_ul = Port(PhysicalPacket, name + '_output_radio_control_ul')
        self.output_radio_transport_ul = Port(PhysicalPacket, name + '_output_radio_transport_ul')
        self.add_in_port(self.input_radio_bc)
        self.add_in_port(self.input_radio_control_dl)
        self.add_in_port(self.input_radio_transport_dl)
        self.add_out_port(self.output_radio_control_ul)
        self.add_out_port(self.output_radio_transport_ul)

        # Ambassador-antenna ports
        self.input_service = Port(NetworkPacket, name + '_input_ambassador')
        self.output_service = Port(NetworkPacket, name + '_output_ambassador')
        self.add_in_port(self.input_service)
        self.add_out_port(self.output_service)

        # Access manager-antenna ports
        self.input_access_request = Port(AccessRequest, name + '_input_access_request')
        self.input_disconnect_request = Port(DisconnectRequest, name + '_input_disconnect_request')
        self.input_rrc = Port(RadioResourceControl, name + '_input_rrc')
        self.input_ho_ready = Port(HandOverReady, name + '_input_ho_ready')
        self.input_ho_response = Port(HandOverResponse, name + '_input_ho_response')
        self.input_connected_ap = Port(ConnectedAccessPoint, name + '_input_connected_ap')
        self.input_antenna_powered = Port(AntennaPowered, name + '_input_antenna_powered')
        self.output_pss = Port(ExtendedPSS, name + '_output_pss')
        self.output_access_response = Port(AccessResponse, name + '_output_access_response')
        self.output_disconnect_response = Port(DisconnectResponse, name + '_output_disconnect_response')
        self.output_ho_started = Port(HandOverStarted, name + '_output_ho_started')
        self.output_ho_finished = Port(HandOverFinished, name + '_output_ho_finished')
        self.add_in_port(self.input_access_request)
        self.add_in_port(self.input_disconnect_request)
        self.add_in_port(self.input_rrc)
        self.add_in_port(self.input_ho_ready)
        self.add_in_port(self.input_ho_response)
        self.add_in_port(self.input_connected_ap)
        self.add_out_port(self.output_pss)
        self.add_out_port(self.output_access_response)
        self.add_out_port(self.output_disconnect_response)
        self.add_out_port(self.output_ho_started)
        self.add_out_port(self.output_ho_finished)

        # Auxiliary ports
        self.output_dl_mcs = Port(NewDownLinkMCS, name + '_output_new_dl_mcs')
        self.add_out_port(self.output_dl_mcs)

    def check_in_ports(self):
        self._check_antenna_powered()
        res = self._check_connected_ap()
        if self.connected_ap is not None:
            assert self.powered
        if self.powered:
            res |= self._check_radio_control_dl()
            res |= self._check_radio_transport_dl()
        if res:
            self._send_new_dl_mcs()
        if self.powered:
            self._check_radio_broadcast()
            self._check_access_manager()
            self._check_service_ambassador()

    def _check_antenna_powered(self):
        if self.input_antenna_powered:
            self.powered = self.input_antenna_powered.get().powered

    def _check_connected_ap(self):
        res = False
        if self.input_connected_ap:
            res = True
            self.connected_ap = self.input_connected_ap.get().ap_id
            self.connection_parameters = {UL_MCS: self.potential_ul_mcs,
                                          DL_MCS: self.min_dl_mcs,
                                          BANDWIDTH: self.potential_bandwidth}
        return res

    def _check_radio_control_dl(self):
        prop_mcs = False
        for job in self.input_radio_control_dl.values:
            ap_id, network_msg = self.__expand_physical_message(job)
            ap_id, app_msg = self.__expand_network_message(network_msg)
            if ap_id == self.connected_ap:
                if isinstance(app_msg, NewUpLinkMCS):
                    prop_mcs = True
                    self.__process_new_ul_mcs(app_msg)
                elif isinstance(app_msg, HandOverStarted):
                    self.add_msg_to_queue(self.output_ho_started, app_msg)
                else:
                    raise Exception("Unable to determine message type")
                best_dl_mcs = self.antenna.select_best_rx_mcs(self.antenna.compute_snr(job))
                if best_dl_mcs != self.connection_parameters[DL_MCS]:
                    prop_mcs = True
                    self.connection_parameters[DL_MCS] = best_dl_mcs
            else:
                if isinstance(app_msg, HandOverFinished):
                    self.add_msg_to_queue(self.output_ho_finished, app_msg)
                elif isinstance(app_msg, DisconnectResponse):
                    self.add_msg_to_queue(self.output_disconnect_response, app_msg)
                elif isinstance(app_msg, AccessResponse):
                    self.add_msg_to_queue(self.output_access_response, app_msg)
                elif isinstance(app_msg, NewUpLinkMCS):
                    self.potential_ul_mcs = self.antenna.get_tx_mcs(app_msg.mcs_index)
                    self.potential_bandwidth = app_msg.bandwidth
                else:
                    raise Exception("Unable to determine message type")
        return prop_mcs

    def _check_radio_transport_dl(self):
        prop_mcs = False
        for job in self.input_radio_transport_dl.values:
            ap_id, network_msg = self.__expand_physical_message(job)
            if ap_id == self.connected_ap:
                self.add_msg_to_queue(self.output_service, network_msg)
                best_dl_mcs = self.antenna.select_best_rx_mcs(self.antenna.compute_snr(job))
                if best_dl_mcs != self.connection_parameters[DL_MCS]:
                    prop_mcs = True
                    self.connection_parameters[DL_MCS] = best_dl_mcs
        return prop_mcs

    def _send_new_dl_mcs(self):
        if self.connected_ap is None:
            msg = NewDownLinkMCS(self.ue_id, None, 0, 0, 0)
        else:
            mcs_index = self.connection_parameters[DL_MCS][0]
            mcs_eff = self.connection_parameters[DL_MCS][1]
            bw = self.connection_parameters[BANDWIDTH]
            msg = NewDownLinkMCS(self.ue_id, self.connected_ap, mcs_index, mcs_eff, bw)
            self.__add_app_msg_to_radio_control_ul(msg, self.connected_ap)
        self.add_msg_to_queue(self.output_dl_mcs, msg)

    def _check_radio_broadcast(self):
        for job in self.input_radio_bc.values:
            snr = self.antenna.compute_snr(job)
            ap_id, network_msg = self.__expand_physical_message(job)
            ap_id, app_msg = self.__expand_network_message(network_msg)
            self.add_msg_to_queue(self.output_pss, ExtendedPSS(ap_id, snr))

    def _check_access_manager(self):
        for msg in self.input_access_request.values:
            self.__add_app_msg_to_radio_control_ul(msg, msg.ap_id)
        for msg in self.input_disconnect_request.values:
            self.__add_app_msg_to_radio_control_ul(msg, msg.ap_id)
        for msg in self.input_rrc.values:
            self.__add_app_msg_to_radio_control_ul(msg, msg.ap_id)
        for msg in self.input_ho_ready.values:
            self.__add_app_msg_to_radio_control_ul(msg, msg.ap_to)
        for msg in self.input_ho_response.values:
            self.__add_app_msg_to_radio_control_ul(msg, msg.ap_from)

    def _check_service_ambassador(self):
        for msg in self.input_service.values:
            self.__add_network_msg_to_radio_transport_ul(msg)

    def __process_new_ul_mcs(self, app_msg):
        """
        :param NewUpLinkMCS app_msg:
        """
        bandwidth = app_msg.bandwidth
        mcs_tuple = self.antenna.get_tx_mcs(app_msg.mcs_index)
        self.connection_parameters[BANDWIDTH] = bandwidth
        self.connection_parameters[UL_MCS] = mcs_tuple

    def __add_app_msg_to_radio_control_ul(self, msg, node_to):
        network = self.__encapsulate_network_packet(self.ue_id, node_to, msg)
        bandwidth = self.radio_config.bandwidth
        spectral_efficiency = self.min_ul_mcs[1]
        msg = self.__encapsulate_physical_packet(node_to, network, bandwidth, spectral_efficiency)
        size = msg.compute_size()
        channel = "pucch_" + node_to
        self.add_msg_to_buffer(self.output_radio_control_ul, msg, channel, size, bandwidth, spectral_efficiency)

    def __add_network_msg_to_radio_transport_ul(self, msg):
        physical_to = self.connected_ap
        bandwidth = self.connection_parameters[BANDWIDTH]
        spectral_efficiency = self.connection_parameters[UL_MCS][1]
        msg = self.__encapsulate_physical_packet(physical_to, msg, bandwidth, spectral_efficiency)
        size = msg.compute_size()
        channel = "pusch_" + self.connected_ap
        self.add_msg_to_buffer(self.output_radio_transport_ul, msg, channel, size, bandwidth, spectral_efficiency)

    def __expand_physical_message(self, physical_message):
        assert self.ue_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def __expand_network_message(self, network_message):
        assert self.ue_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __encapsulate_network_packet(self, node_from, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(node_from, node_to, header, application_message)

    def __encapsulate_physical_packet(self, node_to, network_message, bandwidth, spectral_efficiency):
        header = self.radio_config.header
        power = self.antenna.inject_power()
        return PhysicalPacket(self.ue_id, node_to, power, bandwidth, spectral_efficiency, header, network_message)
