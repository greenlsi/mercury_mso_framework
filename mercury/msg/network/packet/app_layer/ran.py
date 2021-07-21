from mercury.config.network import PacketConfig
from typing import Dict, Optional
from ..packet import ApplicationPacket, PacketData


class RANPacket(ApplicationPacket):
    def __init__(self, ap_id: str, ue_id: Optional[str]):
        super().__init__(PacketData(), PacketConfig.RAN_MGMT_HEADER)
        self.ap_id: str = ap_id
        self.ue_id: Optional[str] = ue_id


class RANAccessPacket(RANPacket):
    pass


class ConnectRequest(RANAccessPacket):
    def __init__(self, ue_id: str, ap_id: str):
        super().__init__(ap_id, ue_id)


class DisconnectRequest(RANAccessPacket):
    def __init__(self, ue_id: str, ap_id: str):
        super().__init__(ap_id, ue_id)


class ConnectResponse(RANAccessPacket):
    def __init__(self, ap_id: str, ue_id: str, response: bool):
        super().__init__(ap_id, ue_id)
        self.response: bool = response


class DisconnectResponse(RANAccessPacket):
    def __init__(self, ap_id: str, ue_id: str, response: bool):
        super().__init__(ap_id, ue_id)
        self.response: bool = response


class RadioResourceControl(RANAccessPacket):
    def __init__(self, ue_id: str, ap_id: str, rrc_list: Dict[str, float]):
        super().__init__(ap_id, ue_id)
        self.rrc_list = rrc_list


class RANControlPacket(RANPacket):
    pass


class PrimarySynchronizationSignal(RANAccessPacket):
    def __init__(self, ap_id: str, ue_id: Optional[str] = None):
        super().__init__(ap_id, ue_id)


class RANControlRequest(RANControlPacket):
    pass


class CreatePathRequest(RANControlRequest):
    pass


class RemovePathRequest(RANControlRequest):
    pass


class SwitchPathRequest(RANControlRequest):
    def __init__(self, ap_id: str, ue_id: str, prev_ap_id: str):
        super().__init__(ap_id, ue_id)
        self.prev_ap_id: str = prev_ap_id


class RANControlResponse(RANControlPacket):
    def __init__(self, ap_id, ue_id, response):
        super().__init__(ap_id, ue_id)
        self.response: bool = response


class CreatePathResponse(RANControlResponse):
    pass


class RemovePathResponse(RANControlResponse):
    pass


class SwitchPathResponse(RANControlResponse):
    def __init__(self, ap_id: str, ue_id: str, prev_ap_id: str, response: bool):
        super().__init__(ap_id, ue_id, response)
        self.prev_ap_id: str = prev_ap_id


class RANHandOverPacket(RANPacket):
    def __init__(self, ap_from: str, ap_to: str, ue_id: str):
        super().__init__(ap_from, ue_id)
        self.ap_from = ap_from
        self.ap_to = ap_to


class RANHandOverRequestPacket(RANHandOverPacket):
    pass


class StartHandOverRequest(RANHandOverRequestPacket):
    pass


class HandOverStarted(RANHandOverRequestPacket):
    def __init__(self, ap_from: str, ue_id: str, ap_to: str):
        super().__init__(ap_from, ap_to, ue_id)


class HandOverReady(RANHandOverRequestPacket):
    def __init__(self, ue_id: str, ap_to: str, ap_from: str):
        super().__init__(ap_from, ap_to, ue_id)


class RANHandOverResponsePacket(RANHandOverPacket):
    def __init__(self, ap_from: str, ap_to: str, ue_id: str, response: bool):
        super().__init__(ap_from, ap_to, ue_id)
        self.response: bool = response


class StartHandOverResponse(RANHandOverResponsePacket):
    def __init__(self, ap_to: str, ap_from: str, ue_id: str, response: bool):
        super().__init__(ap_from, ap_to, ue_id, response)


class HandOverFinished(RANHandOverResponsePacket):
    def __init__(self, ap_to: str, ue_id: str, ap_from: str, response: bool):
        super().__init__(ap_from, ap_to, ue_id, response)


class HandOverResponse(RANHandOverResponsePacket):
    def __init__(self, ue_id: str, ap_from: str, ap_to: str, response: bool):
        super().__init__(ap_from, ap_to, ue_id, response)
