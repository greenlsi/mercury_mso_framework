import logging
from xdevs.models import Port
from ..common import TransmissionDelayer, logging_overhead
from ..common.packet.network import NetworkPacket, NetworkPacketConfiguration
from ..common.packet.physical import PhysicalPacket
from ..common.packet.application.ran import RadioAccessNetworkConfiguration
from ..common.packet.application.ran.ran_access_control import RANAccessControlRequest
from ..common.packet.application.ran.ran_access_control import CreatePathRequest, RemovePathRequest, SwitchPathRequest
from ..common.packet.application.ran.ran_access_control import CreatePathResponse, RemovePathResponse, SwitchPathResponse
from ..common.crosshaul import CrosshaulConfiguration, CrosshaulTransceiverConfiguration


LOGGING_OVERHEAD = "    "


class AccessAndMobilityManagementFunction(TransmissionDelayer):
    def __init__(self, name, amf_id, ran_config, network_config, crosshaul_config, crosshaul_transceiver):
        """
        Access and Mobility Management Function xDEVS model
        :param str name: name of the xDEVS module
        :param str amf_id: ID of the Access and Mobility Management Function
        :param RadioAccessNetworkConfiguration ran_config: RAN application Configuration
        :param NetworkPacketConfiguration network_config: network packets configuration
        :param CrosshaulConfiguration crosshaul_config: Crosshaul configuration
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver: CrosshaulTransceiverConfiguration
        """
        super().__init__(name=name)

        self.amf_id = amf_id
        self.ran_ac_config = ran_config
        self.network_config = network_config
        self.crosshaul_config = crosshaul_config
        self.crosshaul_transceiver = crosshaul_transceiver

        self.path_table = dict()  # {node_id: connected_ap}

        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.output_crosshaul_dl = Port(PhysicalPacket, name + '_output_crosshaul_dl')
        self.add_in_port(self.input_crosshaul_ul)
        self.add_out_port(self.output_crosshaul_dl)

    def check_in_ports(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        for job in self.input_crosshaul_ul.values:
            phys_node_from, network_msg = self.__expand_physical_message(job)
            net_node_from, app_msg = self.__expand_network_message(network_msg)
            if isinstance(app_msg, RANAccessControlRequest):
                ap_id = app_msg.ap_id
                ue_id = app_msg.ue_id
                if isinstance(app_msg, SwitchPathRequest):
                    prev_ap_id = app_msg.prev_ap_id
                    self._switch_path(ue_id, ap_id, prev_ap_id, overhead)
                elif isinstance(app_msg, CreatePathRequest):
                    self._create_path(ue_id, ap_id, overhead)
                elif isinstance(app_msg, RemovePathRequest):
                    self._remove_path(ue_id, ap_id, overhead)
                else:
                    raise Exception("RAN access_points_config control message type could nob be identified by AMF")
            else:
                raise Exception("Application message could nob be identified by AMF")

    def _create_path(self, ue_id, ap_id, overhead):
        """
        If UE has not yet an assigned path, the AMF module generates new path.
        :param str ue_id: ID of the UE to be routed
        :param str ap_id: ID of the AP on which the UE is connected_ap
        :param str overhead: logging overhead
        """
        res = ue_id not in self.path_table
        logging.info(overhead + '%s--->AMF create path %s request' % (ap_id, ue_id))
        if res:
            self.path_table[ue_id] = ap_id
        msg = CreatePathResponse(ap_id, ue_id, res, self.ran_ac_config.header)
        self.__add_msg_to_crosshaul_dl(msg, ap_id, ap_id)

    def _remove_path(self, ue_id, ap_id, overhead):
        """
        If UE has an assigned path, the AMF removes it
        :param str, ue_id: ID of the UE to be routed
        :param str, ap_id: ID of the AP on which the UE is connected_ap
        :param str overhead: logging overhead
        """
        res = ue_id in self.path_table and ap_id == self.path_table[ue_id]
        logging.info(overhead + '%s--->AMF remove path %s request' % (ap_id, ue_id))
        if res:
            self.path_table.pop(ue_id)
        msg = RemovePathResponse(ap_id, ue_id, res, self.ran_ac_config.header)
        self.__add_msg_to_crosshaul_dl(msg, ap_id, ap_id)

    def _switch_path(self, ue_id, new_ap_id, prev_ap_id, overhead):
        """
        If UE has already an assigned path, the path can be changed by the AMF when requested
        :param str ue_id: ID of the UE to be re-routed
        :param str new_ap_id: ID of the AP on which the UE is re-connected_ap
        :param str prev_ap_id: ID of the AP on which the UE was previously connected_ap
        :param str overhead: logging overhead
        """
        res = ue_id in self.path_table and prev_ap_id == self.path_table[ue_id]
        logging.info(overhead + '%s--->AMF switch path %s request' % (new_ap_id, ue_id))
        if res:
            self.path_table[ue_id] = new_ap_id
        msg = SwitchPathResponse(new_ap_id, ue_id, prev_ap_id, res, self.ran_ac_config.header)
        self.__add_msg_to_crosshaul_dl(msg, new_ap_id, new_ap_id)

    def __encapsulate_network_packet(self, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(self.amf_id, node_to, header, application_message)

    def __encapsulate_physical_packet(self, node_to, network_message):
        header = self.crosshaul_config.header
        power, bandwidth, spectral_eff = self.crosshaul_transceiver.get()
        return PhysicalPacket(self.amf_id, node_to, power, bandwidth, spectral_eff, header, network_message)

    def __expand_physical_message(self, physical_message):
        assert self.amf_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def __expand_network_message(self, network_message):
        assert self.amf_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __add_msg_to_crosshaul_dl(self, msg, network_to, physical_to):
        network = self.__encapsulate_network_packet(network_to, msg)
        msg = self.__encapsulate_physical_packet(physical_to, network)
        size = msg.compute_size()
        channel = "crosshaul_dl"
        self.add_msg_to_buffer(self.output_crosshaul_dl, msg, channel, size, msg.bandwidth, msg.spectral_efficiency)
        # self.add_msg_to_queue(self.output_crosshaul_dl, msg)
