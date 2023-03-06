from __future__ import annotations
import multiprocessing
import os.path
from abc import ABC
from collections import deque
from typing import Any, Deque
from .optimizer import Optimizer, OptimizerState


class TabuSearch(Optimizer, ABC):
    def __init__(self, **kwargs):
        """
        Tabu search optimizer.

        :param int n_neighbors: number of neighbors evaluated in each iteration. By default, it is set to 1.
        :param bool parallel: if True, it evaluates the neighbors in parallel. By default, it is set to False.
        :param int tabu_size: size of the tabu list. By default, it is set to 0 (i.e., no tabu list).
        :param kwargs: refer to the Optimizer base class for more configuration parameters.
        """
        super().__init__(**kwargs)
        self.n_neighbors: int = kwargs.get('n_neighbors', 1)
        self.parallel: bool = kwargs.get('parallel', False)
        tabu_size: int = kwargs.get("tabu_size", 0)
        self.tabu_list: Deque[dict[str, Any]] = deque(maxlen=tabu_size)

    def reset(self):
        super().reset()
        self.tabu_list.clear()

    @staticmethod
    def cost_and_append(state: OptimizerState, states: list[OptimizerState]):
        _ = state.cost
        states.append(state)

    def new_candidate(self, prev_state: OptimizerState) -> OptimizerState | None:
        neighbors = list()
        iter_dir = os.path.join(self.base_dir, f'iter_{self.n_iter}')
        if os.path.exists(iter_dir):
            raise AssertionError(f'directory {iter_dir} should not exist')
        os.mkdir(iter_dir)
        for i in range(self.n_neighbors):  # as much as n_neighbors
            raw_neighbor = self.new_raw_neighbor(prev_state.raw_config)
            if raw_neighbor is None:
                return None
            elif raw_neighbor not in self.tabu_list:
                neighbor_dir = os.path.join(iter_dir, f'neighbor_{i}')
                neighbor = OptimizerState(self.cost_function, raw_neighbor, neighbor_dir,
                                          self.interval, self.lite, self.p_type)
                neighbors.append(neighbor)
        # If parallel, we evaluate the new neighbors using multiprocessing
        if self.parallel and len(neighbors) > 1:
            manager = multiprocessing.Manager()
            scores = manager.list()
            jobs = list()
            for neighbor in neighbors:
                p = multiprocessing.Process(target=TabuSearch.cost_and_append, args=(neighbor, scores))
                p.start()
                jobs.append(p)
            for t in jobs:
                t.join()
        else:
            scores = neighbors
        best_neighbor = min(scores, key=lambda x: x.cost, default=None)
        if best_neighbor is not None:
            os.system(f'cp {best_neighbor.config_file} {os.path.join(iter_dir, "config.json")}')
        return min(scores, key=lambda x: x.cost, default=None)

    def acceptance_p(self, candidate: OptimizerState) -> float:
        """
        Returns the probability to move the current state to a new candidate.
        If candidate is accepted, then it is added to the tabu list.

        :param candidate: a state
        :return: acceptance probability
        """
        if candidate.cost < self.current_state.cost:
            self.tabu_list.append(candidate.raw_config)
            return 1
        return 0
