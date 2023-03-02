from __future__ import annotations
from mercury.config.edcs import EdgeFederationConfig
from mercury.config.gateway import GatewaysConfig
from mercury.logger import logger as logging, logging_overhead
from mercury.msg.edcs import EdgeDataCenterReport
from mercury.msg.packet.app_packet import AppPacket
from mercury.msg.packet.app_packet.edc_packet import EDCReportPacket
from mercury.msg.packet.app_packet.srv_packet import SrvRelatedRequest, \
    SrvRelatedResponse, SrvRequest, SrvResponse, OpenSessRequest, OpenSessResponse
from mercury.utils.amf import AccessManagementFunction
from xdevs.models import Port
from ...common import ExtendedAtomic


class EDCInterface(ExtendedAtomic):
    LOGGING_OVERHEAD = '        '

    def __init__(self, edc_id: str, edge_fed_config: EdgeFederationConfig,
                 gws_config: GatewaysConfig, amf: AccessManagementFunction):
        """
        Data Center Interface implementation for xDEVS
        :param edc_id: ID of the corresponding edge data center.
        :param edge_fed_config: edge federation configuration parameters.
        :param gws_config: configuration of the gateways in the RAN.
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        from mercury.plugin import AbstractFactory, ServerMappingStrategy

        self.edc_id: str = edc_id
        self.edge_fed_config: EdgeFederationConfig = edge_fed_config
        self.mapper: ServerMappingStrategy = AbstractFactory.create_edc_server_mapping(
            edge_fed_config.mapping_id, **edge_fed_config.mapping_config,
            edc_id=self.edc_id, amf=amf, gws_config=gws_config, edge_fed_config=edge_fed_config
        )
        self.edc_report: EdgeDataCenterReport | None = None
        super().__init__(name=f'edc_{self.edc_id}_inf')
        self.input_report: Port[EdgeDataCenterReport] = Port(EdgeDataCenterReport, 'input_report')
        self.input_srv: Port[SrvRelatedResponse] = Port(SrvRelatedResponse, 'input_srv')
        self.input_app: Port[AppPacket] = Port(AppPacket, 'input_app')
        self.output_srv: Port[SrvRelatedRequest] = Port(SrvRelatedRequest, 'output_srv')
        self.output_app: Port[AppPacket] = Port(AppPacket, 'output_app')
        self.add_in_port(self.input_report)
        self.add_in_port(self.input_srv)
        self.add_in_port(self.input_app)
        self.add_out_port(self.output_srv)
        self.add_out_port(self.output_app)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        if self.input_report:
            self.edc_report = self.input_report.get()
            self.mapper.update_edc_report(self.edc_report)
            for edc_id in self.edge_fed_config.edcs_config:
                if edc_id != self.edc_id:
                    edc_report_packet = EDCReportPacket(edc_id, self.edc_report, self._clock)
                    edc_report_packet.send(self._clock)
                    self.add_msg_to_queue(self.output_app, edc_report_packet)
        for msg in self.input_srv.values:
            self.add_msg_to_queue(self.output_app, msg)
        srv_reqs: list[SrvRelatedRequest] = list()
        for msg in self.input_app.values:
            if isinstance(msg, EDCReportPacket):
                msg.receive(self._clock)
                self.mapper.update_edc_report(msg.edc_report)
            elif isinstance(msg, SrvRelatedRequest):
                srv_reqs.append(msg)
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        for msg in srv_reqs:
            self.process_srv_request(overhead, msg)
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def process_srv_request(self, overhead: str, req: SrvRelatedRequest):
        if req.server_id == self.edc_id:  # Request is already attached to this server
            self.add_msg_to_queue(self.output_srv, req)
        else:
            server_id = self.mapper.map_server(req)
            log_msg = f'{overhead}{self.edc_id}: request {req} server map: {server_id}'
            if server_id is None:
                if self.edge_fed_config.cloud_id is not None:
                    log_msg = f'{log_msg}. Sending to cloud {self.edge_fed_config.cloud_id}'
                    req.set_server(self.edge_fed_config.cloud_id)
                    self.add_msg_to_queue(self.output_app, req)
                else:
                    req.receive(self._clock)
                    if isinstance(req, SrvRequest):
                        output = SrvResponse(req, False, self._clock, 'No available server')
                    elif isinstance(req, OpenSessRequest):
                        output = OpenSessResponse(req, None, self._clock, 'No available server')
                    else:
                        raise TypeError(f'unknown data type: {type(req)}')
                    output.send(self._clock)
                    self.add_msg_to_queue(self.output_app, output)
                logging.warning(log_msg)
            else:
                logging.info(log_msg)
                req.set_server(server_id)
                if server_id == self.edc_id:  # Request is already attached to this server
                    self.add_msg_to_queue(self.output_srv, req)
                else:
                    self.add_msg_to_queue(self.output_app, req)
