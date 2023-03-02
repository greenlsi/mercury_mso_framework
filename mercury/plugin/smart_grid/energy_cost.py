from __future__ import annotations
import pandas as pd
from abc import ABC
from ..common.event_generator import EventGenerator, DiracDeltaGenerator, EventHistoryGenerator


class EnergyCostGenerator(EventGenerator[float], ABC):
    @property
    def next_cost(self) -> float:
        return self.next_val


class ConstantEnergyCostGenerator(EnergyCostGenerator, DiracDeltaGenerator[float]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, initial_val=kwargs['cost'])
        assert self.last_val is not None


class HistoryEnergyCostGenerator(EnergyCostGenerator, EventHistoryGenerator[float]):
    def __init__(self, **kwargs):
        self.cost_column = kwargs.get('cost_column', 'cost')
        super().__init__(**kwargs)
        if not self.history_buffer.column_exists(self.cost_column):
            raise ValueError(f"dataframe does not have the mandatory column {self.cost_column}")

    def _pd_series_to_val(self, series: pd.Series) -> float:
        return series[self.cost_column].item()
