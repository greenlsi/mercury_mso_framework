from __future__ import annotations
from math import exp
from .optimizer import Optimizer, OptimizerState


class StochasticHillClimbing(Optimizer):
    def __init__(self, **kwargs):
        """
        Stochastic hill climbing optimizer.

        :param float temp: temperature for computing the acceptance probability. It defaults to 0.01.
        :param kwargs: refer to the Optimizer base class for more configuration parameters.
        """
        self.temp: float = kwargs.get('temp', .01)  # TODO justify default value
        super().__init__(**kwargs)

    def acceptance_p(self, candidate: OptimizerState) -> float:
        try:
            return 1 / (1 + exp((candidate.cost - self.current_state.cost) / self.temp))
        except OverflowError:
            return 1
