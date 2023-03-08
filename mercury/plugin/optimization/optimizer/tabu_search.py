from __future__ import annotations
from collections import deque
from typing import Any, Deque
from .optimizer import OptimizerState
from .parallel import ParallelOptimizer


class TabuSearch(ParallelOptimizer):
    def __init__(self, **kwargs):
        """
        Tabu search optimizer.

        :param int tabu_size: size of the tabu list. By default, it is set to 0 (i.e., no tabu list).
        :param kwargs: refer to the ParallelOptimizer base class for more configuration parameters.
        """
        super().__init__(**kwargs)
        tabu_size: int = kwargs.get("tabu_size", 0)
        if tabu_size < 0:
            raise ValueError('tabu_size must be greater than or equal to 0')
        self.tabu_list: Deque[dict[str, Any]] = deque(maxlen=tabu_size)

    def reset(self):
        super().reset()
        self.tabu_list.clear()

    def new_raw_candidate(self, prev_raw_state: dict[str, Any]) -> dict[str, Any] | None:
        raw_candidate = super().new_raw_candidate(prev_raw_state)
        if raw_candidate is None or raw_candidate in self.tabu_list:  # check that candidate is not in tabu list!
            return None
        return raw_candidate

    def acceptance_p(self, candidate: OptimizerState) -> float:
        """
        Returns the probability to move the current state to a new candidate.
        If candidate is accepted, then it is added to the tabu list.

        :param candidate: a state
        :return: acceptance probability
        """
        if candidate.cost < self.current_state.cost:
            self.tabu_list.append(candidate.raw_config)  # If we accept it, we append it to the tabu list
            return 1
        return 0
