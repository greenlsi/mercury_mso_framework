from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
from mercury.config.edcs import EdgeDataCenterConfig
from mercury.msg.edcs import EdgeDataCenterReport, NewEDCSlicing


class DynamicEDCSlicing(ABC):
    def __init__(self, **kwargs):
        self.edc_config: EdgeDataCenterConfig = kwargs['edc_config']
        self.edc_slicing: dict[str, float] = deepcopy(self.edc_config.r_mngr_config.edc_slicing)

    def new_slicing(self, edc_report: EdgeDataCenterReport, srv_estimation: dict[str, int]) -> NewEDCSlicing | None:
        new_slicing = self.assign_slicing(edc_report, srv_estimation)
        if new_slicing != self.edc_slicing:
            self.edc_slicing = new_slicing
            return NewEDCSlicing(edc_report.edc_id, deepcopy(new_slicing))

    @abstractmethod
    def assign_slicing(self, edc_report: EdgeDataCenterReport, srv_estimation: dict[str, int]) -> dict[str, int]:
        pass


class EstimationSlicing(DynamicEDCSlicing):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_slicing(self, edc_report: EdgeDataCenterReport, srv_estimation: dict[str, int]) -> dict[str, int]:
        return {service_id: slicing for service_id, slicing in srv_estimation.items()}
