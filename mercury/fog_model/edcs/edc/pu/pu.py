from mercury.logger import logger as logging, logging_overhead
from collections import defaultdict
from mercury.config.edcs import ProcessingUnitConfig
from mercury.msg.edcs import ProcessingUnitHotStandBy, ProcessingUnitServiceRequest, \
    ProcessingUnitServiceResponse, ProcessingUnitReport
from mercury.msg.network.packet.app_layer.service import ServiceRequest, StartSessionRequest, StopSessionRequest
from typing import DefaultDict, Dict, Optional, Set, Tuple
from xdevs.models import Port, INFINITY
from .pu_scheduler import ProcessingUnitScheduler
from ....common import ExtendedAtomic


class ProcessingUnit(ExtendedAtomic):

    PHASE_OFF = 'off'
    PHASE_ON = 'on'
    PHASE_TO_ON = 'to_on'
    PHASE_TO_OFF = 'to_off'
    LOGGING_OVERHEAD = '                '

    def __init__(self, edc_id: str, pu_id: str, pu_config: ProcessingUnitConfig, env_temp: float = 298):
        """
        Processing unit model for xDEVS.
        :param edc_id: ID of the EDC that contains the PU.
        :param pu_id: ID of the processing unit.
        :param pu_config: Processing Unit Configuration.
        :param env_temp: Processing unit base temperature (in Kelvin).
        """
        from mercury.plugin import AbstractFactory, ProcessingUnitPowerModel, ProcessingUnitTemperatureModel

        self.next_phase_change: float = INFINITY
        self.pu_config: ProcessingUnitConfig = pu_config
        self.env_temp: float = env_temp

        self.scheduler: ProcessingUnitScheduler = ProcessingUnitScheduler(pu_config)
        self.power_model: Optional[ProcessingUnitPowerModel] = None
        power_model_name = pu_config.power_name
        power_model_config = pu_config.power_config
        if power_model_name is not None:
            self.power_model = AbstractFactory.create_edc_pu_pwr(power_model_name, **power_model_config)

        self.temp_model: Optional[ProcessingUnitTemperatureModel] = None
        temp_model_name = pu_config.temp_name
        temp_model_config = pu_config.temp_config
        if temp_model_name is not None:
            self.temp_model = AbstractFactory.create_edc_pu_temp(temp_model_name, **temp_model_config)

        # Set status attributes
        self.edc_id: str = edc_id  # ID of the EDC that contains the processing unit
        self.pu_id: str = pu_id    # ID of the PU
        self.hot_standby: bool = False
        self.instantaneous: bool = False
        self.resource_share: DefaultDict[str, Dict[ServiceRequest, Tuple[float, float]]] = defaultdict(lambda: dict())

        name = f"edge_fed_{edc_id}_{pu_id}"
        super().__init__(name)

        # I/O ports
        self.input_hot_standby = Port(ProcessingUnitHotStandBy, 'input_hot_standby')
        self.input_start_session_request = Port(ProcessingUnitServiceRequest, 'input_start_session_request')
        self.input_service_request = Port(ProcessingUnitServiceRequest, 'input_service_request')
        self.input_stop_session_request = Port(ProcessingUnitServiceRequest, 'input_stop_session_request')

        self.output_start_session_response = Port(ProcessingUnitServiceResponse, 'output_start_session_response')
        self.output_service_response = Port(ProcessingUnitServiceResponse, 'output_service_response')
        self.output_stop_session_response = Port(ProcessingUnitServiceResponse, 'output_stop_session_response')
        self.output_pu_report = Port(ProcessingUnitReport, 'output_pu_report')

        self.add_in_port(self.input_hot_standby)
        self.add_in_port(self.input_start_session_request)
        self.add_in_port(self.input_service_request)
        self.add_in_port(self.input_stop_session_request)

        self.add_out_port(self.output_start_session_response)
        self.add_out_port(self.output_service_response)
        self.add_out_port(self.output_stop_session_response)
        self.add_out_port(self.output_pu_report)

    def dvfs_index(self, status: bool, u: float) -> float:
        return 0 if not status else min(i for i in self.pu_config.dvfs_table if i >= u)

    def power(self, status: bool, u: float, dvfs_index: float) -> float:
        if self.power_model is not None:
            return self.power_model.compute_power(status, u, self.pu_config.dvfs_table.get(dvfs_index, None))
        return 0

    def temperature(self, status: bool, u: float, dvfs_index: float) -> float:
        if self.temp_model is not None:
            return self.temp_model.compute_temperature(status, u, self.pu_config.dvfs_table.get(dvfs_index, None))
        return self.env_temp

    @property
    def status(self) -> bool:
        return self.phase != ProcessingUnit.PHASE_OFF

    @property
    def pending_service_requests(self) -> bool:
        return any((self.input_start_session_request, self.input_service_request, self.input_stop_session_request))

    def deltint_extension(self):
        if self.next_phase_change == self._clock:
            self.next_phase_change = INFINITY
            if self.phase == ProcessingUnit.PHASE_TO_ON:
                self.phase = ProcessingUnit.PHASE_ON
                self.start_execution()
            else:
                self.phase = ProcessingUnit.PHASE_OFF
            self.add_msg_to_queue(self.output_pu_report, self.get_pu_report(self.status))  # TODO
        else:
            # We only wake up the scheduler if PU is on and the scheduler's next event coincides with the clock
            if self.scheduler.next_t == self._clock:
                self.stop_execution()
                self.start_execution()
                self.deduce_next_state()
                self.add_msg_to_queue(self.output_pu_report, self.get_pu_report(self.status))  # TODO
            else:
                self.deduce_next_state()
        self.sigma = self.next_timeout()

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, ProcessingUnit.LOGGING_OVERHEAD)
        self.process_hot_standby_requests(overhead)
        if self.pending_service_requests:
            self.stop_execution()
            self.process_new_service_requests(overhead)
            self.start_execution()
            self.deduce_next_state()
            self.add_msg_to_queue(self.output_pu_report, self.get_pu_report(self.status))  # TODO
        else:
            self.deduce_next_state()
        self.sigma = self.next_timeout()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.add_msg_to_queue(self.output_pu_report, self.get_pu_report(False))
        self.hold_in(ProcessingUnit.PHASE_OFF, 0)

    def exit(self):
        pass

    def stop_execution(self):
        if self.phase == ProcessingUnit.PHASE_ON:
            for responses, port in zip(self.scheduler.stop_execution(self._clock), (self.output_start_session_response,
                                                                                    self.output_service_response,
                                                                                    self.output_stop_session_response)):
                for response in responses:
                    self.add_msg_to_queue(port, ProcessingUnitServiceResponse(self.edc_id, self.pu_id, response))
            self.resource_share = defaultdict(lambda: dict())

    def start_execution(self):
        if self.phase == ProcessingUnit.PHASE_ON:
            for request, stats in self.scheduler.start_execution(self._clock).items():
                self.resource_share[request.service_id][request] = stats

    def deduce_next_state(self):  # TODO revisar
        if self.phase == ProcessingUnit.PHASE_OFF:
            if self.hot_standby or self.scheduler.busy:
                self.phase = ProcessingUnit.PHASE_TO_ON
                ta = self.pu_config.t_on
                if self.instantaneous:  # If instantaneous, switching on does not take any time (only valid once)
                    ta = 0
                    self.instantaneous = False
                self.next_phase_change = self._clock + ta
        elif self.phase == ProcessingUnit.PHASE_ON:
            if not self.hot_standby and not self.scheduler.busy:
                self.phase = ProcessingUnit.PHASE_TO_OFF
                ta = self.pu_config.t_off
                if self.instantaneous:  # If instantaneous, switching off does not take any time (only valid once)
                    ta = 0
                    self.instantaneous = False
                self.next_phase_change = self._clock + ta

    def process_hot_standby_requests(self, overhead: str):
        if self.input_hot_standby:
            msg = self.input_hot_standby.get()
            hot_standby = msg.hot_standby
            instantaneous = msg.instantaneous
            if hot_standby != self.hot_standby:
                logging.info(f"{overhead}{self.name} received new hot standby mode {hot_standby}")
                self.hot_standby = hot_standby
                self.instantaneous = instantaneous

    def process_new_service_requests(self, overhead: str):
        self._check_start_session_requests(overhead)
        self._check_stop_session_requests(overhead)
        self._check_task_requests(overhead)

    def next_timeout(self):
        if not self.msg_queue_empty():
            return 0
        next_event = min(self.scheduler.next_t, self.next_phase_change)
        return next_event - self._clock

    def _check_start_session_requests(self, overhead: str):
        for job in self.input_start_session_request.values:
            request = job.request
            if not isinstance(request, StartSessionRequest):
                raise AssertionError('PU received wrong message type')
            logging.info(f"{overhead}{self.name} received {request} request")
            response = self.scheduler.start_session(request, self._clock)
            if response is not None:
                logging.warning(f"{overhead}{self.name} got early response to request: {response}")
                msg = ProcessingUnitServiceResponse(self.edc_id, self.pu_id, response)
                self.add_msg_to_queue(self.output_start_session_response, msg)

    def _check_stop_session_requests(self, overhead: str):
        for job in self.input_stop_session_request.values:
            request = job.request
            if not isinstance(request, StopSessionRequest):
                raise AssertionError('PU received wrong message type')
            logging.info(f"{overhead}{self.name} received {request} request")
            response = self.scheduler.stop_session(request, self._clock)
            if response is not None:
                logging.warning(f"{overhead}{self.name} got early response to request: {response}")
                msg = ProcessingUnitServiceResponse(self.edc_id, self.pu_id, response)
                self.add_msg_to_queue(self.output_stop_session_response, msg)

    def _check_task_requests(self, overhead: str):
        for job in self.input_service_request.values:
            request = job.request
            logging.info(f"{overhead}{self.name} received {request} request")
            response = self.scheduler.execute_task(request, self._clock)
            if response is not None:
                logging.warning(f"{overhead}{self.name} got early response to request: {response}")
                msg = ProcessingUnitServiceResponse(self.edc_id, self.pu_id, response)
                self.add_msg_to_queue(self.output_service_response, msg)

    def get_pu_report(self, status: bool) -> ProcessingUnitReport:  # TODO try to pre-compute this when needed
        starting_sessions: DefaultDict[str, Set[str]] = defaultdict(lambda: set())
        started_sessions: DefaultDict[str, Set[str]] = defaultdict(lambda: set())
        removing_sessions: DefaultDict[str, Set[str]] = defaultdict(lambda: set())
        for report, sessions in zip((starting_sessions, started_sessions, removing_sessions),
                                    (self.scheduler.ready_to_start_sessions, self.scheduler.ready_session_requests,
                                     self.scheduler.ready_to_stop_sessions)):
            for service_id, client_id in sessions:
                report[service_id].add(client_id)
        utilization = self.scheduler.last_u
        dvfs_index = self.dvfs_index(status, utilization)
        power = self.power(status, utilization, dvfs_index)
        temperature = self.temperature(status, utilization, dvfs_index)
        return ProcessingUnitReport(self.edc_id, self.pu_id, self.pu_config.pu_type,
                                    status, dvfs_index, utilization, self.scheduler.last_u, power, temperature,
                                    starting_sessions, started_sessions, removing_sessions, self.resource_share)
