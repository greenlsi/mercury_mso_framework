import pandas as pd
from abc import ABC
from ..common.event_generator import EventGenerator, DiracDeltaGenerator, EventHistoryGenerator


class DemandEstimationGenerator(EventGenerator[float], ABC):
    pass


class DemandEstimationGeneratorStatic(DemandEstimationGenerator, DiracDeltaGenerator[float]):
    pass


class DemandEstimationGeneratorHistory(DemandEstimationGenerator, EventHistoryGenerator[float]):
    def __init__(self, **kwargs):
        self.estimation_column = kwargs.get('estimation_column', 'estimation')
        super().__init__(**kwargs)
        if not self.history_buffer.column_exists(self.estimation_column):
            raise ValueError(f"dataframe does not have the mandatory column {self.estimation_column}")

    def _pd_series_to_val(self, series: pd.Series) -> float:
        return series[self.estimation_column].item()
