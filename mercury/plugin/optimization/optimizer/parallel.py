from __future__ import annotations
import multiprocessing
import os.path
from .optimizer import Optimizer, OptimizerState


class ParallelOptimizer(Optimizer):
    def __init__(self, **kwargs):
        """
        Tabu search optimizer.

        :param int n_candidates: number of candidates evaluated in each iteration. By default, it is set to 1.
        :param bool parallel: if True, it evaluates the candidates in parallel. By default, it is set to True.
        """
        super().__init__(**kwargs)
        self.n_candidates: int = kwargs.get('n_candidates', 1)
        self.parallel: bool = kwargs.get('parallel', True)
        self.manager = multiprocessing.Manager() if self.parallel else None

    @staticmethod
    def cost_and_append(state: OptimizerState, states: list[OptimizerState]):
        _ = state.cost
        states.append(state)

    def new_candidate(self, prev_state: OptimizerState) -> OptimizerState | None:
        # create iteration folder
        iter_dir = os.path.join(self.base_dir, f'iter_{self.n_iter}')
        if os.path.exists(iter_dir):
            raise AssertionError(f'directory {iter_dir} should not exist')
        os.mkdir(iter_dir)
        # create up to n_candidates candidates
        candidates = list()
        for i in range(self.n_candidates):  # as much as n_neighbors
            raw_candidate = self.new_raw_candidate(prev_state.raw_config)
            if raw_candidate is not None:
                candidate_dir = os.path.join(iter_dir, f'candidate_{i}')
                candidate = OptimizerState(self.cost_function, raw_candidate, candidate_dir,
                                           self.interval, self.lite, self.p_type)
                candidates.append(candidate)
        # if candidates list is empty, we return None
        if not candidates:
            return None
        # If parallel, we evaluate the new neighbors using multiprocessing
        if self.parallel:
            scores = self.manager.list()
            jobs = list()
            for candidate in candidates:
                p = multiprocessing.Process(target=ParallelOptimizer.cost_and_append, args=(candidate, scores))
                p.start()
                jobs.append(p)
            for t in jobs:
                t.join()
        # Otherwise, we do it sequentially
        else:
            scores = candidates
        # Return best candidate
        best_candidate = min(scores, key=lambda x: x.cost)
        os.system(f'cp {best_candidate.config_file} {os.path.join(iter_dir, "config.json")}')
        return best_candidate
