from collections import deque
from typing import Deque, Dict, Optional
from xdevs.models import Port, INFINITY
from mercury.config.core import CoreConfig
from mercury.config.iot_devices import ServiceConfig
from mercury.logger import logger as logging, logging_overhead
from mercury.msg.network import NetworkPacket
from mercury.msg.iot_devices import ServiceRequired, ConnectedAccessPoint, ServiceDelayReport
from mercury.msg.network.packet.app_layer.service import ServiceRequest, StartSessionRequest, \
    StopSessionRequest, ServiceResponse, GetDataCenterRequest, GetDataCenterResponse
from mercury.plugin import ServiceRequestProfile, AbstractFactory
from ...common import ExtendedAtomic


class RequestStruct:
    def __init__(self, data: ServiceRequest, initial_clock: float):
        self.data: ServiceRequest = data
        self.initial_clock: float = initial_clock
        self.acknowledged: bool = False
        self.times_sent: int = 0
        self.first_time_sent: float = initial_clock
        self.next_timeout: float = initial_clock


class Service(ExtendedAtomic):

    PHASE_SESSION_CLOSED: str = "session_closed"
    PHASE_AWAIT_SERVER: str = "await_server"
    PHASE_AWAIT_START_SESSION: str = "await_start_session"
    PHASE_SESSION_STARTED: str = "session_started"
    PHASE_AWAIT_STOP_SESSION: str = "await_stop_session"

    LOGGING_OVERHEAD: str = ""

    def __init__(self, ue_id: str, srv_config: ServiceConfig, guard_time: float = 0,
                 t_start: float = 0, t_end: float = INFINITY, lite: bool = False):
        """
        Service Session Manager xDEVS module.
        :param ue_id: User Equipment ID.
        :param srv_config: service configuration.
        :param guard_time: guard time to wait before starting the execution cycle.
        :param t_start: time at which the UE is created.
        :param t_end: time at which the UE is removed.
        :param lite: True if Mercury Lite is selected.
        """
        super().__init__(f"iot_devices_{ue_id}_{srv_config.service_id}")
        self._clock = t_start  # We advance current clock to t_start
        self.t_end: float = t_end

        self.ue_id: str = ue_id
        self.service_id: str = srv_config.service_id
        self.srv_config: ServiceConfig = srv_config

        self.session_profile = AbstractFactory.create_srv_session_profile(srv_config.session_profile_name,
                                                                          **srv_config.session_profile_config,
                                                                          t_start=t_start + guard_time)
        self.session_duration = AbstractFactory.create_srv_session_duration(srv_config.session_duration_name,
                                                                            **srv_config.session_duration_config,
                                                                            t_start=t_start + guard_time)

        self.request_generator: Optional[ServiceRequestProfile] = None
        self.req_label: int = 0
        self.data_buffer: Deque[RequestStruct] = deque()
        self.awaiting_requests: Dict[ServiceRequest, RequestStruct] = dict()

        self.connected_ap: Optional[str] = CoreConfig.CORE_ID if lite else None
        self.prev_ap: Optional[str] = CoreConfig.CORE_ID if lite else None
        self.server_id: Optional[str] = None

        self.times_sent: int = 0
        self.first_time_sent: float = 0
        self.next_timeout: float = self._clock

        self.input_connected_ap = Port(ConnectedAccessPoint, 'input_connected_ap')
        self.input_network = Port(NetworkPacket, 'input_network')
        self.output_network = Port(NetworkPacket, 'output_network')
        self.output_service_delay_report = Port(ServiceDelayReport, 'output_service_delay_report')
        self.output_service_required = Port(ServiceRequired, 'output_service_required')

        self.add_in_port(self.input_connected_ap)
        self.add_in_port(self.input_network)
        self.add_out_port(self.output_network)
        self.add_out_port(self.output_service_delay_report)
        self.add_out_port(self.output_service_required)

    def deltint_extension(self):
        if self.phase == self.PHASE_SESSION_CLOSED:
            self.deltint_session_closed()
        elif self.phase == self.PHASE_AWAIT_SERVER:
            self.deltint_await_server()
        elif self.phase == self.PHASE_AWAIT_START_SESSION:
            self.deltint_await_start_session()
        elif self.phase == self.PHASE_SESSION_STARTED:
            if self._clock >= self.next_timeout:
                self.data_buffer.clear()
            self.deltint_session_started()
        elif self.phase == self.PHASE_AWAIT_STOP_SESSION:
            self.deltint_await_stop_session()

    def deltint_session_closed(self):
        if self.session_profile.next_t >= self.t_end:    # UE must be removed
            self.passivate(self.PHASE_SESSION_CLOSED)
        elif self.session_profile.next_t > self._clock:  # UE must wait cool-down before starting a new session
            self.hold_in(self.PHASE_SESSION_CLOSED, self.session_profile.next_t - self._clock)
        else:                                            # UE can start a new session
            self.add_msg_to_queue(self.output_service_required, ServiceRequired(self.service_id, True))
            self.times_sent = 1
            self.first_time_sent = self._clock
            self.next_timeout = min(self._clock + self.srv_config.session_timeout, self.t_end)
            self.activate(self.PHASE_AWAIT_SERVER)

    def deltint_await_server(self):
        if self._clock >= self.t_end:             # if UE must be removed
            self.add_msg_to_queue(self.output_service_required, ServiceRequired(self.service_id, False))
            self.activate(self.PHASE_SESSION_CLOSED)
        elif self.connected_ap is None:           # UE is not connected to the RAN. We should keep waiting
            self.hold_in(self.PHASE_AWAIT_SERVER, self.t_end - self._clock)
        else:
            if self._clock >= self.next_timeout:  # Timeout has been triggered
                self.times_sent += 1
                self.next_timeout = min(self._clock + self.srv_config.session_timeout, self.t_end)
            self.hold_in(self.PHASE_AWAIT_SERVER, self.next_timeout - self._clock)

    def deltint_await_start_session(self):
        if self.connected_ap is None:             # UE is not connected to the RAN. We should keep waiting
            self.passivate(self.PHASE_AWAIT_START_SESSION)
        else:
            if self._clock >= self.next_timeout:  # Timeout has been triggered
                self.times_sent += 1
                self.next_timeout = self._clock + self.srv_config.session_timeout
            self.hold_in(self.PHASE_AWAIT_START_SESSION, self.next_timeout - self._clock)

    def deltint_session_started(self):
        self._add_request_to_buffer()
        if not (self.data_buffer or self.awaiting_requests):  # no data is to be sent yet
            n_event = min(self.request_generator.next_t, self.next_timeout)
            if self._clock < n_event:                         # wait cool-down period before stopping current session
                self.hold_in(self.PHASE_SESSION_STARTED, n_event - self._clock)
            else:                                             # proceed to stop current session
                self.times_sent = 1
                self.first_time_sent = self._clock
                self.next_timeout = self._clock + self.srv_config.session_timeout
                self.activate(self.PHASE_AWAIT_STOP_SESSION)
        elif self.connected_ap is None:                       # UE not connected to RAN. Wait to create a new packet
            n_event = self.request_generator.next_t if self.request_generator.next_t < self.next_timeout else INFINITY
            self.hold_in(self.PHASE_SESSION_STARTED, n_event - self._clock)
        else:
            overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
            self._resend_timedout_requests(overhead)
            self._send_requests(overhead)
            if self.msg_queue_empty():
                n_event = min(msg.next_timeout for msg in self.awaiting_requests.values())
                if self.request_generator.next_t < self.next_timeout and self.request_generator.next_t < n_event:
                    n_event = self.request_generator.next_t
                self.hold_in(self.PHASE_SESSION_STARTED, max(n_event - self._clock, 0))
            else:
                self.activate(self.PHASE_SESSION_STARTED)

    def deltint_await_stop_session(self):
        if self.connected_ap is None:
            self.passivate(self.PHASE_AWAIT_STOP_SESSION)
        else:
            if self._clock >= self.next_timeout:
                self.times_sent += 1
                self.next_timeout = self._clock + self.srv_config.session_timeout
            self.hold_in(self.PHASE_AWAIT_STOP_SESSION, self.next_timeout - self._clock)

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        if self.input_connected_ap:
            self.connected_ap = self.input_connected_ap.get().ap_id
            logging.info(f"{overhead}{self.ue_id} handed over from AP {self.prev_ap} to {self.connected_ap}")

        if self.phase == self.PHASE_SESSION_CLOSED:
            self.deltext_session_closed(e, overhead)
        elif self.phase == self.PHASE_AWAIT_SERVER:
            self.deltext_await_server(e, overhead)
        elif self.phase == self.PHASE_AWAIT_START_SESSION:
            self.deltext_await_start_session(e, overhead)
        elif self.phase == self.PHASE_SESSION_STARTED:
            self.deltext_session_started(e, overhead)
        elif self.phase == self.PHASE_AWAIT_STOP_SESSION:
            self.deltext_await_stop_session(e, overhead)

        self.prev_ap = self.connected_ap

    def deltext_session_closed(self, e: float, overhead: str):
        self.passivate(self.PHASE_SESSION_CLOSED) if self.session_profile.next_t >= self.t_end else self.continuef(e)

    def deltext_await_server(self, e: float, overhead: str):
        if self.prev_ap != self.connected_ap:  # If we changed AP, we request again to the new AP and ignore messages
            self.times_sent += 1
            self.next_timeout = self._clock + self.srv_config.session_timeout
            self.activate(self.PHASE_AWAIT_SERVER)
        else:
            for job in self.input_network.values:
                node_from, msg = job.expanse_packet()
                if isinstance(msg, GetDataCenterResponse):
                    self.server_id = msg.server_id
                    logging_msg = f"{overhead}{self.ue_id} {self.service_id} to be processed at {self.server_id}"
                    if self.server_id is not None:
                        logging.info(logging_msg)
                        report = ServiceDelayReport(self.ue_id, self.service_id, 'get_server',
                                                    self.first_time_sent, self._clock, self.times_sent)
                        self.add_msg_to_queue(self.output_service_delay_report, report)
                        self.times_sent = 1
                        self.first_time_sent = self._clock
                        self.next_timeout = self._clock + self.srv_config.session_timeout
                        self.activate(self.PHASE_AWAIT_START_SESSION)
                    else:
                        logging.warning(f"{logging_msg}. Waiting timeout to try again...")
                        self.continuef(e)
                    return
            self.continuef(e)

    def deltext_await_start_session(self, e: float, overhead: str):
        response = False
        for job in self.input_network.values:
            node_from, msg = job.expanse_packet()
            if isinstance(msg, ServiceResponse) and isinstance(msg.request, StartSessionRequest):
                response = msg.response
                logging_msg = f"{overhead}{self.ue_id} received {msg.request} request response: {response}"
                if response:
                    logging.info(logging_msg)
                    report = ServiceDelayReport(self.ue_id, self.service_id, 'start_session',
                                                self.first_time_sent, self._clock, self.times_sent)
                    self.add_msg_to_queue(self.output_service_delay_report, report)
                    self._create_request_generator()
                    self._add_request_to_buffer()
                    self._send_requests(overhead)
                    self.next_timeout = min(self._clock + self.session_duration._compute_next_ta(), self.t_end)
                    self.activate(self.PHASE_SESSION_STARTED)
                else:
                    logging.warning(f"{logging_msg}. Waiting timeout to try again...")
                break
        if not response:
            if self.prev_ap != self.connected_ap:
                self.next_timeout = self._clock + self.srv_config.session_timeout
                self.activate(self.PHASE_AWAIT_START_SESSION)
            else:
                self.continuef(e)

    def deltext_session_started(self, e: float, overhead: str):
        self._process_responses(overhead)
        self._send_requests(overhead)
        if not self.msg_queue_empty():
            self.activate(self.PHASE_SESSION_STARTED)
        else:
            next_event = min(self.request_generator.next_t, self.next_timeout)
            if not (self.data_buffer or self.awaiting_requests):
                ta = next_event - self._clock
                if ta > 0:    # wait cool-down period before stopping current session
                    self.hold_in(self.PHASE_SESSION_STARTED, ta)
                else:
                    self.next_timeout = self._clock + self.srv_config.session_timeout
                    self.times_sent = 1
                    self.first_time_sent = self._clock
                    self.activate(self.PHASE_AWAIT_STOP_SESSION)
            else:
                next_event = min(next_event, min(msg.next_timeout for msg in self.awaiting_requests.values()))
                self.hold_in(self.PHASE_SESSION_STARTED, max(next_event - self._clock, 0))

    def deltext_await_stop_session(self, e: float, overhead: str):
        response = False
        for job in self.input_network.values:
            node_from, msg = job.expanse_packet()
            if isinstance(msg, ServiceResponse) and isinstance(msg.request, StopSessionRequest):
                response = msg.response
                logging_msg = f"{overhead}{self.ue_id} received {msg.request} request response: {response}"
                if response:
                    logging.info(logging_msg)
                    self.server_id = None
                    report = ServiceDelayReport(self.ue_id, self.service_id, 'stop_session',
                                                self.first_time_sent, self._clock, self.times_sent)
                    self.add_msg_to_queue(self.output_service_delay_report, report)
                    self.add_msg_to_queue(self.output_service_required, ServiceRequired(self.service_id, False))
                    self.session_profile.next_session(self._clock)
                    self.activate(self.PHASE_SESSION_CLOSED)
                else:
                    logging.warning(f"{logging_msg}. Waiting timeout to try again...")
                break
        if not response:
            if self.prev_ap != self.connected_ap:
                self.next_timeout = self._clock + self.srv_config.session_timeout
                self.activate(self.PHASE_AWAIT_STOP_SESSION)
            else:
                self.continuef(e)

    def lambdaf_extension(self):
        clock = self._clock + self.sigma
        overhead = logging_overhead(clock, self.LOGGING_OVERHEAD)
        if self.connected_ap is not None:
            log_function = logging.info
            log_msg = f"{overhead}{self.ue_id}"
            if self.phase == self.PHASE_AWAIT_SERVER:
                if clock >= self.next_timeout:
                    log_function = logging.warning
                    log_msg = f"{log_msg} (request timed out)"
                app_msg = GetDataCenterRequest(self.service_id, self.ue_id, self.connected_ap)
                self.output_network.add(NetworkPacket(self.ue_id, CoreConfig.CORE_ID, app_msg))
                log_function(f"{log_msg}: sending get server request for service {self.service_id}")
            elif self.phase == self.PHASE_AWAIT_START_SESSION:
                if clock >= self.next_timeout:
                    log_function = logging.warning
                    log_msg = f"{log_msg} (request timed out)"
                app_msg = StartSessionRequest(self.service_id, self.ue_id, self.server_id)
                self.output_network.add(NetworkPacket(self.ue_id, self.server_id, app_msg))
                log_function(f"{log_msg}: sending {app_msg} request")
            elif self.phase == self.PHASE_AWAIT_STOP_SESSION:
                if clock >= self.next_timeout:
                    log_function = logging.warning
                    log_msg = f"{log_msg} (request timed out)"
                app_msg = StopSessionRequest(self.service_id, self.ue_id, self.server_id)
                self.output_network.add(NetworkPacket(self.ue_id, self.server_id, app_msg))
                log_function(f"{log_msg}: sending {app_msg} request")

    def initialize(self):
        """Schedule first session"""
        if self.session_profile.next_t < self.t_end:
            self.hold_in(self.PHASE_SESSION_CLOSED, self.session_profile.next_t - self._clock)
        else:
            self.passivate(self.PHASE_SESSION_CLOSED)

    def exit(self):
        pass

    def _add_request_to_buffer(self):
        if self._clock < self.next_timeout:
            while self.request_generator.next_t <= self._clock:
                data = ServiceRequest(self.service_id, self.ue_id, self.server_id, self.req_label, True)
                self.req_label += 1
                self.data_buffer.append(RequestStruct(data, self._clock))
                self.request_generator.advance()

    def _resend_timedout_requests(self, overhead: str):
        for msg in self.awaiting_requests.values():
            if (not msg.acknowledged) and msg.next_timeout <= self._clock:
                logging.warning(f"{overhead}{self.ue_id} experienced a timeout for request {msg.data}. Trying again...")
                msg.next_timeout = self._clock + self.srv_config.req_timeout
                msg.times_sent += 1
                self.add_msg_to_queue(self.output_network, NetworkPacket(self.ue_id, self.server_id, msg.data))

    def _send_requests(self, overhead: str):
        while self.data_buffer and (len(self.awaiting_requests) < self.srv_config.max_batches):
            job = self.data_buffer.popleft()
            logging.info(f"{overhead}{self.ue_id} sending {job.data} request")
            job.first_time_sent = self._clock
            job.next_timeout = self._clock + self.srv_config.req_timeout
            job.times_sent = 1
            self.awaiting_requests[job.data] = job
            self.add_msg_to_queue(self.output_network, NetworkPacket(self.ue_id, self.server_id, job.data))

    def _process_responses(self, overhead: str):
        for job in self.input_network.values:
            node_from, msg = job.expanse_packet()
            if isinstance(msg, ServiceResponse) and msg.request in self.awaiting_requests:
                request = msg.request
                response = msg.response
                logging_msg = f"{overhead}{self.ue_id} received request {request} response {response}"
                if response:
                    struct = self.awaiting_requests.pop(request)
                    struct.acknowledged = True
                    instant_generated = struct.initial_clock
                    instant_received = self._clock
                    times_sent = struct.times_sent
                    logging.info(f"{logging_msg}. Perceived delay: {instant_received - instant_generated:.3f} seconds")
                    delay_report = ServiceDelayReport(self.ue_id, self.service_id, 'srv_request',
                                                      instant_generated, instant_received, times_sent)
                    self.add_msg_to_queue(self.output_service_delay_report, delay_report)
                else:
                    logging.warning(f"{logging_msg}. Waiting for timeout to try again...")

    def _create_request_generator(self):
        self.req_label = 0
        self.request_generator = AbstractFactory.create_srv_request_profile(self.srv_config.req_profile_name,
                                                                            **self.srv_config.req_profile_config,
                                                                            t_start=self._clock)
