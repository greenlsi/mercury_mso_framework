from __future__ import annotations
import pandas as pd
from abc import ABC
from ..common.event_generator import EventGenerator, DiracDeltaGenerator, EventHistoryGenerator


class PowerGenerationGenerator(EventGenerator[float], ABC):
    @property
    def next_power(self) -> float:
        return self.next_val


class ConstantPowerGeneration(PowerGenerationGenerator, DiracDeltaGenerator[float]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, initial_val=kwargs['power'])
        assert self.last_val is not None


class HistoryPowerGeneration(PowerGenerationGenerator, EventHistoryGenerator[float]):
    def __init__(self, **kwargs):
        self.power_column: str = kwargs.get('power_column', 'power')
        super().__init__(**kwargs)
        if not self.history_buffer.column_exists(self.power_column):
            raise ValueError(f"dataframe does not have the mandatory column {self.power_column}")

    def _pd_series_to_val(self, series: pd.Series) -> float:
        return series[self.power_column].item()
