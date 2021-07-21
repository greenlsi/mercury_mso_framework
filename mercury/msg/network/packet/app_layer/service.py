from abc import ABC
from mercury.config.network import PacketConfig
from typing import Optional, Tuple
from ..packet import PacketData, ApplicationPacket


class ServicePacket(ApplicationPacket, ABC):
    def __init__(self, service_id: str, client_id: str, server_id: Optional[str], header_only: bool):
        data: PacketData = PacketData() if header_only else PacketData(PacketConfig.SRV_CONTENTS.get(service_id, 0))
        super().__init__(data, PacketConfig.SRV_HEADERS.get(service_id, 0))
        self.service_id: str = service_id
        self.client_id: str = client_id
        self.server_id: Optional[str] = server_id

    @property
    def ue_id(self) -> str:
        return self.client_id


class GetDataCenterRequest(ServicePacket):
    def __init__(self, service_id: str, client_id: str, ap_id: str):
        super().__init__(service_id, client_id, None, True)
        self.ap_id: str = ap_id


class GetDataCenterResponse(ServicePacket):
    def __init__(self, request: GetDataCenterRequest, response: Optional[str]):
        super().__init__(request.service_id, request.client_id, response, True)
        self.request: GetDataCenterRequest = request

    @property
    def ap_id(self) -> str:
        return self.request.ap_id


class ServiceRequest(ServicePacket):
    def __init__(self, service_id: str, client_id: str, server_id: Optional[str],
                 req_id: int = 0, session: bool = False, header_only: bool = False):
        """
        Service request message.
        :param service_id: identification of the service.
        :param client_id: identification of the client.
        :param server_id: identification of the server. If server is not known, it can be set to None.
        :param req_id: identification number of the request.
        :param session: if true, a session related to the service is already open.
        :param header_only: if true, data packet is empty.
        """
        super().__init__(service_id, client_id, server_id, header_only)
        self.req_id: int = req_id
        self.session: bool = session

    def __str__(self) -> str:
        return f"<{self.service_id},{self.client_id},{self.req_id},{self.session}>"

    @property
    def info(self) -> Tuple[str, str, int]:
        return self.service_id, self.client_id, self.req_id


class StartSessionRequest(ServiceRequest):
    def __init__(self, service_id: str, client_id: str, server_id: Optional[str]):
        """Start service session request message."""
        super().__init__(service_id, client_id, server_id, header_only=True)

    def __str__(self) -> str:
        return f"start {super().__str__()}"


class StopSessionRequest(ServiceRequest):
    def __init__(self, service_id: str, client_id: str, server_id: str):
        """Stop service session request message."""
        super().__init__(service_id, client_id, server_id, session=True, header_only=True)

    def __str__(self) -> str:
        return f"stop {super().__str__()}"


class ServiceResponse(ServicePacket):
    def __init__(self, request: ServiceRequest, response: bool, trace: Optional[str] = None):
        """
        Service response message.
        :param request: service request related to the response.
        :param response: it indicates if the service succeeded.
        :param trace: message providing additional information about the service response.
        """
        super().__init__(request.service_id, request.client_id, request.server_id, True)
        self.request: ServiceRequest = request
        self.response: bool = response
        self.trace: Optional[str] = trace

    def __str__(self) -> str:
        return str(self.response) if self.trace is None else f"{self.response} ({self.trace})"

    @property
    def info(self) -> Tuple[Tuple[str, str, int], bool]:
        return self.request.info, self.response
