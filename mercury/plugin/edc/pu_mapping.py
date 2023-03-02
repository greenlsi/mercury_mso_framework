from __future__ import annotations
import mercury.model.edcs.edc.r_manager.pu as mpu
from abc import ABC, abstractmethod
from mercury.config.client import ServicesConfig
from queue import PriorityQueue
from typing import Generic, Iterable, TypeVar


T = TypeVar('T')


class PUMappingStrategy(ABC, Generic[T]):
    def __init__(self, **kwargs):
        pass

    def map_task(self, pus: Iterable[mpu.ProcessingUnit], service_id: str) -> mpu.ProcessingUnit | None:
        best_pu, best_pu_fit = None, None
        for pu in pus:
            pu_fit = self.fitness(pu, service_id)
            if pu_fit is not None and (best_pu is None or pu_fit < best_pu_fit):
                best_pu, best_pu_fit = pu, pu_fit
        return best_pu

    def map_priority_queue(self, pus: Iterable[mpu.ProcessingUnit],
                           service_id: str) -> PriorityQueue[tuple[T, mpu.ProcessingUnit]]:
        queue: PriorityQueue[tuple[T, mpu.ProcessingUnit]] = PriorityQueue()
        for pu in pus:
            fitness = self.fitness(pu, service_id)
            if fitness is not None:
                queue.put((fitness, pu))
        return queue

    def fitness(self, pu: mpu.ProcessingUnit, service_id: str) -> T | None:
        if pu.additional_tasks(service_id) > 0:
            return self._fitness(pu, service_id)

    @abstractmethod
    def _fitness(self, pu: mpu.ProcessingUnit, service_id: str) -> T:
        pass


class FirstFit(PUMappingStrategy[int]):
    def map_task(self, pus: Iterable[mpu.ProcessingUnit], service_id: str) -> mpu.ProcessingUnit | None:
        for pu in pus:
            if self.fitness(pu, service_id) is not None:
                return pu

    def map_priority_queue(self, pus: Iterable[mpu.ProcessingUnit],
                           service_id: str) -> PriorityQueue[tuple[int, mpu.ProcessingUnit]]:
        queue: PriorityQueue[tuple[int, mpu.ProcessingUnit]] = PriorityQueue()
        i = 0
        for pu in pus:
            if self.fitness(pu, service_id) is not None:
                queue.put((i, pu))
                i += 1
        return queue

    def _fitness(self, pu: mpu.ProcessingUnit, service_id: str) -> int:
        return 0


class FullestProcessingUnit(PUMappingStrategy[float]):
    def _fitness(self, pu: mpu.ProcessingUnit, service_id: str) -> float:
        return (pu.additional_tasks(service_id) - 1) / pu.max_n_tasks(service_id)


class EmptiestProcessingUnit(FullestProcessingUnit):
    def _fitness(self, pu: mpu.ProcessingUnit, service_id: str) -> float:
        return -super()._fitness(pu, service_id)


class ShortestProcessingTime(PUMappingStrategy[float]):
    def _fitness(self, pu: mpu.ProcessingUnit, service_id: str) -> float:
        return pu.queue_time + pu.pu_config.srv_configs[service_id].proc_t_model.expected_proc_time


class LongestProcessingTime(ShortestProcessingTime):
    def _fitness(self, pu: mpu.ProcessingUnit, service_id: str) -> float:
        return -super()._fitness(pu, service_id)


class SmallestPowerIncrement(PUMappingStrategy[float]):
    def _fitness(self, pu: mpu.ProcessingUnit, service_id: str) -> float:
        if ServicesConfig.SERVICES[service_id].sess_required:
            n_sessions = len(pu.sessions)
            prev_power = pu.compute_power(pu.busy, pu.service_id, n_sessions)
            return pu.compute_power(True, service_id, n_sessions + 1) - prev_power
        else:
            return pu.compute_power(True, service_id, 1) - pu.compute_power(pu.busy, None, 0)
