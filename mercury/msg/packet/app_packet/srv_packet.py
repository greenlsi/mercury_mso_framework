from __future__ import annotations
from abc import ABC, abstractmethod
from math import inf
from mercury.config.client import ServicesConfig
from mercury.config.packet import PacketConfig
from typing import Any
from .app_packet import AppPacket


class SrvPacket(AppPacket, ABC):
    def __init__(self, node_from: str, node_to: str | None, service_id: str, client_id: str,
                 gateway_id: str, server_id: str | None, data: int, t_gen: float):
        """
        Service-related application layer message.
        :param node_from: ID of the sender node.
        :param node_to: ID of the receiver node.
        :param service_id: ID of the service.
        :param client_id: ID of the service client.
        :param gateway_id: ID of the client's gateway
        :param server_id: ID of the server. If None, it is unknown yet.
        :param data: size (in bits) of the content of the message.
        :param t_gen: time (in seconds) at which the packet was generated.
        """
        super().__init__(node_from, node_to, data, PacketConfig.SRV_PACKET_HEADERS[service_id], t_gen)
        self.service_id: str = service_id
        self.client_id: str = client_id
        self.gateway_id: str = gateway_id
        self.server_id: str | None = server_id


class SrvRelatedRequest(SrvPacket, ABC):
    def __init__(self, service_id: str, client_id: str, req_n: int,
                 gateway_id: str, server_id: str | None, data: int, t_gen: float):
        node_to: str = gateway_id if server_id is None else server_id
        super().__init__(client_id, node_to, service_id, client_id, gateway_id, server_id, data, t_gen)
        self.req_n: int = req_n

    def __str__(self) -> str:
        return f'request <{self.service_id},{self.client_id},{self.req_n}>'

    @property
    def info(self) -> tuple[str, str, int]:
        return self.service_id, self.client_id, self.req_n

    @property
    def sess_required(self) -> bool:
        return ServicesConfig.SERVICES[self.service_id].sess_required

    @property
    def t_deadline(self) -> float | None:
        """ Returns the time at which the deadline of this request expires. """
        return self.t_rcv[0] + self.req_deadline if self.t_rcv else None

    @property
    @abstractmethod
    def req_deadline(self) -> float:
        pass

    def set_gateway(self, gateway_id: str):
        if self.server_id is None:
            self.node_to = gateway_id
        self.gateway_id = gateway_id

    def set_node_to(self, node_to: str):
        self.node_to = node_to

    def set_server(self, server_id: str | None):
        if server_id is not None:
            self.node_to = server_id
        self.server_id = server_id

    def send_req(self, t: float, gateway_id: str, server_id: str | None):
        self.set_gateway(gateway_id)
        self.set_server(server_id)
        self.send(t)


class SrvRequest(SrvRelatedRequest):
    def __init__(self, service_id: str, client_id: str, req_n: int, gateway_id: str, server_id: str | None, t_gen: float):
        data = PacketConfig.SRV_PACKET_SRV_REQ[service_id]
        super().__init__(service_id, client_id, req_n, gateway_id, server_id, data, t_gen)
        self.process: SrvRequestProcess | None = None

    @property
    def req_deadline(self) -> float:
        return ServicesConfig.SERVICES[self.service_id].t_deadline

    def create_process(self, t_arrived: float):
        if self.process is None:
            self.process = SrvRequestProcess(self, t_arrived)


class OpenSessRequest(SrvRelatedRequest):
    def __init__(self, service_id: str, client_id: str, req_n: int,
                 gateway_id: str, server_id: str | None, t_gen: float):
        data = PacketConfig.SRV_PACKET_OPEN_REQ[service_id]
        super().__init__(service_id, client_id, req_n, gateway_id, server_id, data, t_gen)

    def __str__(self) -> str:
        return f'open session {super().__str__()}'

    @property
    def req_deadline(self) -> float:
        return ServicesConfig.SERVICES[self.service_id].sess_config.t_deadline


class CloseSessRequest(SrvRelatedRequest):
    def __init__(self, service_id: str, client_id: str, req_n: int,
                 gateway_id: str, server_id: str | None, t_gen: float):
        data = PacketConfig.SRV_PACKET_CLOSE_REQ[service_id]
        super().__init__(service_id, client_id, req_n, gateway_id, server_id, data, t_gen)

    def __str__(self) -> str:
        return f'close session {super().__str__()}'

    @property
    def req_deadline(self) -> float:
        return inf


class SrvRelatedResponse(SrvPacket, ABC):
    def __init__(self, req: SrvRelatedRequest, response: Any, data: int, t_gen: float, trace: str | None = None):
        """
        Response to a service-related request.
        :param req: service-related request.
        :param response: response to the request.
        :param data: size (in bits) of the content of the response message.
        :param t_gen: time (in seconds) at which the response was generated (and sent).
        :param trace: optional trace with additional information about the response.
        """
        node_from = req.gateway_id if req.server_id is None else req.server_id
        super().__init__(node_from, req.client_id, req.service_id, req.client_id,
                         req.gateway_id, req.server_id, data, t_gen)
        self.request: SrvRelatedRequest = req
        self.response = response
        self.trace: str | None = trace
        self.send(t_gen)  # responses are not queued: they are sent immediately

    def __str__(self) -> str:
        return f'{self.request}: {self.response}' if self.trace is None else f'{self.request}: {self.response} ({self.trace})'

    @property
    def info(self) -> tuple[tuple[str, str, int], Any]:
        return self.request.info, self.response

    @property
    def t_round_trip(self) -> float | None:
        """ Returns the round-trip time (i.e., it does not consider queuing nor processing time) """
        return None if not self.t_rcv else self.t_trip + self.request.t_trip

    @property
    def t_processing(self) -> float | None:
        """ Returns the processing time (i.e., the time needed by the server to process the request) """
        return self.t_sent[0] - self.request.t_rcv[-1]

    @property
    def t_delay(self) -> float | None:
        """ Returns the total delay (i.e. queueing time + processing time + round-trip time """
        return None if not self.t_rcv else self.t_rcv[-1] - self.request.t_sent[0]

    @property
    def deadline_met(self) -> bool:
        """ It returns whether or not the service request deadline was met. """
        return self.response and self.t_sent[-1] <= self.request.t_deadline

    @property
    @abstractmethod
    def successful(self) -> bool:
        pass


class SrvResponse(SrvRelatedResponse):
    response: bool
    request: SrvRequest

    def __init__(self, req: SrvRequest, response: bool, t_gen: float, trace: str | None = None):
        """The response indicates if the service request was successfully processed."""
        data = 0 if not response else PacketConfig.SRV_PACKET_SRV_RES[req.service_id]
        super().__init__(req, response, data, t_gen, trace)

    @property
    def successful(self) -> bool:
        return self.response


class OpenSessResponse(SrvRelatedResponse):
    response: str | None
    request: OpenSessRequest

    def __init__(self, req: OpenSessRequest, response: str | None, t_gen: float, trace: str | None = None):
        """The response indicates the ID of server that opened the session. If None, the session failed to open."""
        data = 0 if not response else PacketConfig.SRV_PACKET_OPEN_RES[req.service_id]
        super().__init__(req, response, data, t_gen, trace)

    @property
    def successful(self) -> bool:
        return self.response is not None


class CloseSessResponse(SrvRelatedResponse):
    response: float
    request: CloseSessRequest

    def __init__(self, req: CloseSessRequest, response: float, t_gen: float, trace: str | None = None):
        """
        The response indicates the time (in seconds) in which the closed session remained open.
        If less than 0, the session failed to close
        """
        data = 0 if not response else PacketConfig.SRV_PACKET_CLOSE_RES[req.service_id]
        super().__init__(req, response, data, t_gen, trace)

    @property
    def successful(self) -> bool:
        return self.response >= 0


class SrvRequestProcess:
    def __init__(self, request: SrvRequest, t_arrived: float):
        """
        Service task process structure.
        :param request: service request being processed.
        :param t_arrived: time at which the EDC received the request.
        """
        self.request: SrvRequest = request
        self.t_arrived: float = t_arrived
        self.t_last: float = t_arrived
        self.t_operation: float | None = None
        self.t_finish: float = inf
        self.t_burst: float = 0
        self.progress: float = 0

    def __lt__(self, other):
        """ Processes of PU are sorted in a First-Come-First-Served basis"""
        return self.t_arrived < other.t_arrived

    @property
    def service_id(self) -> str:
        return self.request.service_id

    @property
    def client_id(self) -> str:
        return self.request.client_id

    @property
    def t_deadline(self) -> float:
        return self.request.t_deadline

    @property
    def req_deadline(self) -> float:
        return self.request.req_deadline

    @property
    def info(self) -> tuple[tuple[str, str, int], float]:
        """returns service request information and progress bar"""
        return self.request.info, self.progress

    @property
    def finished(self) -> bool:
        """Returns whether or not the process has been completed"""
        return self.progress >= 1

    @property
    def running(self) -> bool:
        """Returns whether or not the process is running"""
        return self.t_operation is not None

    def start(self, t: float, t_operation: float) -> float:
        """
        Starts running a process of PU.
        :param t: current time.
        :param t_operation: total operation time required for the PU to complete the process.
        :return: time needed for the process to finish if it is not stopped.
        """
        if self.stop(t) >= 1:
            return 0
        ta = t_operation * (1 - self.progress)
        self.t_last = t
        self.t_operation = t_operation
        self.t_finish = t + ta
        return ta

    def stop(self, t: float) -> float:
        """
        Stops running a process of PU.
        :param t: current time.
        :return: progress of the process.
        """
        t_elapsed = t - self.t_last
        if t_elapsed < 0:
            raise AssertionError('new time is previous to last time')
        if self.running:
            if t >= self.t_finish:
                self.progress = 1
            else:
                delta = 1 if self.t_operation <= 0 else t_elapsed / self.t_operation
                self.progress = min(self.progress + delta, 1)
            self.t_last = t
            self.t_operation = None
            self.t_finish = inf
            self.t_burst += t_elapsed
        return self.progress
