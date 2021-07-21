import pandas as pd
from abc import ABC, abstractmethod
from math import inf
from mercury.utils.history_buffer import EventHistoryBuffer
from random import expovariate, gauss, uniform
from typing import Callable, Generic, Optional, TypeVar


T = TypeVar('T')


class EventGenerator(ABC, Generic[T]):
    def __init__(self, **kwargs):
        self.last_val: Optional[T] = kwargs.get('initial_val', None)
        self.last_t: float = kwargs.get('t_start', 0)
        self.val_modifier: Callable[[T], T] = kwargs.get('val_modifier', lambda x: x)
        self.next_val: Optional[T] = self.last_val
        self.next_t: float = self.last_t

    @property
    def ta(self) -> float:
        return self.next_t - self.last_t

    def _compute_next_val(self) -> Optional[T]:
        return self.last_val

    @abstractmethod
    def _compute_next_ta(self) -> float:
        pass

    def advance(self):
        self.last_val = self.next_val
        self.last_t = self.next_t
        self.next_val = self._compute_next_val()
        self.next_t += self._compute_next_ta()


class DiracDeltaGenerator(EventGenerator[T], ABC, Generic[T]):
    def _compute_next_ta(self) -> float:
        return inf


class PeriodicGenerator(EventGenerator[T], ABC, Generic[T]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.period: float = kwargs['period']

    def _compute_next_ta(self) -> float:
        return self.period


class UniformDistributionGenerator(EventGenerator[T], ABC, Generic[T]):
    def __init__(self, **kwargs):
        self.lower_bound: float = kwargs['lower_bound']
        if self.lower_bound <= 0:
            raise AssertionError('lower bound must be greater than 0')
        self.upper_bound: float = kwargs.get('upper_bound', self.lower_bound)
        if self.upper_bound < self.lower_bound:
            raise AssertionError('upper bound must be greater than lower bound')
        super().__init__(**kwargs)

    def _compute_next_ta(self) -> float:
        return max(uniform(self.lower_bound, self.upper_bound), 0)


class GaussianDistributionGenerator(EventGenerator[T], ABC, Generic[T]):
    def __init__(self, **kwargs):
        self.mean: float = kwargs['mean']
        if self.mean <= 0:
            raise AssertionError('mean period must be greater than 0')
        self.std_deviation: float = kwargs.get('std_deviation', 0)
        if self.std_deviation < 0:
            raise AssertionError('standard deviation must be greater than 0')
        super().__init__(**kwargs)

    def _compute_next_ta(self) -> float:
        return max(gauss(self.mean, self.std_deviation), 0)


class ExponentialDistributionGenerator(EventGenerator[T], ABC, Generic[T]):
    def __init__(self, **kwargs):
        self.mean: float = kwargs['mean']
        if self.mean <= 0:
            raise AssertionError('mean period must be greater than 0')
        self.lambd: float = 1 / self.mean
        super().__init__(**kwargs)

    def _compute_next_ta(self) -> float:
        return expovariate(self.lambd)


class LambdaDrivenGenerator(EventGenerator[T], ABC, Generic[T]):
    def __init__(self, **kwargs):
        self.lambd: Callable[[], float] = kwargs['lambd']
        super().__init__(**kwargs)

    def _compute_next_ta(self) -> float:
        return max(self.lambd(), 0)


class EventHistoryGenerator(EventGenerator[T], ABC, Generic[T]):
    def __init__(self, **kwargs):
        self.history_buffer = EventHistoryBuffer(**kwargs)
        super().__init__(**kwargs, initial_val=self._pd_series_to_val(self.history_buffer.initial_val))

    def _compute_next_val(self) -> Optional[T]:
        return self._pd_series_to_val(self.history_buffer.get_event())

    def _compute_next_ta(self) -> float:
        res: float = self.history_buffer.time_of_next_event() - self.next_t
        self.history_buffer.advance()
        return res

    @abstractmethod
    def _pd_series_to_val(self, series: pd.Series) -> T:
        pass
