import logging
from xdevs.models import Port
from ..common import Stateless, logging_overhead
from ..common.packet.packet import NetworkPacket, NetworkPacketConfiguration, PhysicalPacket
from ..common.packet.apps.ran import RadioAccessNetworkConfiguration
from ..common.packet.apps.ran.ran_access_control import RANAccessControlRequest
from ..common.packet.apps.ran.ran_access_control import CreatePathRequest, RemovePathRequest, SwitchPathRequest
from ..common.packet.apps.ran.ran_access_control import CreatePathResponse, RemovePathResponse, SwitchPathResponse


class AccessAndMobilityManagementFunction(Stateless):

    LOGGING_OVERHEAD = "    "

    def __init__(self, name: str, amf_id: str, ran_config: RadioAccessNetworkConfiguration,
                 network_config: NetworkPacketConfiguration):
        """
        Access and Mobility Management Function xDEVS model
        :param name: name of the xDEVS module
        :param amf_id: ID of the Access and Mobility Management Function
        :param ran_config: RAN application Configuration
        :param network_config: network packets configuration
        """

        super().__init__(name=name)

        self.amf_id = amf_id
        self.ran_ac_config = ran_config
        self.network_config = network_config

        self.path_table = dict()  # {node_id: connected_ap}

        self.input_crosshaul = Port(PhysicalPacket, 'input_crosshaul')
        self.output_crosshaul = Port(PhysicalPacket, 'output_crosshaul')
        self.add_in_port(self.input_crosshaul)
        self.add_out_port(self.output_crosshaul)

    def check_in_ports(self):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        for job in self.input_crosshaul.values:
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

    def __encapsulate_network_packet(self, node_to: str, application_message):
        header = self.network_config.header
        return NetworkPacket(self.amf_id, node_to, header, application_message)

    def __encapsulate_physical_packet(self, node_to: str, network_message: NetworkPacket):
        return PhysicalPacket(node_from=self.amf_id, node_to=node_to, data=network_message)

    def __expand_physical_message(self, physical_message: PhysicalPacket):
        assert self.amf_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def __expand_network_message(self, network_message: NetworkPacket):
        assert self.amf_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __add_msg_to_crosshaul_dl(self, msg, network_to, physical_to):
        network = self.__encapsulate_network_packet(network_to, msg)
        msg = self.__encapsulate_physical_packet(physical_to, network)
        self.add_msg_to_queue(self.output_crosshaul, msg)

    def process_internal_messages(self):
        pass
