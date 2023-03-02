from __future__ import annotations
from math import exp
from typing import Callable
from .optimizer import Optimizer, OptimizerState


class SimulatedAnnealing(Optimizer):
    def __init__(self, **kwargs):
        """
        Simulated annealing optimizer.

        :param float t_max: maximum (i.e., initial) temperature. It defaults to 100.
        :param float t_min: minimum (i.e., final) temperature. It defaults to 0.
        :param str schedule_type: cooling schedule type. It defaults to "exponential".
        :param float schedule_constant: cooling constant. If exponential, it defaults to 0.99. If linear, it's set to 1.
        :param kwargs: refer to the Optimizer base class for more configuration parameters.
        """
        super().__init__(**kwargs)
        self.t_max: float = kwargs.get('t_max', 100)  # TODO justify default value
        if self.t_max <= 0:
            raise ValueError('t_max > 0')
        self.t_min: float = kwargs.get('t_min', 0)
        if self.t_max < 0:
            raise ValueError('t_min >= 0')
        if self.t_max <= self.t_min:
            raise ValueError('t_max > t_min')
        self.current_t = self.t_max

        schedule_type: str = kwargs.get('schedule_type', 'exponential')
        if schedule_type == 'exponential':
            schedule_constant: float = kwargs.get('schedule_constant', .99)  # TODO justify default value
            if schedule_constant <= 0 or schedule_constant >= 1:
                raise ValueError('0 < schedule_constant < 1')
            self.t_min = max(self.t_min, 1e-6)  # Cannot be zero because otherwise it will never cool down
            self.adjust_temp: Callable[[float], float] = lambda x: x * schedule_constant
        elif schedule_type == 'linear':
            schedule_constant: float = kwargs.get('schedule_constant', 1)  # TODO justify default value
            if schedule_constant <= 0:
                raise ValueError('schedule_constant > 0')
            self.adjust_temp = lambda x: x - schedule_constant
        else:
            raise ValueError('annealing schedule must be either "exponential" or "linear"')

    def reset(self):
        """Resets the variables that are altered on a per-run basis of the algorithm"""
        super().reset()
        self.current_t = self.t_max

    def acceptance_p(self, neighbor: OptimizerState) -> float:
        try:
            return exp(-(neighbor.cost - self.current_state.cost) / self.current_t)
        except OverflowError:
            return 1

    def run_iteration(self, csv_writer) -> str | None:
        super().run_iteration(csv_writer)
        self.current_t = self.adjust_temp(self.current_t)
        if self.current_t < self.t_min:
            return 'REACHED MINIMUM TEMPERATURE'
