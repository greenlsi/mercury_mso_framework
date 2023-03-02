from __future__ import annotations
from abc import ABC, abstractmethod
from random import gauss


class ProcessingUnitProcTimeModel(ABC):
    def __init__(self, **kwargs):
        """
        Processing unit processing time model.
        :param int max_parallel_tasks: maximum number of tasks that the processing unit can execute in parallel.
        :param kwargs: any additional configuration parameter.
        """
        self.max_parallel_tasks: int = kwargs['max_parallel_tasks']

    def utilization(self, n_tasks: int) -> float:
        """:return: the utilization factor of the processing unit."""
        return min(n_tasks / self.max_parallel_tasks, 1)

    def proc_time(self, n_tasks: int) -> float:
        """
        Compute processing time depending on the number of tasks running concurrently.
        :param n_tasks: number of active tasks.
        :return: power consumption (in Watts) of the processing unit.
        """
        if n_tasks < 1 or n_tasks > self.max_parallel_tasks:
            raise ValueError("Invalid number of tasks being executed by PU")
        return self._proc_time(n_tasks)

    @abstractmethod
    def _proc_time(self, n_tasks: int) -> float:
        """
        Compute processing time depending on the number of tasks running concurrently.
        :param n_tasks: number of active tasks.
        :return: power consumption (in Watts) of the processing unit.
        """
        pass

    @property
    def expected_proc_time(self) -> float:
        return self._proc_time(1)  # TODO -> supongo que todo se ejecuta secuencialmente


class ConstantProcTimeModel(ProcessingUnitProcTimeModel):
    def __init__(self, **kwargs):
        """
        Constant processing time model for processing unit.
        :param float | list[float] proc_t: processing time (in s) of processing unit. By default, it is set to 0.
                                           If float, proc_t must be greater than or equal to 0.
                                           If list, the length of proc_t must be equal to max_parallel_tasks.
                                           If list, all the elements of proc_t must be greater than or equal to 0.
                                           If list, proc_t[i] must be greater than or equal to proc_t[i - 1].
        """
        super().__init__(**kwargs)
        self.proc_t: float | list[float] = kwargs.get('proc_t', 0)
        if isinstance(self.proc_t, list):
            if len(self.proc_t) != self.max_parallel_tasks:
                raise ValueError(f"Length of proc_t ({len(self.proc_t)}) does not match with max_parallel_tasks ({self.max_parallel_tasks})")
            for i, t in enumerate(self.proc_t):
                if t < 0:
                    raise ValueError(f'proc_time for {i + 1} tasks ({t}) must be greater than or equal to 0')
                if i > 0 and self.proc_t[i - 1] > t:
                    raise ValueError(f'proc_time for {i + 1} tasks ({t}) is less than proc_time for {i} tasks ({self.proc_t[i - 1]})')
        elif self.proc_t < 0:
            raise ValueError(f'proc_t ({self.proc_t}) must be greater than or equal to 0')

    def _proc_time(self, n_tasks: int) -> float:
        return self.proc_t[n_tasks - 1] if isinstance(self.proc_t, list) else self.proc_t


class RoundRobinProcTimeModel(ProcessingUnitProcTimeModel):
    def __init__(self, **kwargs):
        """
        Round-robin processing time model. It emulates an even computing time-sharing between the active tasks.
        :param float proc_t: processing time (in seconds) for a single task. By default, it is set to 0.
                             Ideally, the processing time to process n tasks in round-robin is proc_t * n
                             proc_t must be greater than or equal to 0.
        :param float switch_penalty: task switch penalty. It increments the processing time for more than one task.
                                     T(n_tasks) = proc_t * n_tasks * (1 + switch_penalty).
                                     Switch penalty is only applied if n_tasks is greater than 1.
                                     switch_penalty must be greater than or equal to min_power.
        """
        super().__init__(**kwargs)
        self.proc_t: float = kwargs.get('proc_t', 0)
        if self.proc_t < 0:
            raise ValueError(f'proc_t ({self.proc_t}) must be greater than or equal to 0')
        self.switch_penalty: float = kwargs.get('switch_penalty', 0)
        if self.switch_penalty < 0:
            raise ValueError(f'switch_penalty ({self.switch_penalty}) must be greater than or equal to 0')

    def _proc_time(self, n_tasks: int) -> float:
        return self.proc_t if n_tasks == 1 else self.proc_t * n_tasks * (1 + self.switch_penalty)


class GaussianProcTimeModel(ProcessingUnitProcTimeModel):
    def __init__(self, **kwargs):
        """
        Constant processing time model for processing unit.
        :param float | list[float] mu: mean processing time (in s) of processing unit. By default, it is set to 0.
                                       If float, mu must be greater than or equal to 0.
                                       If list, the length of mu must be equal to max_parallel_tasks.
                                       If list, all the elements of mu must be greater than or equal to 0.
                                       If list, mu[i] must be greater than or equal to mu[i - 1].
        :param float | list[float] sigma: standard deviation (in s) of processing time. By default, it is set to 0.
                                          If float, sigma must be greater than or equal to 0.
                                          If list, the length of sigma must be equal to max_parallel_tasks.
                                          If list, all the elements of sigma must be greater than or equal to 0.
        :param float z_score: Z score to be applied when computing the minimum and maximum processing time.
                              By default, z_score is set to 2 (i.e., it contains 95.5% of all values).
                              z_score must be greater than or equal to 0.
        """
        super().__init__(**kwargs)

        self.mu: float | list[float] = kwargs.get('mu', 0)
        if isinstance(self.mu, list):
            if len(self.mu) != self.max_parallel_tasks:
                raise ValueError(f"Length of mu ({len(self.mu)}) does not match with max_parallel_tasks ({self.max_parallel_tasks})")
            for i, t in enumerate(self.mu):
                if t < 0:
                    raise ValueError(f'mu for {i} tasks ({t}) must be greater than or equal to 0')
                if i > 0 and self.mu[i - 1] > t:
                    raise ValueError(f'mu for {i} tasks ({t}) is less than mu for {i - 1} tasks ({self.mu[i - 1]})')
        elif self.mu < 0:
            raise ValueError(f'mu ({self.mu}) must be greater than or equal to 0')

        self.sigma: float | list[float] = kwargs.get('sigma', 0)
        if isinstance(self.sigma, list):
            if len(self.sigma) != self.max_parallel_tasks:
                raise ValueError(f"Length of sigma ({len(self.sigma)}) does not match with max_parallel_tasks ({self.max_parallel_tasks})")
            for i, t in enumerate(self.sigma):
                if t < 0:
                    raise ValueError(f'sigma for {i} tasks ({t}) must be greater than or equal to 0')
        elif self.sigma < 0:
            raise ValueError(f'sigma ({self.sigma}) must be greater than or equal to 0')

        self.z_score: float = kwargs.get('z_score', 2)

    def _proc_time(self, n_tasks: int) -> float:
        mu = self.mu[n_tasks - 1] if isinstance(self.mu, list) else self.mu
        sigma = self.sigma[n_tasks - 1] if isinstance(self.sigma, list) else self.sigma
        return max(gauss(mu, sigma), 0)

    @property
    def expected_proc_time(self) -> float:
        mu = self.mu[0] if isinstance(self.mu, list) else self.mu
        sigma = self.sigma[0] if isinstance(self.sigma, list) else self.sigma
        return mu + sigma * self.z_score
