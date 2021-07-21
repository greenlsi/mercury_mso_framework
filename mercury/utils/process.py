from math import inf
from mercury.msg.network.packet.app_layer.service import ServiceRequest
from typing import Optional, Tuple


class ProcessingUnitProcess:
    def __init__(self, request: ServiceRequest, max_u: float, t_operation: float, t: float):
        self.request: ServiceRequest = request
        self.max_u: float = max_u
        self.t_operation: float = t_operation
        self.t_created: float = t

        self.progress: float = 0
        self.utilization: float = 0
        self.t_started: Optional[float] = None
        self.last_t: Optional[float] = None
        self.finishing_t: float = inf

    def __lt__(self, other):
        """ Processes of PU are sorted in a First-Come-First-Served basis"""
        return self.t_created < other.t_created

    @property
    def info(self) -> Tuple[Tuple[str, str, int], float]:
        return self.request.info, self.progress

    @property
    def finished(self) -> bool:
        return self.progress >= 100

    @property
    def running(self) -> bool:
        return self.utilization > 0

    @property
    def t_burst(self) -> float:
        return self.t_operation * self.progress / 100

    def start(self, t: float, utilization: float) -> float:
        """
        Starts running a process of PU.
        :param t: current time.
        :param utilization: utilization of the PU assigned to process (in %).
        :return: time needed for the process to finish if it is not stopped.
        """
        self._assert_correct_time(t)
        if self.running:
            self.stop(t)
        if self.finished:
            return 0
        if self.t_started is None:
            self.t_started = t
        self.last_t = t
        self.utilization = utilization
        ta = self.t_operation * (100 - self.progress) / 100 * self.max_u / min(self.utilization, self.max_u)
        self.finishing_t = t + ta
        return ta

    def stop(self, t: float) -> float:
        """
        Stops running a process of PU.
        :param t: current time.
        :return: progress of the process (in %).
        """
        self._assert_correct_time(t)
        if self.t_started is None:
            return 0
        if t >= self.finishing_t:
            self.progress = 100
        else:
            t_elapsed = t - self.last_t
            u_fraction = min(self.utilization, self.max_u) / self.max_u
            delta = 100 if self.t_operation <= 0 else 100 * u_fraction * t_elapsed / self.t_operation
            self.progress = min(self.progress + delta, 100)
            self.last_t = t
            self.utilization = 0.
            self.finishing_t = inf
        return self.progress

    def _assert_correct_time(self, t: float):
        if self.last_t is not None and t < self.last_t:
            raise AssertionError('new time is less than last time')
