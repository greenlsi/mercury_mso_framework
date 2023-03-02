from __future__ import annotations
from collections import deque
from mercury.config.client import SrvConfig
from mercury.config.transducers import TransducersConfig
from mercury.logger import logger as logging, logging_overhead
from mercury.msg.client import ServiceActive, GatewayConnection, ServiceReport
from mercury.msg.packet.app_packet.srv_packet import *
from mercury.plugin import AbstractFactory, SrvRequestGenerator, SrvActivityGenerator, SrvActivityWindowGenerator
from random import uniform
from xdevs.models import Port
from ....common import ExtendedAtomic


class SrvManager(ExtendedAtomic):
    LOGGING_OVERHEAD: str = ''
    PHASE_INACTIVE: str = 'inactive'
    PHASE_AWAIT_OPEN: str = 'await_open'
    PHASE_ACTIVE: str = 'active'
    PHASE_AWAIT_CLOSE: str = 'await_close'

    def __init__(self, client_id: str, srv_config: SrvConfig,
                 gateway: str | None, t_start: float = 0, t_end: float = inf):
        """
        Basic service manager xDEVS module.
        :param client_id: client ID.
        :param srv_config: service configuration parameters.
        :param gateway: ID of the initial gateway of the client.
        :param t_start: time at which the UE is created.
        :param t_end: time at which the UE is removed.
        """
        self.client_id: str = client_id
        self.service_id: str = srv_config.service_id
        self.srv_config: SrvConfig = srv_config
        super().__init__(f'{self.client_id}_srv_{self.service_id}')
        self._clock = t_start  # We advance current clock to t_start
        self.t_cool_down: float = self._clock
        self.t_window: float = self._clock
        self.t_end: float = t_end

        self.req_buffer: deque[SrvRequest] = deque()
        self.aux_req: SrvRelatedRequest | None = None
        self.sent_req: SrvRelatedRequest | None = None

        self.prev_gateway: str | None = gateway
        self.gateway_id: str | None = gateway
        self.server_id: str | None = None

        self.req_n: int = 0
        self.srv_met_deadlines: int = 0
        self.srv_missed_deadlines: int = 0

        self.sessions: list[tuple[bool, float | None]] = list()
        self.open_sess_met_deadlines: int = 0
        self.open_sess_missed_deadlines: int = 0
        self.close_sess_met_deadlines: int = 0
        self.close_sess_missed_deadlines: int = 0
        self.t_sess: float = 0

        guard_time = uniform(0, ServicesConfig.SRV_MAX_GUARD)
        self.session: bool = self.srv_config.sess_required
        activity_gen_config = {**self.srv_config.activity_gen_config, 't_start': self._clock + guard_time}
        self.activity_generator: SrvActivityGenerator = AbstractFactory.create_srv_activity_generator(
            self.srv_config.activity_gen_id, **activity_gen_config)
        activity_window_config = {**self.srv_config.activity_window_config, 't_start': self._clock + guard_time}
        self.activity_window: SrvActivityWindowGenerator = AbstractFactory.create_srv_activity_window(
            self.srv_config.activity_window_id, **activity_window_config)
        self.req_generator: SrvRequestGenerator | None = None

        self.input_srv: Port[AppPacket] = Port(AppPacket, 'input_srv')
        self.input_gateway: Port[GatewayConnection] = Port(GatewayConnection, 'input_gateway')
        self.output_srv: Port[AppPacket] = Port(AppPacket, 'output_srv')
        self.output_active: Port[ServiceActive] = Port(ServiceActive, 'output_active')
        self.output_report: Port[ServiceReport] = Port(ServiceReport, 'output_report')
        self.add_in_port(self.input_srv)
        self.add_in_port(self.input_gateway)
        self.add_out_port(self.output_srv)
        self.add_out_port(self.output_active)
        self.add_out_port(self.output_report)

    @property
    def ready_to_dump(self) -> bool:
        return self._clock >= self.t_end and self.phase == self.PHASE_INACTIVE and self.sigma == inf

    @property
    def srv_miss_ratio(self) -> float:
        return self.srv_missed_deadlines / (self.srv_missed_deadlines + self.srv_met_deadlines)

    @property
    def open_sess_miss_ratio(self) -> float:
        return self.open_sess_missed_deadlines / (self.open_sess_missed_deadlines + self.open_sess_met_deadlines)

    @property
    def close_sess_miss_ratio(self) -> float:
        return self.close_sess_missed_deadlines / (self.close_sess_missed_deadlines + self.close_sess_met_deadlines)

    def deltint_extension(self):
        self.sigma = inf  # By default, in internal transitions it passivates in its current phase
        self.update_req_buffer()
        if self.phase == self.PHASE_INACTIVE:
            self.deltint_inactive()
        elif self.phase == self.PHASE_AWAIT_OPEN:
            self.deltint_await_open()
        elif self.phase == self.PHASE_ACTIVE:
            self.deltint_active()
        elif self.phase == self.PHASE_AWAIT_CLOSE:
            self.deltint_await_close()
        if not self.msg_queue_empty():
            self.sigma = 0  # If message queue is not empty after the internal transition, it activates in its new phase

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        self.check_connected_ap(overhead)
        if self.phase == self.PHASE_INACTIVE:
            self.continuef(e)
        elif self.phase == self.PHASE_AWAIT_OPEN:
            self.deltext_await_open(e, overhead)
        elif self.phase == self.PHASE_ACTIVE:
            self.deltext_active(e, overhead)
        elif self.phase == self.PHASE_AWAIT_CLOSE:
            self.deltext_await_close(e, overhead)
        if not self.msg_queue_empty():
            self.sigma = 0
        self.prev_gateway = self.gateway_id

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.phase = self.PHASE_INACTIVE
        self.deltint_extension()

    def exit(self):
        pass

    def new_req_generator(self, t_start: float) -> SrvRequestGenerator:
        req_gen_config = {**self.srv_config.req_gen_config, 't_start': t_start}
        return AbstractFactory.create_srv_req_generator(self.srv_config.req_gen_id, **req_gen_config)

    def update_req_buffer(self):
        if self._clock < self.t_window:
            while self.req_generator.next_t <= self._clock:
                req = SrvRequest(self.service_id, self.client_id, self.req_n, self.gateway_id, None, self._clock)
                self.req_n += 1
                self.req_buffer.append(req)
                self.req_generator.advance()
        else:
            self.req_n -= len(self.req_buffer)
            self.req_buffer.clear()
            self.req_generator = None

    def deltint_inactive(self):
        self.phase = self.PHASE_INACTIVE
        self.aux_req = None
        self.sent_req = None
        self.server_id = None
        if self._clock < self.t_end:
            if self._clock < self.activity_generator.next_t:
                self.hold_in(self.PHASE_INACTIVE, min(self.activity_generator.next_t, self.t_end) - self._clock)
            else:
                self.add_msg_to_queue(self.output_active, ServiceActive(self.client_id, self.service_id, True))
                if self.session:
                    self.deltint_await_open()
                else:
                    self.t_window = min(self._clock + self.activity_window._compute_next_ta(), self.t_end)
                    self.req_generator = self.new_req_generator(self._clock)
                    self.update_req_buffer()
                    self.deltint_active()

    def deltint_await_open(self):
        self.phase = self.PHASE_AWAIT_OPEN
        if self._clock < self.t_end:
            if self.gateway_id is None or self.sent_req is not None:  # client disconnected or waiting for a response
                self.hold_in(self.PHASE_AWAIT_OPEN, self.t_end - self._clock)
            else:
                if self.aux_req is None:
                    self.aux_req = OpenSessRequest(self.service_id, self.client_id, len(self.sessions),
                                                   self.gateway_id, None, self._clock)
                if self._clock < self.t_cool_down:  # client needs to cool down
                    self.hold_in(self.PHASE_AWAIT_OPEN, min(self.t_cool_down, self.t_end) - self._clock)
                else:
                    self.sent_req = self.aux_req
                    self.sent_req.send_req(self._clock, self.gateway_id, self.server_id)
                    self.add_msg_to_queue(self.output_srv, self.sent_req)
        elif self.sent_req is None:
            self.add_msg_to_queue(self.output_active, ServiceActive(self.client_id, self.service_id, False))
            self.deltint_inactive()

    def deltint_active(self):
        self.phase = self.PHASE_ACTIVE
        if self._clock < self.t_window:
            if self.sent_req is not None:
                self.hold_in(self.PHASE_ACTIVE, min(self.req_generator.next_t, self.t_window) - self._clock)
            elif not self.req_buffer:
                self.hold_in(self.PHASE_ACTIVE, min(self.req_generator.next_t, self.t_window) - self._clock)
            elif self.gateway_id is not None:
                if self._clock < self.t_cool_down:  # client needs to cool down
                    self.hold_in(self.PHASE_ACTIVE, min(self.t_window, self.t_cool_down) - self._clock)
                else:
                    self.sent_req = self.req_buffer.popleft()
                    self.sent_req.send_req(self._clock, self.gateway_id, self.server_id)
                    self.add_msg_to_queue(self.output_srv, self.sent_req)
            else:
                self.hold_in(self.PHASE_ACTIVE, min(self.req_generator.next_t, self.t_window) - self._clock)
        elif self.sent_req is None:
            if self.session:
                self.deltint_await_close()
            else:
                self.add_msg_to_queue(self.output_active, ServiceActive(self.client_id, self.service_id, False))
                self.deltint_inactive()

    def deltint_await_close(self):
        self.phase = self.PHASE_AWAIT_CLOSE
        if self.gateway_id is not None and self.sent_req is None:  # client ready to send the close session request
            if self.aux_req is None:
                self.aux_req = CloseSessRequest(self.service_id, self.client_id, len(self.sessions) - 1,
                                                self.gateway_id, self.server_id, self._clock)
            if self._clock < self.t_cool_down:  # client needs to cool down
                self.hold_in(self.PHASE_AWAIT_CLOSE, self.t_cool_down - self._clock)
            else:
                self.sent_req = self.aux_req
                self.sent_req.send_req(self._clock, self.gateway_id, self.server_id)
                self.add_msg_to_queue(self.output_srv, self.sent_req)

    def check_connected_ap(self, overhead: str):
        if self.input_gateway:
            self.gateway_id = self.input_gateway.get().gateway_id
            logging.info(f'{overhead}{self.client_id} is now connected to gateway {self.gateway_id}')

    def deltext_await_open(self, e: float, overhead: str):
        for resp in self.input_srv.values:
            if isinstance(resp, OpenSessResponse) and resp.request == self.sent_req:
                resp.receive(self._clock)
                self.sent_req = None
                server_id = resp.response
                log_msg = f'{overhead}{self.client_id} received {resp.request} response: {resp}'
                if server_id is not None:
                    log_function = logging.info
                    if resp.deadline_met:
                        self.open_sess_met_deadlines += 1
                    else:
                        self.open_sess_missed_deadlines += 1
                        log_function = logging.warning
                        log_msg = f'{log_msg} (missed deadline)'
                    self.aux_req = None
                    self.sessions.append((resp.deadline_met, None))
                    self.send_report(resp)
                    self.server_id = server_id
                    log_msg = f'{log_msg}; delay: {resp.t_delay:.3f} seconds; miss ratio: {self.open_sess_miss_ratio:.3f}'
                    if self._clock < self.t_end:
                        self.t_window = min(self._clock + self.activity_window._compute_next_ta(), self.t_end)
                        self.req_generator = self.new_req_generator(self._clock)
                        self.update_req_buffer()
                        log_function(log_msg)
                        self.deltint_active()
                    else:
                        log_function(f'{log_msg}, but client needs to be removed. Closing session...')
                        self.deltint_await_close()
                elif self._clock < self.t_end:
                    logging.warning(f'{log_msg}. Waiting cool down to try again...')
                    self.t_cool_down = self._clock + self.srv_config.cool_down
                    self.deltint_await_open()
                else:
                    logging.info(f'{log_msg}, but client needs to be removed. Moving to phase inactive...')
                    self.add_msg_to_queue(self.output_active, ServiceActive(self.client_id, self.service_id, False))
                    self.deltint_inactive()
                return
        if self.prev_gateway is None and self.gateway_id is not None:
            self.deltint_await_open()
        else:
            self.continuef(e)

    def deltext_active(self, e, overhead):
        for resp in self.input_srv.values:
            if isinstance(resp, SrvResponse) and resp.request == self.sent_req:
                resp.receive(self._clock)
                self.sent_req = None
                request = resp.request
                response = resp.response
                log_function = logging.info
                log_msg = f'{overhead}{self.client_id} received {request} response: {resp}'
                if response:
                    if resp.deadline_met:
                        self.srv_met_deadlines += 1
                    else:
                        log_function = logging.warning
                        log_msg = f'{log_msg} (missed deadline)'
                        self.srv_missed_deadlines += 1
                    self.send_report(resp)
                    log_msg = f'{log_msg}; delay: {resp.t_delay:.3f} seconds; miss ratio: {self.srv_miss_ratio:.3f}'
                else:
                    log_function = logging.warning
                    if self._clock < self.t_window:
                        log_msg = f'{log_msg}. Waiting cool down to try again...'
                        self.req_buffer.appendleft(request)
                        self.t_cool_down = self._clock + self.srv_config.cool_down
                    else:
                        self.req_n -= 1
                        if self.session:
                            log_msg = f'{log_msg}, but request window finished. Closing session...'
                        else:
                            log_msg = f'{log_msg}, but request window finished. Moving to phase inactive...'
                log_function(log_msg)
                self.deltint_active()
                return
        if self.prev_gateway is None and self.gateway_id is not None:
            self.deltint_active()
        else:
            self.continuef(e)

    def deltext_await_close(self, e: float, overhead: str):
        for resp in self.input_srv.values:
            if isinstance(resp, CloseSessResponse) and resp.request == self.sent_req:
                resp.receive(self._clock)
                self.sent_req = None
                request = resp.request
                response = resp.response
                log_msg = f'{overhead}{self.client_id} received {request} response: {resp} seconds'
                if response < 0:
                    logging.warning(f'{log_msg}. Waiting cool down to try again...')
                    self.t_cool_down = self._clock + self.srv_config.cool_down
                    self.deltint_await_close()
                else:
                    log_function = logging.info
                    if resp.deadline_met:
                        self.close_sess_met_deadlines += 1
                    if not resp.deadline_met:
                        self.close_sess_missed_deadlines += 1
                        log_function = logging.warning
                        log_msg = f'{log_msg} (missed deadline)'
                    self.aux_req = None
                    deadline_met, t_sess = self.sessions.pop()
                    assert t_sess is None
                    self.t_sess += response
                    self.sessions.append((deadline_met, response))
                    self.send_report(resp)
                    log_msg = f'{log_msg}; delay: {resp.t_delay:.3f} seconds; miss ratio: {self.close_sess_miss_ratio:.3f}'
                    log_function(log_msg)
                    self.activity_generator.next_activity(self._clock)
                    if self.activity_generator.next_t <= self._clock < self.t_end:
                        self.deltint_await_open()
                    else:
                        self.add_msg_to_queue(self.output_active, ServiceActive(self.client_id, self.service_id, False))
                        self.deltint_inactive()
                return
        if self.prev_gateway is None and self.gateway_id is not None:
            self.deltint_await_close()
        else:
            self.continuef(e)

    def send_report(self, response: SrvRelatedResponse):
        if TransducersConfig.LOG_SRV:
            acc_met_deadlines = -1
            acc_missed_deadlines = -1
            if isinstance(response, OpenSessResponse):
                acc_met_deadlines = self.open_sess_met_deadlines
                acc_missed_deadlines = self.open_sess_missed_deadlines
            elif isinstance(response, SrvResponse):
                acc_met_deadlines = self.srv_met_deadlines
                acc_missed_deadlines = self.srv_missed_deadlines
            elif isinstance(response, CloseSessResponse):
                acc_met_deadlines = self.close_sess_met_deadlines
                acc_missed_deadlines = self.close_sess_missed_deadlines
            rep = ServiceReport(response, acc_met_deadlines, acc_missed_deadlines, len(self.sessions), self.t_sess)
            self.add_msg_to_queue(self.output_report, rep)
