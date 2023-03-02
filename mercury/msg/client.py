from __future__ import annotations
from .packet.app_packet.srv_packet import SrvRelatedResponse


class SendPSS:
    def __init__(self, client_id: str, best_gw: str | None):
        self.client_id: str = client_id
        self.best_gw: str | None = best_gw


class GatewayConnection:
    def __init__(self, client_id: str, gateway_id: str | None):
        self.client_id: str = client_id
        self.gateway_id: str | None = gateway_id


class ServiceActive:
    def __init__(self, client_id: str, service_id: str, active: bool):
        self.client_id: str = client_id
        self.service_id: str = service_id
        self.active: bool = active


class ServiceReport:
    def __init__(self, response: SrvRelatedResponse, acc_met_deadlines: int,
                 acc_missed_deadlines: int, n_sess: int, t_sess: float):
        self.response: SrvRelatedResponse = response
        self.req_type: str = type(response.request).__name__
        self.acc_met_deadlines: int = acc_met_deadlines
        self.acc_missed_deadlines: int = acc_missed_deadlines
        self.n_sess: int = n_sess
        self.t_sess: float = t_sess

    @property
    def client_id(self) -> str:
        return self.response.request.client_id

    @property
    def service_id(self) -> str:
        return self.response.request.service_id

    @property
    def req_n(self) -> int:
        return self.response.request.req_n

    @property
    def t_req_gen(self) -> float:
        return self.response.request.t_gen

    @property
    def t_res_rcv(self) -> float:
        return self.response.t_rcv[-1]

    @property
    def t_delay(self) -> float:
        return self.response.t_delay

    @property
    def deadline_met(self) -> bool:
        return self.response.deadline_met
