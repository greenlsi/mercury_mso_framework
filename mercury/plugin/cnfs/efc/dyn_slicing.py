from typing import Dict, Optional
from abc import ABC, abstractmethod
from mercury.msg.cnfs import EdgeDataCenterSlicing
from mercury.msg.smart_grid import PowerConsumptionReport


class DynamicSlicing(ABC):

    edc_slicing: Dict[str, Dict[str, float]]

    def __init__(self, **kwargs):
        self.edc_slicing = dict()

    def slicing(self, edc_reports: Dict[str, PowerConsumptionReport], offers: Dict[str, Optional[float]],
                demand: Dict[str, Dict[str, Optional[float]]]) -> Dict[str, EdgeDataCenterSlicing]:
        new_slicing = self.assign_slicing(edc_reports, offers, demand)
        res = dict()
        for edc_id, service_slice in new_slicing.items():
            if service_slice != self.edc_slicing[edc_id]:
                self.edc_slicing[edc_id] = service_slice
                res[edc_id] = EdgeDataCenterSlicing(edc_id, service_slice)
        return res

    @abstractmethod
    def assign_slicing(self, edc_reports: Dict[str, PowerConsumptionReport], offers: Dict[str, Optional[float]],
                       demand: Dict[str, Dict[str, Optional[float]]]) -> Dict[str, Dict[str, float]]:
        pass
