from collections import defaultdict
from math import inf, ceil
from mercury.config.edcs import EdgeDataCenterConfig
from mercury.logger import logger as logging, logging_overhead
from mercury.msg.edcs import EdgeDataCenterReport, ProcessingUnitReport, ProcessingUnitHotStandBy, \
    ProcessingUnitServiceRequest,  ProcessingUnitServiceResponse, CoolerReport, DispatchingFunction, HotStandbyFunction
from mercury.msg.network.packet.app_layer.service import ServiceRequest, \
    StartSessionRequest, StopSessionRequest, ServiceResponse
from mercury.msg.smart_grid import PowerDemandReport, PowerConsumptionReport
from typing import ClassVar, Dict, Set, Tuple
from xdevs.models import Port, PHASE_PASSIVE
from .dispatcher import EdgeDataCenterDispatcher
from ....common import ExtendedAtomic


class ResourceManager(ExtendedAtomic):

    LOGGING_OVERHEAD: ClassVar[str] = "            "

    def __init__(self, edc_config: EdgeDataCenterConfig, services: Set[str], smart_grid: bool):
        """
        Resource Manager xDEVS module
        :param edc_config: Edge Data Center model configuration
        :param services: set containing the ID of all the services in the scenario
        :param smart_grid: it indicates if the smart grid layer is activated or not
        """
        super().__init__(name=f"edge_fed_{edc_config.edc_id}_r_manager")

        self.edc_id: str = edc_config.edc_id
        self.edc_location: Tuple[float, ...] = edc_config.edc_location
        self.env_temp: float = edc_config.env_temp
        self.smart_grid: bool = smart_grid
        self.start: bool = True

        self.dispatcher: EdgeDataCenterDispatcher = EdgeDataCenterDispatcher(edc_config)
        self.cool_down: float = edc_config.r_manager_config.cool_down
        self.next_hot_standby: float = 0

        self.max_sessions: Dict[str, int] = dict()
        for service_id in services:
            self.max_sessions[service_id] = 0
            for pu_config in edc_config.pus_config.values():
                srv_conf = pu_config.services.get(service_id)
                srv_u = 0 if srv_conf is None else srv_conf.max_u
                if 0 < srv_u <= 100:
                    self.max_sessions[service_id] += ceil(100 / srv_u)

        # Define input/output ports
        self.input_new_dispatching = Port(DispatchingFunction, 'input_new_dispatching')
        self.input_new_hot_standby = Port(HotStandbyFunction, 'input_new_hot_standby')
        self.input_start_session_request = Port(StartSessionRequest, 'input_start_session_request')
        self.input_service_request = Port(ServiceRequest, 'input_service_request')
        self.input_stop_session_request = Port(StopSessionRequest, 'input_stop_session_request')
        self.output_service_response = Port(ServiceResponse, 'output_service_response')

        self.add_in_port(self.input_new_dispatching)
        self.add_in_port(self.input_new_hot_standby)
        self.add_in_port(self.input_start_session_request)
        self.add_in_port(self.input_service_request)
        self.add_in_port(self.input_stop_session_request)
        self.add_out_port(self.output_service_response)

        self.input_pu_report = Port(ProcessingUnitReport, 'input_pu_report')
        self.input_start_session_response = Port(ProcessingUnitServiceResponse, 'input_start_session_response')
        self.input_service_response = Port(ProcessingUnitServiceResponse, 'input_service_response')
        self.input_stop_session_response = Port(ProcessingUnitServiceResponse, 'input_stop_session_response')

        self.add_in_port(self.input_pu_report)
        self.add_in_port(self.input_start_session_response)
        self.add_in_port(self.input_service_response)
        self.add_in_port(self.input_stop_session_response)

        self.outputs_hot_standby = dict()
        self.outputs_start_session_request = dict()
        self.outputs_service_request = dict()
        self.outputs_stop_session_request = dict()
        for pu_id in self.dispatcher.pu_twins.keys():
            self.outputs_hot_standby[pu_id] = Port(ProcessingUnitHotStandBy, f"output_{pu_id}_hot_standby")
            self.outputs_start_session_request[pu_id] = Port(ProcessingUnitServiceRequest, f"output_{pu_id}_start")
            self.outputs_service_request[pu_id] = Port(ProcessingUnitServiceRequest, f"output_{pu_id}_service")
            self.outputs_stop_session_request[pu_id] = Port(ProcessingUnitServiceRequest, f"output_{pu_id}_stop")
            self.add_out_port(self.outputs_hot_standby[pu_id])
            self.add_out_port(self.outputs_start_session_request[pu_id])
            self.add_out_port(self.outputs_service_request[pu_id])
            self.add_out_port(self.outputs_stop_session_request[pu_id])

        self.output_cooler_report = Port(CoolerReport, 'output_cooler_report')
        self.add_out_port(self.output_cooler_report)

        if self.smart_grid:
            self.output_power_demand = Port(PowerDemandReport, 'output_power_demand_report')
            self.add_out_port(self.output_power_demand)
        else:
            self.output_power_consumption = Port(PowerConsumptionReport, 'output_power_consumption')
            self.add_out_port(self.output_power_consumption)

    @property
    def it_power(self) -> float:
        return sum(pu_twin.latest_report.power for pu_twin in self.dispatcher.pu_twins.values())

    @property
    def cooling_power(self) -> float:
        return self.dispatcher.cooler.cooling_power if self.dispatcher.cooler is not None else 0

    @property
    def ongoing_sessions(self) -> Dict[str, Set[str]]:
        res: Dict[str, Set[str]] = defaultdict(lambda: set())
        for session_dict in (self.dispatcher.starting, self.dispatcher.started, self.dispatcher.stopping):
            for service_id, sessions in session_dict.items():
                for client_id in sessions:
                    res[service_id].add(client_id)
        return res

    @property
    def tasks_progress(self) -> Dict[str, Dict[ServiceRequest, float]]:
        res: Dict[str, Dict[ServiceRequest, float]] = defaultdict(lambda: dict())
        for pu_twin in self.dispatcher.pu_twins.values():
            pu_report = pu_twin.latest_report
            if pu_report is not None:
                for service_id, requests in pu_report.request_share.items():
                    for request, (_, progress) in requests.items():
                        res[service_id][request] = progress
        return res

    @property
    def utilization(self) -> float:
        total_u = 0
        n_pu = 0
        for pu_twin in self.dispatcher.pu_twins.values():
            total_u += pu_twin.latest_report.utilization if pu_twin.latest_report is not None else 0
            n_pu += 1
        return total_u / n_pu

    def deltint_extension(self):
        self.manage_hot_standby(logging_overhead(self._clock, self.LOGGING_OVERHEAD))
        self.hold_in(PHASE_PASSIVE, self.next_phase())

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        self.check_new_config()
        res = self.check_pu_reports()
        self.trigger_dispatching(overhead)
        if res:
            self.send_edc_reports()
        self.manage_hot_standby(overhead)
        self.hold_in(PHASE_PASSIVE, self.next_phase())

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.start = True
        self.activate()

    def exit(self):
        pass

    def manage_hot_standby(self, overhead: str):
        if self.dispatcher.explore_hot_standby and self._clock >= self.next_hot_standby:
            instantaneous = self.start
            self.start = False
            self.next_hot_standby = self._clock + self.cool_down
            for job in self.dispatcher.explore_hot_standby_changes(instantaneous):
                pu_id, standby = job.pu_id, job.hot_standby
                logging.info(f"{overhead}{self.name} set PU {pu_id}\'s hot standby mode to {standby}")
                msg = ProcessingUnitHotStandBy(self.edc_id, pu_id, standby, instantaneous)
                self.add_msg_to_queue(self.outputs_hot_standby[pu_id], msg)

    def next_phase(self) -> float:
        hot_standby = max(self.next_hot_standby - self._clock, 0) if self.dispatcher.explore_hot_standby else inf
        others = inf if self.msg_queue_empty() else 0
        return min(hot_standby, others)

    def check_new_config(self):
        if self.input_new_dispatching:
            new_config = self.input_new_dispatching.get()
            self.dispatcher.new_mapper(new_config.function_id, **new_config.function_config)
        if self.input_new_hot_standby:
            new_config = self.input_new_hot_standby.get()
            self.dispatcher.new_hot_standby(new_config.function_id, **new_config.function_config)

    def check_pu_reports(self) -> bool:
        res: bool = False
        if self.input_pu_report:
            for pu_report in self.input_pu_report.values:
                self.dispatcher.update_pu_report(pu_report.pu_id, pu_report)
            res = True
        return res  # self.send_edc_reports()

    def trigger_dispatching(self, overhead):
        self._check_pu_responses(overhead)
        self._check_service_requests(overhead)

    def send_edc_reports(self):
        if self.dispatcher.cooler is not None:
            self.dispatcher.update_cooler()
            self.add_msg_to_queue(self.output_cooler_report, self.dispatcher.cooler.get_cooler_report())

        it_power = self.it_power
        cooling_power = self.cooling_power
        report = EdgeDataCenterReport(self.edc_id, self.edc_location, self.utilization, self.max_sessions, it_power,
                                      cooling_power, self.env_temp, self.ongoing_sessions, self.tasks_progress)
        if self.smart_grid:
            msg = PowerDemandReport(self.edc_id, it_power + cooling_power, report)
            self.add_msg_to_queue(self.output_power_demand, msg)
        else:
            msg = PowerConsumptionReport(self.edc_id, None, None, it_power + cooling_power,
                                         0, False, False, 0, 0, 0, report)
            self.add_msg_to_queue(self.output_power_consumption, msg)

    def _check_pu_responses(self, overhead: str):
        for job in self.input_start_session_response.values:
            logging_f = logging.info if job.response.response else logging.warning
            logging_f(f"{overhead}{self.name} received {job.response.request} response: {job.response.response}")
            self.add_msg_to_queue(self.output_service_response, self.dispatcher.start_response(job))
        for job in self.input_service_response.values:
            logging_f = logging.info if job.response.response else logging.warning
            logging_f(f"{overhead}{self.name} received {job.response.request} response: {job.response.response}")
            self.add_msg_to_queue(self.output_service_response, self.dispatcher.service_response(job))
        for job in self.input_stop_session_response.values:
            logging_f = logging.info if job.response.response else logging.warning
            logging_f(f"{overhead}{self.name} received {job.response.request} response: {job.response.response}")
            self.add_msg_to_queue(self.output_service_response, self.dispatcher.stop_response(job))

    def _check_service_requests(self, overhead: str):
        self._check_start_session_port(overhead)
        self._check_ongoing_session_port(overhead)
        self._check_remove_session_port(overhead)

    def _check_start_session_port(self, overhead: str):
        """Process incoming create service requests"""
        for request in self.input_start_session_request.values:
            logging.info(f"{overhead}{self.name} received {request} request")
            response = self.dispatcher.start_request(request)
            if isinstance(response, ProcessingUnitServiceRequest):
                logging.info(f"{overhead}{self.name} mapped start session request in PU {response.pu_id}")
                self.add_msg_to_queue(self.outputs_start_session_request[response.pu_id], response)
            elif isinstance(response, ServiceResponse):
                logging.warning(f"{overhead}{self.name} got early response to request: {response}")
                self.add_msg_to_queue(self.output_service_response, response)
            else:
                logging.warning(f"{overhead}{self.name} is still waiting for PU's response. Ignoring request")

    def _check_ongoing_session_port(self, overhead: str):
        """Process incoming ongoing session requests"""
        for request in self.input_service_request.values:
            logging.info(f"{overhead}{self.name} received {request} request")
            response = self.dispatcher.service_request(request)
            if isinstance(response, ProcessingUnitServiceRequest):
                logging.info(f"{overhead}{self.name} mapped service request in PU {response.pu_id}")
                self.add_msg_to_queue(self.outputs_service_request[response.pu_id], response)
            elif isinstance(response, ServiceResponse):
                logging.warning(f"{overhead}{self.name} got early response to request: {response}")
                self.add_msg_to_queue(self.output_service_response, response)
            else:
                logging.warning(f"{overhead}{self.name} is still waiting for PU's response. Ignoring request")

    def _check_remove_session_port(self, overhead: str):
        """Process incoming remove service requests"""
        for request in self.input_stop_session_request.values:
            logging.info(f"{overhead}{self.name} received {request} request")
            response = self.dispatcher.stop_request(request)
            if isinstance(response, ProcessingUnitServiceRequest):
                logging.info(f"{overhead}{self.name} mapped stop session request in PU {response.pu_id}")
                self.add_msg_to_queue(self.outputs_stop_session_request[response.pu_id], response)
            elif isinstance(response, ServiceResponse):
                logging.warning(f"{overhead}{self.name} got early response to request: {response}")
                self.add_msg_to_queue(self.output_service_response, response)
            else:
                logging.warning(f"{overhead}{self.name} is still waiting for PU's response. Ignoring request")
