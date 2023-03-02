from __future__ import annotations
from typing import Any, ClassVar
from .network import StaticNodeConfig, TransceiverConfig


class CoreConfig:
    CORE_ID: ClassVar[str] = 'core'

    def __init__(self, location: tuple[float, ...] = (0, 0), trx: TransceiverConfig | None = None,
                 sdnc_id: str = 'closest', sdnc_config: dict[str, Any] | None = None):
        self.location: tuple[float, ...] = location
        self.xh_node: StaticNodeConfig = StaticNodeConfig(CoreConfig.CORE_ID, location, trx)
        self.sdnc_id: str = sdnc_id
        self.sdnc_config: dict[str, Any] = dict() if sdnc_config is None else sdnc_config
