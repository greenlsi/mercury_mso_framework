from __future__ import annotations
from mercury.logger import logger as logging, logging_overhead
from mercury.config.cloud import CloudConfig, CloudServiceConfig
from mercury.msg.packet.app_packet.srv_packet import *
from xdevs.models import Port
from ..common import ExtendedAtomic


class CloudPool(ExtendedAtomic):

    LOGGING_OVERHEAD: str = '                '

    def __init__(self, cloud_config: CloudConfig):
        super().__init__(f'{cloud_config.cloud_id}_pool')

        self.cloud_id: str = cloud_config.cloud_id
        self.srv_config: dict[str, CloudServiceConfig] = cloud_config.srv_config
        self.sessions: dict[tuple[str, str], float] = dict()
        self.requests: dict[tuple[str, str], SrvRequest] = dict()
        self.timeline: dict[float, list[tuple[str, str]]] = dict()

        self.input_requests: Port[AppPacket] = Port(AppPacket, 'in_requests')
        self.output_responses: Port[SrvRelatedResponse] = Port(SrvRelatedResponse, 'out_responses')
        self.add_in_port(self.input_requests)
        self.add_out_port(self.output_responses)

    def deltint_extension(self):
        overhead = logging_overhead(self._clock, CloudPool.LOGGING_OVERHEAD)
        for (client_id, service_id) in self.timeline.pop(self._clock, list()):
            request = self.requests.pop((client_id, service_id))
            self.send_response(overhead, SrvResponse(request, True, self._clock))
        self.sigma = self.next_sigma()

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, CloudPool.LOGGING_OVERHEAD)
        for msg in self.input_requests.values:
            msg.receive(self._clock)
            if isinstance(msg, OpenSessRequest):
                response = self.open_session(msg)
            elif isinstance(msg, SrvRequest):
                response = self.process_srv_request(msg)
            elif isinstance(msg, CloseSessRequest):
                response = self.close_session(msg)
            else:
                raise ValueError('Invalid message type!')
            if response is not None:
                self.send_response(overhead, response)
        self.sigma = self.next_sigma()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.sigma = self.next_sigma()

    def exit(self):
        pass

    def open_session(self, request: OpenSessRequest) -> OpenSessResponse:
        client_id: str = request.client_id
        service_id: str = request.service_id
        srv_config = self.srv_config.get(service_id)
        if srv_config is None:
            return OpenSessResponse(request, None, self._clock, 'Cloud does not support this service')
        elif (service_id, client_id) in self.sessions:
            return OpenSessResponse(request, self.cloud_id, self._clock, 'Service session is already opened')
        self.sessions[(service_id, client_id)] = self._clock
        return OpenSessResponse(request, self.cloud_id, self._clock)

    def process_srv_request(self, request: SrvRequest) -> SrvResponse | None:
        client_id: str = request.client_id
        service_id: str = request.service_id
        srv_config = self.srv_config.get(service_id)
        if srv_config is None:
            return SrvResponse(request, False, self._clock, 'Cloud does not support this service')
        if srv_config.sess_required and (service_id, client_id) not in self.sessions:
            return SrvResponse(request, False, self._clock, 'Bad cloud mapping: required session does not exist')
        if (service_id, client_id) not in self.requests:
            proc_t = srv_config.proc_t_model.proc_time() + self._clock
            if proc_t not in self.timeline:
                self.timeline[proc_t] = list()
            self.timeline[proc_t].append((service_id, client_id))
            self.requests[(service_id, client_id)] = request
        elif self.requests[(service_id, client_id)] != request:
            return SrvResponse(request, False, self._clock, 'Cloud is busy with a different request of the same client')

    def close_session(self, request: CloseSessRequest) -> CloseSessResponse:
        client_id: str = request.client_id
        service_id: str = request.service_id
        if (service_id, client_id) not in self.sessions:
            return CloseSessResponse(request, 0, self._clock, 'Service session does not exist')
        elif (service_id, client_id) in self.requests:
            return CloseSessResponse(request, -1, self._clock, 'Service session is busy and cannot be closed')
        t_open = self.sessions.pop((service_id, client_id))
        return CloseSessResponse(request, self._clock - t_open, self._clock)

    def send_response(self, overhead: str, response: SrvRelatedResponse):
        response.send(self._clock)
        self.add_msg_to_queue(self.output_responses, response)
        logging.info(f'{overhead}{self.cloud_id} response: {response}')

    def next_sigma(self):
        return min(self.timeline, default=inf) - self._clock if self.msg_queue_empty() else 0
