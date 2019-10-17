import logging
from copy import deepcopy
from xdevs.models import Port
from ..common import TransmissionDelayer, logging_overhead
from ..common.edge_fed import EdgeFederationControllerConfiguration
from ..common.crosshaul import CrosshaulConfiguration
from ..common.packet.physical import PhysicalPacket
from ..common.packet.network import NetworkPacketConfiguration, NetworkPacket
from ..common.packet.application.federation_management import FederationManagementConfiguration, \
    EdgeDataCenterReportPacket, EdgeFederationReportPacket

LOGGING_OVERHEAD = "        "


class FederationController(TransmissionDelayer):
    """
    Edge Federation Controller xDEVS model
    :param str name: name of the xDEVS module
    :param EdgeFederationControllerConfiguration controller_config: Edge Federation Controller Configuration
    :param FederationManagementConfiguration fed_mgmt_config: Federation Management application configuration
    :param NetworkPacketConfiguration network_config: configuration for network packets
    :param CrosshaulConfiguration crosshaul_config: Configuration for crosshaul_config physical packets
    :param str sdn_controller_id: ID of the SDN controller function
    :param list edc_ids: list of IDs of Edge Data Centes within the Edge Federation
    """
    def __init__(self, name, controller_config, fed_mgmt_config, network_config, crosshaul_config, sdn_controller_id,
                 edc_ids):
        super().__init__(name=name)

        # Unwrap configuration parameters
        self.fed_controller_id = controller_config.controller_id
        self.controller_location = controller_config.controller_location
        self.crosshaul_transceiver = controller_config.crosshaul_transceiver_config

        self.fed_mgmt_config = fed_mgmt_config
        self.network_config = network_config
        self.crosshaul_config = crosshaul_config
        self.sdn_controller_id = sdn_controller_id
        self.edc_ids = [edc_id for edc_id in edc_ids]
        self.n_edc = len(edc_ids)
        self.edc_reports = {edc_id: None for edc_id in edc_ids}
        self.report_to_send = None

        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.output_crosshaul_ul = Port(PhysicalPacket, name + '_output_crosshaul_ul')
        self.add_in_port(self.input_crosshaul_ul)
        self.add_out_port(self.output_crosshaul_ul)

    def check_in_ports(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        reports_to_send = dict()
        for job in self.input_crosshaul_ul.values:
            network_node_from, network_msg = self.__expand_physical_message(job)
            app_node_from, app_msg = self.__expand_network_message(network_msg)
            if isinstance(app_msg, EdgeDataCenterReportPacket):
                edc_id = app_node_from
                report = deepcopy(app_msg)
                logging.info(overhead + "%s->Edge Controller: new Edge Data Center report" % edc_id)
                self.edc_reports[edc_id] = report
                reports_to_send[edc_id] = report
        if reports_to_send:
            msg = EdgeFederationReportPacket(reports_to_send, self.fed_mgmt_config.header,
                                             self.fed_mgmt_config.edc_report_data * len(reports_to_send))
            self.__add_msg_to_crosshaul_ul(msg, self.sdn_controller_id, self.sdn_controller_id)

    def __encapsulate_network_packet(self, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(self.fed_controller_id, node_to, header, application_message)

    def __encapsulate_physical_packet(self, node_to, network_message):
        header = self.crosshaul_config.header
        power, bandwidth, spectral_eff = self.crosshaul_transceiver.get()
        return PhysicalPacket(self.fed_controller_id, node_to, power, bandwidth, spectral_eff, header, network_message)

    def __expand_physical_message(self, physical_message):
        assert self.fed_controller_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def __expand_network_message(self, network_message):
        assert self.fed_controller_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __add_msg_to_crosshaul_ul(self, msg, network_to, physical_to):
        network = self.__encapsulate_network_packet(network_to, msg)
        msg = self.__encapsulate_physical_packet(physical_to, network)
        size = msg.compute_size()
        channel = "crosshaul_ul"
        self.add_msg_to_buffer(self.output_crosshaul_ul, msg, channel, size, msg.bandwidth, msg.spectral_efficiency)
