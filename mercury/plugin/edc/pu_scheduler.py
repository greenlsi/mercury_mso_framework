from __future__ import annotations
from abc import abstractmethod, ABC
from mercury.config.edcs import ProcessingUnitConfig
from mercury.msg.packet.app_packet.srv_packet import SrvRequestProcess
from queue import PriorityQueue
from typing import Generic, Iterable, TypeVar


T = TypeVar('T')


class ProcessingUnitScheduler(ABC, Generic[T]):
    def __init__(self, **kwargs):
        """
        Processing unit scheduler.
        :param kwargs: any additional configuration parameter for the PU scheduler.
        """
        pass

    def select_tasks(self, t: float, pu_config: ProcessingUnitConfig,
                     processes: Iterable[SrvRequestProcess]) -> list[SrvRequestProcess]:
        """
        For a set of processes, it returns a subset of processes to be immediately processed.
        :param t: current time.
        :param pu_config: configuration parameters of the processing unit.
        :param processes: iterable of processes to be scheduled.
        :return: list containing all the processes to be executed. It is a subset of the input processes.
        """
        queue: PriorityQueue[tuple[T, SrvRequestProcess]] = PriorityQueue()
        for process in processes:
            queue.put((self.task_priority(t, pu_config, process), process))
        scheduled: list[SrvRequestProcess] = list()
        while not queue.empty():
            _, process = queue.get()
            if scheduled and scheduled[0].service_id != process.service_id or \
                    len(scheduled) >= pu_config.srv_configs[process.service_id].max_parallel_tasks:
                break
            scheduled.append(process)
        return scheduled

    @abstractmethod
    def task_priority(self, t: float, pu_config: ProcessingUnitConfig, process: SrvRequestProcess) -> T:
        """
        Computes the priority of a given task.
        :param t: current time.
        :param pu_config: processing unit configuration.
        :param process: task to be evaluated.
        :return: process priority.
        """
        pass


class FirstComeFirstServed(ProcessingUnitScheduler[float]):
    def task_priority(self, t: float, pu_config: ProcessingUnitConfig, process: SrvRequestProcess) -> float:
        return process.t_arrived


class ShortestJobFirst(ProcessingUnitScheduler[float]):
    def task_priority(self, t: float, pu_config: ProcessingUnitConfig, process: SrvRequestProcess) -> float:
        return pu_config.srv_configs[process.service_id].proc_t_model.expected_proc_time


class LongestJobFirst(ProcessingUnitScheduler[float]):
    def task_priority(self, t: float, pu_config: ProcessingUnitConfig, process: SrvRequestProcess) -> float:
        return -pu_config.srv_configs[process.service_id].proc_t_model.expected_proc_time


class ShortestRemainingTimeFirst(ProcessingUnitScheduler[float]):
    def task_priority(self, t: float, pu_config: ProcessingUnitConfig, process: SrvRequestProcess) -> float:
        return pu_config.srv_configs[process.service_id].proc_t_model.expected_proc_time * (1 - process.progress)


class LongestRemainingTimeFirst(ProcessingUnitScheduler[float]):
    def task_priority(self, t: float, pu_config: ProcessingUnitConfig, process: SrvRequestProcess) -> float:
        return pu_config.srv_configs[process.service_id].proc_t_model.expected_proc_time * (process.progress - 1)


class EarliestDeadlineFirst(ProcessingUnitScheduler[float]):
    def task_priority(self, t: float, pu_config: ProcessingUnitConfig, process: SrvRequestProcess) -> float:
        return process.t_deadline


class LeastLaxityFirst(ProcessingUnitScheduler[float]):
    def task_priority(self, t: float, pu_config: ProcessingUnitConfig, process: SrvRequestProcess) -> float:
        t_remaining = pu_config.srv_configs[process.service_id].proc_t_model.expected_proc_time * (1 - process.progress)
        return process.t_deadline - (t + t_remaining)
