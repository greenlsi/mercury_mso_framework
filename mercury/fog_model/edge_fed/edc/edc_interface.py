import logging
from copy import deepcopy
from xdevs.models import Port
from ...common import TransmissionDelayer, logging_overhead
from ...common.edge_fed import EdgeDataCenterReport
from ...common.crosshaul import CrosshaulConfiguration, CrosshaulTransceiverConfiguration
from ...common.packet.physical import PhysicalPacket
from ...common.packet.network import NetworkPacketConfiguration, NetworkPacket
from ...common.packet.application.service import ServiceRequest, CreateSessionRequestPacket, \
    RemoveSessionRequestPacket, OngoingSessionRequestPacket, CreateSessionResponsePacket, RemoveSessionResponsePacket, \
    OngoingSessionResponsePacket
from ...common.packet.application.federation_management import FederationManagementConfiguration, \
    EdgeDataCenterReportPacket
from .internal_ports import EDCOverallReport, CreateSession, CreateSessionResponse, RemoveSession, RemoveSessionResponse


SERVICE_AWAITING = 'awaiting'
SERVICE_ONGOING = 'ongoing'
SERVICE_REMOVING = 'removing'

AP_ID = 'connected_ap'
UE_ID = 'node_id'
SERVICE_U = 'service_u'
STATUS = 'status'


LOGGING_OVERHEAD = "        "


class EdgeDataCenterInterface(TransmissionDelayer):
    """
    Data Center Interface implementation for xDEVS
    :param str name: Name of the stateless state machine xDEVS atomic module
    :param str edc_id: ID of the corresponding Edge Data Center
    :param CrosshaulTransceiverConfiguration crosshaul_transceiver: crosshaul_config transceiver configuration
    :param dict services_config: dictionary {service_id: ServiceConfiguration}
    :param FederationManagementConfiguration fed_mgmt_config: Federation Management application configuration
    :param NetworkPacketConfiguration network_config: network packets configuration
    :param CrosshaulConfiguration crosshaul_config: Crosshaul layer configuration parameters
    :param str fed_controller_id: ID of the edge fed_controller_config controller
    """
    def __init__(self, name, edc_id, crosshaul_transceiver, services_config, fed_mgmt_config, network_config,
                 crosshaul_config, fed_controller_id):
        self.edc_id = edc_id
        self.crosshaul_transceiver = crosshaul_transceiver
        self.services_config = services_config
        self.fed_mgmt_config = fed_mgmt_config
        self.network_config = network_config
        self.crosshaul_config = crosshaul_config
        self.fed_controller_id = fed_controller_id

        self.routing_table = dict()  # TODO separar tabla de enrutado y de servicio
        self.edc_report = None

        super().__init__(name=name)

        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.input_create_session_response = Port(CreateSessionResponse, name + '_input_create_session_response')
        self.input_remove_session_response = Port(RemoveSessionResponse, name + '_input_remove_session_response')
        self.input_overall_report = Port(EDCOverallReport, name + '_input_overall_report')
        self.output_create_session = Port(CreateSession, name + '_output_create_session')
        self.output_remove_session = Port(RemoveSession, name + '_output_remove_session')
        self.output_crosshaul_dl = Port(PhysicalPacket, name + '_output_crosshaul_dl')
        self.output_crosshaul_ul = Port(PhysicalPacket, name + '_output_crosshaul_ul')
        self.output_edc_report = Port(EdgeDataCenterReport, name + '_output_overall_report')

        self.add_in_port(self.input_crosshaul_ul)
        self.add_in_port(self.input_create_session_response)
        self.add_in_port(self.input_remove_session_response)
        self.add_in_port(self.input_overall_report)
        self.add_out_port(self.output_create_session)
        self.add_out_port(self.output_remove_session)
        self.add_out_port(self.output_crosshaul_dl)
        self.add_out_port(self.output_crosshaul_ul)
        self.add_out_port(self.output_edc_report)

    def check_in_ports(self):
        self._process_create_session_response()
        self._process_remove_session_response()
        self._process_overall_status()
        self._process_crosshaul_messages()

    def _process_overall_status(self):
        if self.input_overall_report:
            self.edc_report = deepcopy(self.input_overall_report.get().p_units_reports)
            self.__send_overall_report()

    def _process_create_session_response(self):
        """Process Create Service Response messages"""
        for job in self.input_create_session_response.values:
            service_id = job.service_id
            session_id = job.session_id
            response = job.response
            ap_id = self.routing_table[service_id][session_id][AP_ID]
            ue_id = self.routing_table[service_id][session_id][UE_ID]
            status = self.routing_table[service_id][session_id][STATUS]
            if status != SERVICE_AWAITING:
                raise Exception("Created service was not awaited")

            if response:
                self.routing_table[service_id][session_id][STATUS] = SERVICE_ONGOING
            else:
                self.routing_table[service_id].pop(session_id)
                if not self.routing_table[service_id]:
                    self.routing_table.pop(service_id)
            # Forward create service response to UE
            app = CreateSessionResponsePacket(service_id, session_id, response, self.services_config[service_id].header)
            self.__add_msg_to_crosshaul_dl(app, ue_id, ap_id)

    def _process_remove_session_response(self):
        """Process Remove Service Response messages"""
        for job in self.input_remove_session_response.values:
            service_id = job.service_id
            session_id = job.session_id
            response = job.response
            ap_id = self.routing_table[service_id][session_id][AP_ID]
            ue_id = self.routing_table[service_id][session_id][UE_ID]
            status = self.routing_table[service_id][session_id][STATUS]
            if status != SERVICE_REMOVING:
                raise Exception("Removed service was not awaited to be removed")

            if response:
                self.routing_table[service_id].pop(session_id)
                if not self.routing_table[service_id]:
                    self.routing_table.pop(service_id)
            else:
                self.routing_table[service_id][session_id][STATUS] = SERVICE_ONGOING
            # Forward remove pxsch response to UE
            app = RemoveSessionResponsePacket(service_id, session_id, response, self.services_config[service_id].header)
            self.__add_msg_to_crosshaul_dl(app, ue_id, ap_id)

    def _process_crosshaul_messages(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        for job in self.input_crosshaul_ul.values:
            physical_node_from, network_message = self.__expand_physical_message(job)
            network_node_from, app = self.__expand_network_message(network_message)
            # CASE 1: Service message
            if isinstance(app, ServiceRequest):
                ap_id = physical_node_from
                ue_id = network_node_from
                service_id = app.service_id
                session_id = app.session_id
                if isinstance(app, OngoingSessionRequestPacket):
                    packet_id = app.packet_id
                    self._process_ongoing_session_request(ap_id, ue_id, service_id, session_id, packet_id, overhead)
                elif isinstance(app, CreateSessionRequestPacket):
                    service_u = self.services_config[service_id].service_u
                    self._process_create_session_request(ap_id, ue_id, service_id, session_id, service_u, overhead)
                elif isinstance(app, RemoveSessionRequestPacket):
                    self._process_remove_session_request(ap_id, ue_id, service_id, session_id, overhead)
                else:
                    raise Exception("Service-related application message could not be identified")
            else:
                raise Exception("Application message could not be identified")  # TODO meter cosas del controller etc

    def _process_ongoing_session_request(self, ap_id, ue_id, service_id, session_id, packet_id, overhead):
        """Process incoming Service Session Request messages"""
        logging.info(overhead + "%s--->%s: Ongoing session (%s,%s) request (%i)" % (ap_id, self.edc_id, service_id, session_id, packet_id))

        # Only react to session request if service ID is on routing table
        if service_id in self.routing_table and session_id in self.routing_table[service_id]:
            self.routing_table[service_id][session_id][AP_ID] = ap_id  # Refresh routing table
            status = self.routing_table[service_id][session_id][STATUS]
            if status == SERVICE_ONGOING:
                header = self.services_config[service_id].header
                app = OngoingSessionResponsePacket(service_id, session_id, True, header, packet_id)
                self.__add_msg_to_crosshaul_dl(app, ue_id, ap_id)
            else:
                logging.warning(overhead + "    Service is not ongoing. Request is ignored")
        else:
            logging.warning(overhead + "    Service is not in routing table. Request is ignored")

    def _process_create_session_request(self, ap_id, ue_id, service_id, session_id, service_u, overhead):
        """Process incoming Create Service Messages"""
        logging.info(overhead + "%s--->%s: create Session (%s,%s) request" % (ap_id, self.edc_id, service_id, session_id))
        # CASE 1: Service is completely new
        if service_id not in self.routing_table:
            self.routing_table[service_id] = dict()
        if session_id not in self.routing_table[service_id]:
            self.routing_table[service_id][session_id] = dict()
            self.routing_table[service_id][session_id][AP_ID] = ap_id
            self.routing_table[service_id][session_id][UE_ID] = ue_id
            self.routing_table[service_id][session_id][SERVICE_U] = service_u
            self.routing_table[service_id][session_id][STATUS] = SERVICE_AWAITING
            # Forward create pxsch request to resource manager
            msg = CreateSession(service_id, session_id, service_u)
            self.add_msg_to_queue(self.output_create_session, msg)
        # CASE 2: Service is already in routing table
        else:
            assert ue_id == self.routing_table[service_id][session_id][UE_ID]  # UE ID must be the same
            self.routing_table[service_id][session_id][AP_ID] = ap_id  # Refresh routing table
            status = self.routing_table[service_id][session_id][STATUS]
            if status == SERVICE_ONGOING:
                logging.warning(overhead + "    Service already deployed. Sending affirmative response")
                # Forward create pxsch response to UE
                header = self.services_config[service_id].header
                app = CreateSessionResponsePacket(service_id, session_id, True, header)
                self.__add_msg_to_crosshaul_dl(app, ue_id, ap_id)
            else:
                logging.warning(overhead + "    Service already in routing table with status '%s'. Request is ignored" % status)

    def _process_remove_session_request(self, ap_id, ue_id, service_id, session_id, overhead):
        """Process incoming Remove Service messages"""
        logging.info(overhead + "%s--->%s: remove Service (%s,%s) request" % (ap_id, self.edc_id, service_id, session_id))

        # CASE 1: pxsch in routing table
        if service_id in self.routing_table and session_id in self.routing_table[service_id]:
            assert ue_id == self.routing_table[service_id][session_id][UE_ID]  # UE ID must be the same
            self.routing_table[service_id][session_id][AP_ID] = ap_id  # Refresh routing table
            status = self.routing_table[service_id][session_id][STATUS]
            if status == SERVICE_ONGOING:
                self.routing_table[service_id][session_id][STATUS] = SERVICE_REMOVING
                # Forward remove pxsch request to resource manager
                msg = RemoveSession(service_id, session_id)
                self.add_msg_to_queue(self.output_remove_session, msg)
            else:
                logging.warning(overhead + "    Service already in routing table with status '%s'. Request is ignored" % status)
        # CASE 2: pxsch not found in routing table
        else:
            logging.warning(overhead + "    Service not found in routing table. Sending affirmative response")
            # Forward remove pxsch response to UE
            header = self.services_config[service_id].header
            app = RemoveSessionResponsePacket(service_id, session_id, True, header)
            self.__add_msg_to_crosshaul_dl(app, ue_id, ap_id)

    def __encapsulate_network_packet(self, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(self.edc_id, node_to, header, application_message)

    def __encapsulate_physical_packet(self, node_to, network_message):
        header = self.crosshaul_config.header
        power, bandwidth, spectral_efficiency = self.crosshaul_transceiver.get()
        return PhysicalPacket(self.edc_id, node_to, power, bandwidth, spectral_efficiency, header, network_message)

    def __expand_physical_message(self, physical_message):
        assert self.edc_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def __expand_network_message(self, network_message):
        assert self.edc_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __send_overall_report(self):
        total_u = 0
        used_u = 0
        power = 0
        for pu_report in self.edc_report:
            total_u += 100 * pu_report.pu_std_to_spec
            used_u += pu_report.utilization * pu_report.pu_std_to_spec
            power += pu_report.power
        edc_report = EdgeDataCenterReport(self.edc_id, used_u, total_u, power, self.routing_table, self.edc_report)
        self.add_msg_to_queue(self.output_edc_report, edc_report)
        app = EdgeDataCenterReportPacket(edc_report, self.fed_mgmt_config.header, self.fed_mgmt_config.edc_report_data)
        self.__add_msg_to_crosshaul_ul(app, self.fed_controller_id, self.fed_controller_id)

    def __add_msg_to_crosshaul_dl(self, msg, network_to, physical_to):
        network = self.__encapsulate_network_packet(network_to, msg)
        msg = self.__encapsulate_physical_packet(physical_to, network)
        size = msg.compute_size()
        channel = "crosshaul_dl"
        self.add_msg_to_buffer(self.output_crosshaul_dl, msg, channel, size, msg.bandwidth, msg.spectral_efficiency)

    def __add_msg_to_crosshaul_ul(self, msg, network_to, physical_to):
        network = self.__encapsulate_network_packet(network_to, msg)
        msg = self.__encapsulate_physical_packet(physical_to, network)
        size = msg.compute_size()
        channel = "crosshaul_ul"
        self.add_msg_to_buffer(self.output_crosshaul_ul, msg, channel, size, msg.bandwidth, msg.spectral_efficiency)
