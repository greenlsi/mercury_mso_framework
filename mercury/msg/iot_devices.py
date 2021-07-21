from typing import Optional
from .network.packet.app_layer.ran import PrimarySynchronizationSignal


class ServiceDelayReport:
    def __init__(self, ue_id: str, service_id: str, action: str, generated: float, processed: float, times_sent: int):
        self.ue_id: str = ue_id
        self.service_id: str = service_id
        self.action: str = action
        self.generated: float = generated
        self.processed: float = processed
        self.times_sent: int = times_sent

    @property
    def delay(self) -> float:
        return self.processed - self.generated


class ConnectedAccessPoint:
    def __init__(self, ap_id: Optional[str]):
        self.ap_id = ap_id


class ExtendedPSS(PrimarySynchronizationSignal):
    def __init__(self, ap_id: str, snr: Optional[float]):
        super().__init__(ap_id)
        self.snr: Optional[float] = snr


class ServiceRequired:
    def __init__(self, service_id: str, required: bool):
        self.service_id: str = service_id
        self.required: bool = required
