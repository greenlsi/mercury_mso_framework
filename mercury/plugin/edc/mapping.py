import mercury.fog_model.edcs.edc.r_manager as rm
from mercury.config.edcs import EdgeDataCenterConfig
from abc import ABC, abstractmethod
from math import inf
from queue import PriorityQueue
from typing import Generic, Iterable, List, Optional, TypeVar


T = TypeVar('T')


class MappingStrategy(ABC, Generic[T]):
    def __init__(self, **kwargs):
        self.edc_config: EdgeDataCenterConfig = kwargs['edc_config']

    def fitness_function(self, pu: rm.ProcessingUnitDigitalTwin, service_id: str, extra_u: float = 0) -> Optional[T]:
        srv_config = pu.pu_config.services.get(service_id)
        service_u = inf if srv_config is None else srv_config.max_u
        if pu.reserved_u + extra_u + service_u <= 100:
            return self._fitness_function(pu, service_id, extra_u)

    def create_fitness_queue(self, pus: Iterable[rm.ProcessingUnitDigitalTwin], service_id: str) -> PriorityQueue:
        res = PriorityQueue()
        for pu in pus:
            pu_cost: Optional[T] = self.fitness_function(pu, service_id, 0)
            if pu_cost is not None:
                res.put((pu_cost, pu))
        return res

    @abstractmethod
    def allocate_session(self, service_id: str, pus: Iterable[rm.ProcessingUnitDigitalTwin]) \
            -> Optional[rm.ProcessingUnitDigitalTwin]:
        pass

    @abstractmethod
    def _fitness_function(self, pu: rm.ProcessingUnitDigitalTwin, service_id: str, extra_u: float = 0) -> T:
        pass


class FirstFitMapping(MappingStrategy[int]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pu_ids: List[str] = list(self.edc_config.pus_config)

    def allocate_session(self, service_id: str, pus: Iterable[rm.ProcessingUnitDigitalTwin]) \
            -> Optional[rm.ProcessingUnitDigitalTwin]:
        for pu in pus:
            if self.fitness_function(pu, service_id) is not None:
                return pu

    def _fitness_function(self, pu: rm.ProcessingUnitDigitalTwin, service_id: str, extra_u: float = 0) -> int:
        return self.pu_ids.index(pu.pu_id)


class BestFitMapping(MappingStrategy[T], ABC, Generic[T]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def allocate_session(self, service_id: str, pus: Iterable[rm.ProcessingUnitDigitalTwin]) \
            -> Optional[rm.ProcessingUnitDigitalTwin]:
        queue = self.create_fitness_queue(pus, service_id)
        if not queue.empty():
            _, pu = queue.get()
            return pu


class EmptiestProcessingUnit(BestFitMapping[float]):
    def _fitness_function(self, pu: rm.ProcessingUnitDigitalTwin, service_id: str, extra_u: float = 0) -> float:
        return pu.utilization + extra_u + pu.pu_config.services[service_id].max_u


class FullestProcessingUnit(EmptiestProcessingUnit):
    def _fitness_function(self, pu: rm.ProcessingUnitDigitalTwin, service_id: str, extra_u: float = 0) -> float:
        return -super()._fitness_function(pu, service_id, extra_u)


class LessITPowerIncrement(BestFitMapping[float]):
    def _fitness_function(self, pu: rm.ProcessingUnitDigitalTwin, service_id: str, extra_u: float = 0) -> float:
        prev_pow = pu.approx_power if extra_u == 0 else pu.predict_power(True, pu.reserved_u + extra_u)
        new_pow = pu.predict_power(True, pu.reserved_u + extra_u + pu.pu_config.services[service_id].max_u)
        return new_pow - prev_pow
