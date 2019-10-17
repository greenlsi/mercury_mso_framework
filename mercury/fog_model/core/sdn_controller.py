import logging
from copy import deepcopy
from xdevs.models import Port
from ..common import TransmissionDelayer, logging_overhead
from ..common.packet.application.federation_management import FederationManagementPacket, FederationManagementConfiguration
from ..common.packet.application.federation_management import EdgeFederationReportPacket, NewSDNPath
from ..common.packet.network import NetworkPacketConfiguration, NetworkPacket
from ..common.packet.physical import PhysicalPacket
from ..common.crosshaul import CrosshaulConfiguration, CrosshaulTransceiverConfiguration
from ..common.core import SDNStrategy


LOGGING_OVERHEAD = "        "


class SDNController(TransmissionDelayer):
    def __init__(self, name, sdn_controller_id, fed_mgmt_config, network_config, crosshaul_config,
                 crosshaul_transceiver, fed_controller_id, aps_location, edcs_location, sdn_strategy=None):
        """
        xDEVS model of a Software-Defined Network Controller for interconnecting Acess Points and Edge Data Centers
        :param str name: Name of the XDEVS SDN Controller module
        :param str sdn_controller_id: ID of the SDN controller
        :param FederationManagementConfiguration fed_mgmt_config: fed_controller_config management application configuration
        :param NetworkPacketConfiguration network_config: network packets configuration
        :param CrosshaulConfiguration crosshaul_config: crosshaul_config packets configuration
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver: crosshaul_config transceiver
        :param str fed_controller_id: ID of the Edge Federation Controller
        :param dict aps_location: dictionary {AP ID: AP ue_location}
        :param dict edcs_location: dictionary {EDC ID: EDC ue_location}
        :param SDNStrategy sdn_strategy: Software-Defined Network linking strategy
        """
        super().__init__(name=name)

        self.sdn_controller_id = sdn_controller_id
        self.fed_mgmt_config = fed_mgmt_config
        self.network_config = network_config
        self.crosshaul_config = crosshaul_config
        self.crosshaul_transceiver = crosshaul_transceiver
        self.fed_controller_id = fed_controller_id
        self.sdn_strategy = sdn_strategy
        self.aps_location = aps_location
        self.edcs_location = edcs_location

        self.federation_report = {edc_id: None for edc_id in edcs_location.keys()}
        self.designed_edcs = {ap_id: {service_id: None for service_id in sdn_strategy.services_id} for ap_id in aps_location.keys()}

        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.output_crosshaul_dl = Port(PhysicalPacket, name + '_output_crosshaul_dl')
        self.add_in_port(self.input_crosshaul_ul)
        self.add_out_port(self.output_crosshaul_dl)

    def check_in_ports(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        for job in self.input_crosshaul_ul.values:
            phys_node_from, net_msg = self.__expand_physical_message(job)
            net_node_from, app_msg = self.__expand_network_message(net_msg)
            if isinstance(app_msg, FederationManagementPacket):
                if isinstance(app_msg, EdgeFederationReportPacket):
                    logging.info(overhead + "SDNController: received Federation status")
                    for edc_id, edc_report in app_msg.edc_reports.items():
                        # Update fed_controller_config status
                        self.federation_report[edc_id] = deepcopy(edc_report)
                else:
                    raise Exception("Edge fed_controller_config management packet type was not identified by SDN controller")
            else:
                raise Exception("Message type was not identified by SDN controller")
        self._update_availability_list()
        self._select_edc_bindings(overhead)

    def _update_availability_list(self):
        """Computes EDC utilization factor and updates EDC availability list"""
        for edc_id, edc_report_packet in self.federation_report.items():
            if edc_report_packet is None:
                continue
            edc_report = edc_report_packet.edc_report
            utilization_dict = edc_report.relative_u_per_service
            overall_utilization = edc_report.relative_u
            self.sdn_strategy.update_edc_utilization(edc_id, utilization_dict, overall_utilization)

    def _select_edc_bindings(self, overhead):
        """Select paths APs and EDCs. If a change is detected, the SDN Controller sends a message to the AP."""
        for ap_id in self.aps_location:
            edcs_per_service = self.sdn_strategy.assign_edc(ap_id)
            flag = False
            for service_id, edc_id in edcs_per_service.items():
                if edc_id != self.designed_edcs[ap_id][service_id]:
                    flag = True
                    self.designed_edcs[ap_id][service_id] = edc_id
                    if edc_id is None:
                        logging.warning(overhead + "    SDN controller could not find any available EDC for service %s" % service_id)
                    else:
                        logging.info(overhead + "    SDN found new EDC %s for AP %s and service %s" % (edc_id, ap_id, service_id))
            if flag:
                msg = NewSDNPath(self.designed_edcs[ap_id], self.fed_mgmt_config.header)
                self.__add_msg_to_crosshaul_dl(msg, ap_id, ap_id)

    def __encapsulate_network_packet(self, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(self.sdn_controller_id, node_to, header, application_message)

    def __encapsulate_physical_packet(self, node_to, network_message):
        header = self.crosshaul_config.header
        power, bandwidth, spectral_eff = self.crosshaul_transceiver.get()
        return PhysicalPacket(self.sdn_controller_id, node_to, power, bandwidth, spectral_eff, header, network_message)

    def __expand_physical_message(self, physical_message):
        assert self.sdn_controller_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def __expand_network_message(self, network_message):
        assert self.sdn_controller_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __add_msg_to_crosshaul_dl(self, msg, network_to, physical_to):
        network = self.__encapsulate_network_packet(network_to, msg)
        msg = self.__encapsulate_physical_packet(physical_to, network)
        size = msg.compute_size()
        channel = "crosshaul_dl"
        self.add_msg_to_buffer(self.output_crosshaul_dl, msg, channel, size, msg.bandwidth, msg.spectral_efficiency)
