from xdevs.models import Port
from mercury.config.core import CoreConfig
from mercury.msg.edcs import EdgeDataCenterReport, DispatchingFunction, HotStandbyFunction
from mercury.msg.network import PhysicalPacket, CrosshaulPacket, NetworkPacket
from mercury.msg.network.packet.app_layer.edge_fed_mgmt import NewEDCReport, \
    NewDispatchingFunction, NewHotStandbyFunction
from mercury.msg.network.packet.app_layer.service import ServiceRequest, \
    StartSessionRequest, StopSessionRequest, ServiceResponse
from mercury.msg.smart_grid import PowerConsumptionReport
from ...common import ExtendedAtomic


class EdgeDataCenterInterface(ExtendedAtomic):
    def __init__(self, edc_id: str, lite: bool = False):
        """
        Data Center Interface implementation for xDEVS
        :param edc_id: ID of the corresponding Edge Data Center
        :param lite: flag for indicating whether the lite version is enabled or not
        """
        super().__init__(name='edge_fed_{}_interface'.format(edc_id))
        
        self.edc_id: str = edc_id
        self.lite: bool = lite
        self.routing_table: [ServiceRequest, str] = dict()

        port_type = NetworkPacket if lite else PhysicalPacket

        self.input_data = Port(port_type, 'input_data')
        self.input_service_response = Port(ServiceResponse, 'input_service_response')
        self.input_edc_consumption = Port(PowerConsumptionReport, 'input_power_consumption')
        self.output_data = Port(port_type, 'output_data')
        self.output_start_session_request = Port(StartSessionRequest, 'output_start_session_request')
        self.output_service_request = Port(ServiceRequest, 'output_service_request')
        self.output_stop_session_request = Port(StopSessionRequest, 'output_stop_session_request')
        self.output_new_dispatching = Port(DispatchingFunction, 'output_new_dispatching')
        self.output_new_hot_standby = Port(HotStandbyFunction, 'output_hot_standby')
        self.output_edc_report = Port(EdgeDataCenterReport, 'output_edc_report')

        self.add_in_port(self.input_data)
        self.add_in_port(self.input_service_response)
        self.add_in_port(self.input_edc_consumption)
        self.add_out_port(self.output_data)
        self.add_out_port(self.output_start_session_request)
        self.add_out_port(self.output_service_request)
        self.add_out_port(self.output_stop_session_request)
        self.add_out_port(self.output_new_dispatching)
        self.add_out_port(self.output_new_hot_standby)
        self.add_out_port(self.output_edc_report)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        self._process_session_ports()
        self._process_edc_report()
        self._process_xh_messages()
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def _process_session_ports(self):
        for job in self.input_service_response.values:
            request = job.request
            ue_id = request.client_id
            ap_id = self.routing_table.pop(request)
            self._add_msg_to_xh(job, ue_id, ap_id)

    def _process_edc_report(self):
        if self.input_edc_consumption:
            power_report = self.input_edc_consumption.get()
            self._add_msg_to_xh(NewEDCReport(power_report), CoreConfig.CORE_ID, CoreConfig.CORE_ID)
            self.add_msg_to_queue(self.output_edc_report, power_report.report)

    def _process_xh_messages(self):
        for job in self.input_data.values:
            if self.lite:
                physical_node_from, network_message = "lite", job
            else:
                physical_node_from, network_message = job.expanse_packet()
            network_node_from, app = network_message.expanse_packet()

            if isinstance(app, ServiceRequest):
                if app not in self.routing_table:
                    port = self.output_service_request
                    if isinstance(app, StartSessionRequest):
                        port = self.output_start_session_request
                    elif isinstance(app, StopSessionRequest):
                        port = self.output_stop_session_request
                    self.add_msg_to_queue(port, app)
                self.routing_table[app] = physical_node_from
            elif isinstance(app, NewDispatchingFunction):
                self.add_msg_to_queue(self.output_new_dispatching, app.dispatching)
            elif isinstance(app, NewHotStandbyFunction):
                self.add_msg_to_queue(self.output_new_hot_standby, app.hot_standby)
            else:
                raise Exception("Application message could not be identified")

    def _add_msg_to_xh(self, msg, network_to: str, physical_to: str):
        network = NetworkPacket(self.edc_id, network_to, msg)
        if self.lite:
            self.add_msg_to_queue(self.output_data, network)
        else:
            physical = CrosshaulPacket(self.edc_id, physical_to, network)
            self.add_msg_to_queue(self.output_data, physical)
