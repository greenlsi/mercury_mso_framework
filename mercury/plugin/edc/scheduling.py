import mercury.utils.process as p
from abc import abstractmethod, ABC
from queue import PriorityQueue
from typing import Dict, Generic, Iterable, List, Tuple, TypeVar


ProcessingUnitProcess = p.ProcessingUnitProcess


class SchedulingAlgorithm(ABC):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def schedule_tasks(self, tasks: Iterable[ProcessingUnitProcess],
                       total_u: float, t: float) -> Dict[ProcessingUnitProcess, float]:
        pass


class RoundRobinScheduler(SchedulingAlgorithm):
    def schedule_tasks(self, tasks: Iterable[ProcessingUnitProcess],
                       total_u: float, t: float) -> Dict[ProcessingUnitProcess, float]:
        res: Dict[ProcessingUnitProcess, float] = dict()
        pending: Dict[ProcessingUnitProcess, float] = dict()  # Contains all the processes and its maximum utilization
        for task in tasks:
            res[task] = 0
            pending[task] = task.max_u
        # Share the available resources evenly (if a process needs less resources, share the gap evenly too)
        u_gap: float = total_u
        while pending and u_gap > 0:
            u_delta: float = u_gap / len(pending)
            exhaust: List[ProcessingUnitProcess] = list()     # Processes that reached its maximum utilization
            for process, max_u in pending.items():
                u_increment = u_delta
                if u_increment > max_u - res[process]:
                    u_increment = max_u - res[process]
                    exhaust.append(process)
                u_gap -= u_increment
                res[process] += u_increment
            for process in exhaust:                           # Remove exhausted processes from pending list
                pending.pop(process)
        return res


T = TypeVar('T')


class PrioritySchedulingAlgorithm(SchedulingAlgorithm, ABC, Generic[T]):
    def schedule_tasks(self, tasks: Iterable[ProcessingUnitProcess],
                       total_u: float, t: float) -> Dict[ProcessingUnitProcess, float]:
        res: Dict[ProcessingUnitProcess, float] = dict()
        # 1. Create process priority queue
        queue: PriorityQueue[Tuple[T, ProcessingUnitProcess]] = PriorityQueue()
        for task in tasks:
            queue.put((self.get_priority(task), task))
        # 2. Assign resources to processes according to their priority
        u_gap: float = total_u
        while not queue.empty() and u_gap > 0:
            _, process = queue.get()
            process_u = min(process.max_u, u_gap)
            res[process] = process_u
            u_gap -= process_u
        return res

    @abstractmethod
    def get_priority(self, process: ProcessingUnitProcess) -> T:
        pass


class FirstComeFirstServed(PrioritySchedulingAlgorithm[float]):
    def get_priority(self, process: ProcessingUnitProcess) -> float:
        return process.t_created


class ShortestJobFirst(PrioritySchedulingAlgorithm[float]):
    def get_priority(self, process: ProcessingUnitProcess) -> float:
        return process.t_operation


class LongestJobFirst(PrioritySchedulingAlgorithm[float]):
    def get_priority(self, process: ProcessingUnitProcess) -> float:
        return -process.t_operation


class ShortestRemainingTimeFirst(PrioritySchedulingAlgorithm[float]):
    def get_priority(self, process: ProcessingUnitProcess) -> float:
        return process.t_operation * (1 - process.progress / 100)


class LongestRemainingTimeFirst(PrioritySchedulingAlgorithm[float]):
    def get_priority(self, process: ProcessingUnitProcess) -> float:
        return process.t_operation * (process.progress / 100 - 1)
