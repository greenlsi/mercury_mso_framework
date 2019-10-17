from xdevs.models import Port
from ...common import TransmissionDelayer
from ...common.radio import RadioConfiguration, RadioAntenna, RadioAntennaConfig
from ...common.packet.physical import PhysicalPacket
from ...common.packet.network import NetworkPacketConfiguration, NetworkPacket
from .internal_interfaces import ConnectedUEList
from ...common.packet.application.ran.ran_access import PrimarySynchronizationSignal, AccessRequest, AccessResponse, \
    RadioResourceControl, DisconnectRequest, DisconnectResponse, NewDownLinkMCS, NewUpLinkMCS
from ...common.packet.application.ran.ran_handover import HandOverStarted, HandOverReady, HandOverFinished, \
    HandOverResponse
from ...common.packet.application.service import GetDataCenterRequest, GetDataCenterResponse

UL_MCS = 'ul_mcs_list'
DL_MCS = 'dl_mcs_list'
BW_SHARE = 'bandwidth_share'


class AccessPointAntenna(TransmissionDelayer):
    """
    Access Point Antenna xDEVS implementation
    :param str name: name of the xDEVS module
    :param str ap_id: AP ID
    :param NetworkPacketConfiguration network_config: Network packets configuration
    :param RadioConfiguration radio_config: Radio network configuration
    :param RadioAntennaConfig antenna_config: radio antenna configuration
    """
    def __init__(self, name, ap_id, network_config, radio_config, antenna_config):
        super().__init__(name=name)

        self.ap_id = ap_id
        self.network_config = network_config
        self.radio_config = radio_config
        self.antenna = RadioAntenna(antenna_config)

        self.min_dl_mcs = radio_config.dl_mcs_list[0]
        self.min_ul_mcs = radio_config.ul_mcs_list[0]

        self.ue_connected = dict()

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

        self.input_connected_ue_list = Port(ConnectedUEList, name + '_input_connected_ue_list')
        self.add_in_port(self.input_connected_ue_list)

        self.input_pss = Port(PrimarySynchronizationSignal, name + '_input_pss')
        self.add_in_port(self.input_pss)

        self.input_access_response = Port(AccessResponse, name + '_input_access_response')
        self.input_disconnect_response = Port(DisconnectResponse, name + '_input_disconnect_response')
        self.input_ho_started = Port(HandOverStarted, name + '_input_ho_started')
        self.input_ho_finished = Port(HandOverFinished, name + '_input_ho_finished')
        self.output_rrc = Port(RadioResourceControl, name + '_output_rrc')
        self.output_access_request = Port(AccessRequest, name + '_output_access_request')
        self.output_disconnect_request = Port(DisconnectRequest, name + '_output_disconnect_request')
        self.output_ho_ready = Port(HandOverReady, name + '_output_ho_ready')
        self.output_ho_response = Port(HandOverResponse, name + '_output_ho_response')
        self.add_in_port(self.input_access_response)
        self.add_in_port(self.input_disconnect_response)
        self.add_in_port(self.input_ho_started)
        self.add_in_port(self.input_ho_finished)
        self.add_out_port(self.output_rrc)
        self.add_out_port(self.output_access_request)
        self.add_out_port(self.output_disconnect_request)
        self.add_out_port(self.output_ho_ready)
        self.add_out_port(self.output_ho_response)

        self.input_service_routing_response = Port(GetDataCenterResponse, name + '_input_service_routing_response')
        self.input_to_radio_dl = Port(NetworkPacket, name + '_input_to_radio_dl')
        self.output_service_routing_request = Port(GetDataCenterRequest, name + '_output_service_routing_response')
        self.output_from_radio_ul = Port(NetworkPacket, name + '_output_from_radio_ul')
        self.add_in_port(self.input_service_routing_response)
        self.add_in_port(self.input_to_radio_dl)
        self.add_out_port(self.output_service_routing_request)
        self.add_out_port(self.output_from_radio_ul)

        self.output_ul_mcs = Port(NewUpLinkMCS, name + '_output_new_ul_mcs')
        self.add_out_port(self.output_ul_mcs)

    def check_in_ports(self):
        res = self._check_new_ue_list()
        res |= self._check_radio_control_ul()
        res |= self._check_radio_transport_ul()
        if res:
            self._process_ul_mcs()
        self._check_signaling()
        self._check_access_control()
        self._check_transport()

    def _check_new_ue_list(self):
        res = False
        if self.input_connected_ue_list:
            res = True
            ue_list = self.input_connected_ue_list.values[-1].ues_list
            prov_list = {ue_id: {UL_MCS: self.min_ul_mcs, DL_MCS: self.min_dl_mcs, BW_SHARE: 0} for ue_id in ue_list}
            for ue_id in prov_list:
                if ue_id in self.ue_connected:
                    prov_list[ue_id] = self.ue_connected[ue_id]
            self.ue_connected = prov_list
        return res

    def _check_radio_control_ul(self):
        prop_mcs = False
        for job in self.input_radio_control_ul.values:
            ue_id, network_msg = self.__expand_physical_message(job)
            ue_id, app_msg = self.__expand_network_message(network_msg)
            if ue_id in self.ue_connected:
                if isinstance(app_msg, NewDownLinkMCS):
                    self.__process_new_dl_mcs(app_msg)
                elif isinstance(app_msg, RadioResourceControl):
                    self.add_msg_to_queue(self.output_rrc, app_msg)
                elif isinstance(app_msg, HandOverResponse):
                    self.add_msg_to_queue(self.output_ho_response, app_msg)
                elif isinstance(app_msg, DisconnectRequest):
                    self.add_msg_to_queue(self.output_disconnect_request, app_msg)
                else:
                    raise Exception("Unable to determine message type")
                best_ul_mcs = self.antenna.select_best_rx_mcs(self.antenna.compute_snr(job))
                if best_ul_mcs != self.ue_connected[ue_id][UL_MCS]:
                    prop_mcs = True
                    self.ue_connected[ue_id][UL_MCS] = best_ul_mcs
            else:
                if isinstance(app_msg, HandOverReady):
                    self.add_msg_to_queue(self.output_ho_ready, app_msg)
                elif isinstance(app_msg, AccessRequest):
                    self.add_msg_to_queue(self.output_access_request, app_msg)
                else:
                    raise Exception("Unable to determine message type")
        return prop_mcs

    def _check_radio_transport_ul(self):
        prop_mcs = False
        for job in self.input_radio_transport_ul.values:
            ue_id, network_msg = self.__expand_physical_message(job)
            if ue_id in self.ue_connected:
                if network_msg.node_to != self.ap_id:
                    self.add_msg_to_queue(self.output_from_radio_ul, network_msg)
                else:
                    ap_id, app_msg = self.__expand_network_message(network_msg)
                    if isinstance(app_msg, GetDataCenterRequest):
                        self.add_msg_to_queue(self.output_service_routing_request, app_msg)
                    else:
                        raise Exception("Unable to determine message type")
                best_ul_mcs = self.antenna.select_best_rx_mcs(self.antenna.compute_snr(job))
                if best_ul_mcs != self.ue_connected[ue_id][UL_MCS]:
                    prop_mcs = True
                    self.ue_connected[ue_id][UL_MCS] = best_ul_mcs
        return prop_mcs

    def _process_ul_mcs(self):
        eff = {ue_id: params[UL_MCS][1] for ue_id, params in self.ue_connected.items()}
        bw_share = self.radio_config.division_strategy.bandwidth_share(eff)
        for ue_id, bw in bw_share.items():
            self.ue_connected[ue_id][BW_SHARE] = bw
        if not self.ue_connected:
            msg = NewUpLinkMCS(self.ap_id, None, 0, 0, 0)
            self.add_msg_to_queue(self.output_ul_mcs, msg)
        else:
            for ue_id, params in self.ue_connected.items():
                mcs_index = params[UL_MCS][0]
                mcs_eff = params[UL_MCS][1]
                bw = self.radio_config.bandwidth * params[BW_SHARE]
                msg = NewUpLinkMCS(self.ap_id, ue_id, mcs_index, mcs_eff, bw)
                self.add_msg_to_queue(self.output_ul_mcs, msg)
                self.__add_app_msg_to_radio_control_dl(msg)

    def _check_signaling(self):
        for msg in self.input_pss.values:
            self.__add_app_msg_to_radio_bc(msg)

    def _check_access_control(self):
        for msg in self.input_access_response.values:
            self.__add_app_msg_to_radio_control_dl(msg)
        for msg in self.input_disconnect_response.values:
            self.__add_app_msg_to_radio_control_dl(msg)
        for msg in self.input_ho_started.values:
            self.__add_app_msg_to_radio_control_dl(msg)
        for msg in self.input_ho_finished.values:
            self.__add_app_msg_to_radio_control_dl(msg)

    def _check_transport(self):
        for msg in self.input_service_routing_response.values:
            self.__add_app_msg_to_radio_transport_dl(msg)
        for msg in self.input_to_radio_dl.values:
            self.__add_network_msg_to_radio_transport_dl(msg)

    def __encapsulate_network_packet(self, node_from, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(node_from, node_to, header, application_message)

    def __encapsulate_physical_packet(self, node_to, network_message, bandwidth, spectral_efficiency):
        header = self.radio_config.header
        power = self.antenna.inject_power()
        return PhysicalPacket(self.ap_id, node_to, power, bandwidth, spectral_efficiency, header, network_message)

    def __expand_physical_message(self, physical_message):
        assert self.ap_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def __expand_network_message(self, network_message):
        assert self.ap_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __add_app_msg_to_radio_bc(self, msg):
        network = self.__encapsulate_network_packet(self.ap_id, None, msg)
        bandwidth = self.radio_config.bandwidth
        spectral_efficiency = self.min_dl_mcs[1]
        msg = self.__encapsulate_physical_packet(None, network, bandwidth, spectral_efficiency)
        size = msg.compute_size()
        channel = "pbch"
        self.add_msg_to_buffer(self.output_radio_bc, msg, channel, size, bandwidth, spectral_efficiency)

    def __add_app_msg_to_radio_control_dl(self, msg):
        network_to = msg.ue_id
        physical_to = msg.ue_id
        network = self.__encapsulate_network_packet(self.ap_id, network_to, msg)
        bandwidth = self.radio_config.bandwidth
        spectral_efficiency = self.min_dl_mcs[1]
        msg = self.__encapsulate_physical_packet(physical_to, network, bandwidth, spectral_efficiency)
        size = msg.compute_size()
        channel = "pdcch_" + physical_to
        self.add_msg_to_buffer(self.output_radio_control_dl, msg, channel, size, bandwidth, spectral_efficiency)

    def __add_app_msg_to_radio_transport_dl(self, msg):
        network_to = msg.ue_id
        network = self.__encapsulate_network_packet(self.ap_id, network_to, msg)
        self.__add_network_msg_to_radio_transport_dl(network)

    def __add_network_msg_to_radio_transport_dl(self, msg):
        physical_to = msg.node_to
        bandwidth = self.radio_config.bandwidth * self.ue_connected[physical_to][BW_SHARE]
        spectral_efficiency = self.ue_connected[physical_to][DL_MCS][1]
        msg = self.__encapsulate_physical_packet(physical_to, msg, bandwidth, spectral_efficiency)
        size = msg.compute_size()
        channel = "pdsch_" + physical_to
        self.add_msg_to_buffer(self.output_radio_transport_dl, msg, channel, size, bandwidth, spectral_efficiency)

    def __process_new_dl_mcs(self, app_msg):
        """
        :param NewDownLinkMCS app_msg:
        """
        ue_id = app_msg.ue_id
        mcs_tuple = self.antenna.get_tx_mcs(app_msg.mcs_index)
        self.ue_connected[ue_id][DL_MCS] = mcs_tuple
