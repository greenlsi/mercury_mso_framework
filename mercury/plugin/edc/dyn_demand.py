from __future__ import annotations
import pandas as pd
from abc import ABC, abstractmethod
from math import inf, ceil
from mercury.msg.edcs import EdgeDataCenterReport
from ..common.event_generator import EventGenerator, DiracDeltaGenerator, EventHistoryGenerator


class SrvDemandEstimator(ABC):
    def __init__(self, **kwargs):
        self.service_id: str = kwargs['service_id']

    @abstractmethod
    def get_next_t(self) -> float:
        pass

    @abstractmethod
    def estimation(self, t: float, edc_report: EdgeDataCenterReport | None) -> int:
        pass


class EventSrvDemandEstimator(SrvDemandEstimator, EventGenerator[float], ABC):
    def __init__(self, **kwargs):
        SrvDemandEstimator.__init__(self, service_id=kwargs['service_id'])
        EventGenerator.__init__(self, **kwargs)

    def get_next_t(self) -> float:
        return self.next_t

    def estimation(self, t: float, edc_report: EdgeDataCenterReport | None) -> int:
        while self.next_t <= t < inf:
            self.advance()
        return ceil(self.last_val)


class ConstantSrvDemandEstimator(EventSrvDemandEstimator, DiracDeltaGenerator[float]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, initial_val=kwargs.get('demand', 0))


class HistorySrvDemandEstimator(EventSrvDemandEstimator, EventHistoryGenerator[float]):
    def __init__(self, **kwargs):
        self.demand_column: str = kwargs.get('demand_column', 'demand')
        EventSrvDemandEstimator.__init__(self, **kwargs)
        EventHistoryGenerator.__init__(self, **kwargs)
        if not self.history_buffer.column_exists(self.demand_column):
            raise ValueError(f'dataframe does not have the mandatory column {self.demand_column}')

    def _pd_series_to_val(self, series: pd.Series) -> float:
        return series[self.demand_column].item()


class HybridSrvDemandEstimator(HistorySrvDemandEstimator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.margin: float = kwargs.get('margin', 0)

    def estimation(self, t: float, edc_report: EdgeDataCenterReport | None) -> int:
        res = super().estimation(t, edc_report)
        if edc_report is not None and edc_report.edc_profile is not None \
                and self.service_id in edc_report.edc_profile.profiles:
            res = max(res, edc_report.edc_profile.profiles[self.service_id].n_clients)
        return max(ceil(res * (1 + self.margin)), 0)
