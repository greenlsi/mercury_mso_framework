from xdevs.models import Port
from ...common import Stateless
from ...common.edge_fed.edge_fed import EdgeDataCenterReport
from ...common.packet.packet import PhysicalPacket, NetworkPacketConfiguration, NetworkPacket
from ...common.packet.apps.service import ServiceRequest, CreateSessionRequestPacket, \
    RemoveSessionRequestPacket, OngoingSessionRequestPacket, CreateSessionResponsePacket, RemoveSessionResponsePacket, \
    OngoingSessionResponsePacket
from ...common.packet.apps.federation_management import FederationManagementConfiguration, \
    EdgeDataCenterReportPacket


class EdgeDataCenterInterface(Stateless):

    AP_ID = 'ap_id'
    UE_ID = 'ue_id'

    def __init__(self, name: str, edc_id: str, fed_mgmt_config: FederationManagementConfiguration,
                 network_config: NetworkPacketConfiguration, sdn_controller_id: str, lite=False):
        """
        Data Center Interface implementation for xDEVS
        :param name: Name of the stateless state machine xDEVS atomic module
        :param edc_id: ID of the corresponding Edge Data Center
        :param fed_mgmt_config: Federation Management application configuration
        :param network_config: network packets configuration
        :param sdn_controller_id: ID of the edge fed_controller_config controller
        """
        
        self.edc_id = edc_id
        self.fed_mgmt_config = fed_mgmt_config
        self.network_config = network_config
        self.sdn_controller_id = sdn_controller_id

        self.lite = lite

        self.routing_table = dict()

        super().__init__(name=name)

        out_type = NetworkPacket if lite else PhysicalPacket

        self.input_crosshaul = Port(out_type, 'input_crosshaul')
        self.input_create_session_response = Port(CreateSessionResponsePacket, 'input_create_session_resp')
        self.input_ongoing_session_response = Port(OngoingSessionResponsePacket, 'input_ongoing_session_resp')
        self.input_remove_session_response = Port(RemoveSessionResponsePacket, 'input_remove_session_resp')
        self.input_edc_report = Port(EdgeDataCenterReport, 'input_edc_report')
        self.output_create_session_request = Port(CreateSessionRequestPacket, 'output_create_session')
        self.output_ongoing_session_request = Port(OngoingSessionRequestPacket, 'output_ongoing_session')
        self.output_remove_session_request = Port(RemoveSessionRequestPacket, 'output_remove_session')
        self.output_crosshaul = Port(out_type, 'output_crosshaul')

        self.add_in_port(self.input_crosshaul)
        self.add_in_port(self.input_create_session_response)
        self.add_in_port(self.input_ongoing_session_response)
        self.add_in_port(self.input_remove_session_response)
        self.add_in_port(self.input_edc_report)
        self.add_out_port(self.output_create_session_request)
        self.add_out_port(self.output_ongoing_session_request)
        self.add_out_port(self.output_remove_session_request)
        self.add_out_port(self.output_crosshaul)

    def check_in_ports(self):
        self._process_session_ports()
        self._process_edc_report()
        self._process_crosshaul_messages()

    def _process_session_ports(self):
        for job in self.input_create_session_response.values:
            service_id = job.service_id
            session_id = job.session_id
            response = job.response
            routing = self.routing_table[(service_id, session_id)]
            if not response:
                self.routing_table.pop((service_id, session_id))
            ap_id = routing[self.AP_ID]
            ue_id = routing[self.UE_ID]
            self._add_msg_to_crosshaul(job, ue_id, ap_id)
        for job in self.input_ongoing_session_response.values:
            service_id = job.service_id
            session_id = job.session_id
            routing = self.routing_table[(service_id, session_id)]
            ap_id = routing[self.AP_ID]
            ue_id = routing[self.UE_ID]
            self._add_msg_to_crosshaul(job, ue_id, ap_id)
        for job in self.input_remove_session_response.values:
            service_id = job.service_id
            session_id = job.session_id
            response = job.response
            routing = self.routing_table.get((service_id, session_id))
            ap_id = routing[self.AP_ID]
            ue_id = routing[self.UE_ID]
            if response:
                self.routing_table.pop((service_id, session_id))
            self._add_msg_to_crosshaul(job, ue_id, ap_id)

    def _process_edc_report(self):
        if self.input_edc_report:
            edc_report = self.input_edc_report.get()
            header = self.fed_mgmt_config.header
            data = self.fed_mgmt_config.edc_report_data
            msg = EdgeDataCenterReportPacket(edc_report, header, data)
            self._add_msg_to_crosshaul(msg, self.sdn_controller_id, self.sdn_controller_id)

    def _process_crosshaul_messages(self):
        for job in self.input_crosshaul.values:
            if self.lite:
                physical_node_from, network_message = "lite", job
            else:
                physical_node_from, network_message = self._expand_physical_message(job)
            network_node_from, app = self._expand_network_message(network_message)
            # CASE 1: Service message
            if isinstance(app, ServiceRequest):
                ap_id = physical_node_from
                ue_id = network_node_from
                service_id = app.service_id
                session_id = app.session_id
                if isinstance(app, CreateSessionRequestPacket):
                    if (service_id, session_id) not in self.routing_table:
                        self.routing_table[(service_id, session_id)] = dict()
                    self.routing_table[(service_id, session_id)][self.AP_ID] = ap_id
                    self.routing_table[(service_id, session_id)][self.UE_ID] = ue_id
                    self.add_msg_to_queue(self.output_create_session_request, app)
                elif isinstance(app, OngoingSessionRequestPacket):
                    if (service_id, session_id) in self.routing_table:
                        self.routing_table[(service_id, session_id)][self.AP_ID] = ap_id
                        self.routing_table[(service_id, session_id)][self.UE_ID] = ue_id
                        self.add_msg_to_queue(self.output_ongoing_session_request, app)
                    # TODO Send negative response?
                elif isinstance(app, RemoveSessionRequestPacket):
                    if (service_id, session_id) in self.routing_table:
                        self.routing_table[(service_id, session_id)][self.AP_ID] = ap_id
                        self.routing_table[(service_id, session_id)][self.UE_ID] = ue_id
                        self.add_msg_to_queue(self.output_remove_session_request, app)
                    # TODO Send affirmative response?
                else:
                    raise Exception("Service-related application message could not be identified")
            else:
                raise Exception("Application message could not be identified")

    def _encapsulate_network_packet(self, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(self.edc_id, node_to, header, application_message)

    def _encapsulate_physical_packet(self, node_to: str, network_message: NetworkPacket):
        return PhysicalPacket(node_from=self.edc_id, node_to=node_to, data=network_message)

    def _expand_physical_message(self, physical_message):
        # assert self.edc_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def _expand_network_message(self, network_message):
        assert self.edc_id == network_message.node_to
        return network_message.node_from, network_message.data

    def _add_msg_to_crosshaul(self, msg, network_to, physical_to):
        network = self._encapsulate_network_packet(network_to, msg)
        if self.lite:
            self.add_msg_to_queue(self.output_crosshaul, network)
        else:
            physical = self._encapsulate_physical_packet(physical_to, network)
            self.add_msg_to_queue(self.output_crosshaul, physical)

    def process_internal_messages(self):
        pass
