import pandas as pd
from abc import ABC
from math import inf
from typing import Tuple
from ..common.event_generator import EventGenerator, DiracDeltaGenerator, EventHistoryGenerator


class NodeMobility(EventGenerator[Tuple[float, ...]], ABC):
    @property
    def location(self) -> Tuple[float, ...]:
        return self.last_val


class NodeMobilityStill(NodeMobility, DiracDeltaGenerator[Tuple[float, ...]]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.location is not None


class NodeMobility2DFunction(NodeMobility):
    def __init__(self, **kwargs):
        self.function = kwargs.get('function', lambda x: x)
        self.interval = kwargs.get('interval', (0, 0))
        initial_x = kwargs.get('initial_x', 0)
        assert self.interval[0] <= initial_x <= self.interval[1]
        initial_location = (initial_x, self.function(initial_x))
        self.delta = kwargs.get('delta', 0)
        direction = kwargs.get('direction', 1)
        assert direction in [-1, 1]
        self.direction = direction
        sigma = kwargs.get('sigma', inf)
        assert sigma > 0
        self.sigma = sigma
        super().__init__(**kwargs, initial_val=initial_location)

    def _compute_next_val(self) -> Tuple[float, ...]:
        next_x = self.location[0] + self.delta * self.direction
        if not (self.interval[0] < next_x < self.interval[1]):
            next_x = min(max(self.interval[0], next_x), self.interval[1])
            self.direction *= - 1
        return next_x, self.function(next_x)

    def _compute_next_ta(self) -> float:
        return self.sigma


class NodeMobilityHistory(NodeMobility, EventHistoryGenerator[Tuple[float, ...]]):
    def __init__(self, **kwargs):
        self.x_column = kwargs.get('x_column', 'x')
        self.y_column = kwargs.get('y_column', 'y')
        super().__init__(**kwargs)
        for column in (self.x_column, self.y_column):
            if not self.history_buffer.column_exists(column):
                raise ValueError(f"dataframe does not have the mandatory column {column}")

    def _pd_series_to_val(self, series: pd.Series) -> [Tuple[float, ...]]:
        return series[self.x_column].item(), series[self.y_column].item()
