from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
from mercury.config.edcs import EdgeDataCenterConfig
from mercury.msg.edcs import EdgeDataCenterReport, NewEDCMapping
from typing import Any


class DynamicEDCMapping(ABC):
    def __init__(self, **kwargs):
        self.edc_config: EdgeDataCenterConfig = kwargs['edc_config']
        self.mapping_id: str = self.edc_config.r_mngr_config.mapping_id
        self.mapping_config: dict[str, Any] = deepcopy(self.edc_config.r_mngr_config.mapping_config)

    def new_mapping(self, edc_report: EdgeDataCenterReport, srv_estimation: dict[str, int]) -> NewEDCMapping | None:
        new_mapping_id, new_mapping_config = self.assign_mapping(edc_report, srv_estimation)
        if new_mapping_id != self.mapping_id or new_mapping_config != self.mapping_config:
            self.mapping_id, self.mapping_config = new_mapping_id, new_mapping_config
            return NewEDCMapping(edc_report.edc_id, new_mapping_id, deepcopy(new_mapping_config))

    @abstractmethod
    def assign_mapping(self, edc_report: EdgeDataCenterReport,
                       srv_estimation: dict[str, int]) -> tuple[str, dict[str, Any]]:
        pass
