from __future__ import annotations
from abc import ABC
from mercury.config.packet import PacketConfig
from .app_packet import AppPacket


class AccessPacket(AppPacket, ABC):
    def __init__(self, node_from: str, node_to: str, t_gen: float):
        super().__init__(node_from, node_to, 0, PacketConfig.RAN_HEADER, t_gen)
        self.snr: float | None = None


class PSSMessage(AccessPacket):
    def __init__(self, gateway_id: str, client_id: str | None, t_gen: float):
        super().__init__(gateway_id, client_id, t_gen)

    @property
    def gateway_id(self) -> str:
        return self.node_from

    @property
    def client_id(self) -> str:
        return self.node_to


class RRCMessage(AccessPacket):
    def __init__(self, client_id: str, gateway_id: str, perceived_snr: dict[str, float], t_gen: float):
        super().__init__(client_id, gateway_id, t_gen)
        self.perceived_snr: dict[str, float] = perceived_snr

    @property
    def client_id(self) -> str:
        return self.node_from

    @property
    def gateway_id(self) -> str:
        return self.node_to


class AccessRequest(AccessPacket, ABC):  # TODO cambiar response a string del gateway al que está (o no) conectado
    def __init__(self, client_id: str, gateway_id: str, t_gen: float):
        super().__init__(client_id, gateway_id, t_gen)

    @property
    def client_id(self) -> str:
        return self.node_from

    @property
    def gateway_id(self) -> str:
        return self.node_to


class ConnectRequest(AccessRequest):
    pass


class DisconnectRequest(AccessRequest):
    pass


class AccessResponse(AccessPacket, ABC):
    def __init__(self, request: AccessRequest, response: bool, t_gen: float):
        super().__init__(request.node_to, request.node_from, t_gen)
        self.request: AccessRequest = request
        self.response: bool = response

    @property
    def gateway_id(self) -> str:
        return self.node_from

    @property
    def client_id(self) -> str:
        return self.node_to


class ConnectResponse(AccessResponse):
    request: ConnectRequest


class DisconnectResponse(AccessResponse):
    request: DisconnectRequest


class HandOverData:
    def __init__(self, client_id: str, gateway_from: str, gateway_to: str):
        self.client_id: str = client_id
        self.gateway_from: str = gateway_from
        self.gateway_to: str = gateway_to


class HandOverPacket(AccessPacket, ABC):
    def __init__(self, node_from: str, node_to: str, ho_data: HandOverData, t_gen: float):
        super().__init__(node_from, node_to, t_gen)
        self.ho_data: HandOverData = ho_data

    @property
    def gateway_from(self) -> str:
        return self.ho_data.gateway_from

    @property
    def gateway_to(self) -> str:
        return self.ho_data.gateway_to

    @property
    def client_id(self) -> str:
        return self.ho_data.client_id


class StartHandOver(HandOverPacket):
    def __init__(self, ho_data: HandOverData, t_gen: float):
        super().__init__(ho_data.gateway_from, ho_data.client_id, ho_data, t_gen)


class HandOverRequest(HandOverPacket):
    def __init__(self, ho_data: HandOverData, t_gen: float):
        super().__init__(ho_data.client_id, ho_data.gateway_to, ho_data, t_gen)


class HandOverResponse(HandOverPacket):
    def __init__(self, request: HandOverRequest, response: bool, t_gen: float):
        super().__init__(request.gateway_to, request.client_id, request.ho_data, t_gen)
        self.request: HandOverRequest = request
        self.response: bool = response


class HandOverFinished(HandOverPacket):
    def __init__(self, response: HandOverResponse, t_gen: float):
        super().__init__(response.client_id, response.gateway_from, response.ho_data, t_gen)
        self.response: bool = response.response
