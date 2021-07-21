import mercury.fog_model.edcs.edc.r_manager as rm
from abc import ABC, abstractmethod
from collections import defaultdict
from mercury.config.edcs import EdgeDataCenterConfig
from queue import PriorityQueue
from typing import Any, Dict, List, Optional, Tuple
from .mapping import MappingStrategy


ProcessingUnitDigitalTwin = rm.ProcessingUnitDigitalTwin


class HotStandbyStrategy(ABC):
    def __init__(self, **kwargs):
        edc_config: EdgeDataCenterConfig = kwargs['edc_config']
        self.edc_config = edc_config
        self.pu_twins: Dict[str, ProcessingUnitDigitalTwin] = dict()
        for pu_id, pu_config in edc_config.pus_config.items():
            self.pu_twins[pu_id] = ProcessingUnitDigitalTwin(edc_config.edc_id, pu_id, pu_config, edc_config.env_temp)

    @abstractmethod
    def update_hot_standby(self, **kwargs):
        pass

    @abstractmethod
    def explore_hot_standby(self, mapping: MappingStrategy, starting: Dict[str, Dict[str, ProcessingUnitDigitalTwin]],
                            started: Dict[str, Dict[str, ProcessingUnitDigitalTwin]],
                            stopping: Dict[str, Dict[str, ProcessingUnitDigitalTwin]]) -> Dict[str, bool]:
        pass


class FullHotStandby(HotStandbyStrategy):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.standby: bool = kwargs.get('standby', False)

    def update_hot_standby(self, **kwargs):
        self.standby = kwargs.get('standby', False)

    def explore_hot_standby(self, mapping: MappingStrategy, starting: Dict[str, Dict[str, ProcessingUnitDigitalTwin]],
                            started: Dict[str, Dict[str, ProcessingUnitDigitalTwin]],
                            stopping: Dict[str, Dict[str, ProcessingUnitDigitalTwin]]) -> Dict[str, bool]:
        return {pu_id: self.standby for pu_id in self.pu_twins}


class SessionHotStandby(HotStandbyStrategy):
    def __init__(self, **kwargs):
        """
        :param Dict[str, int] min_sessions: Minimum number of sessions in hot standby. Active sessions are considered as
                                            part of the hot standby sessions.
        :param Dict[str, int] extra_sessions: Number of sessions in hot standby required apart from already active sessions.
        """
        super().__init__(**kwargs)
        self.min_sessions: Dict[str, int] = kwargs.get('min_sessions', dict())
        self.extra_sessions: Dict[str, int] = kwargs.get('extra_sessions', dict())

        self.hot_sessions: Dict[str, List[ProcessingUnitDigitalTwin]] = dict()

        self.prev_mapping: Optional[MappingStrategy] = None
        self.last_srv: Optional[str] = None
        self.last_srv_discards: List = list()
        self.last_srv_costs: Optional[PriorityQueue[Tuple[Any, ProcessingUnitDigitalTwin]]] = None

    def update_hot_standby(self, **kwargs):
        self.min_sessions = kwargs.get('min_sessions', dict())
        self.extra_sessions = kwargs.get('extra_sessions', dict())

    def explore_hot_standby(self, mapping: MappingStrategy, starting: Dict[str, Dict[str, ProcessingUnitDigitalTwin]],
                            started: Dict[str, Dict[str, ProcessingUnitDigitalTwin]],
                            stopping: Dict[str, Dict[str, ProcessingUnitDigitalTwin]]) -> Dict[str, bool]:
        if mapping != self.prev_mapping:
            self._reset_hot_standby()
        self.prev_mapping = mapping

        sessions_required = self._compute_required_sessions(starting, started, stopping)
        # First, we try to re-use last service
        if self.last_srv is not None:
            n_sessions = sessions_required.pop(self.last_srv, 0)
            if n_sessions > 0:
                self.add_hot_sessions(mapping, n_sessions)
            elif n_sessions < 0:
                self.remove_hot_sessions(-n_sessions)

        for service_id, n_sessions in sessions_required.items():
            if n_sessions:
                self.last_srv = service_id
                self.last_srv_discards = list()
                self.last_srv_costs = mapping.create_fitness_queue(self.pu_twins.values(), service_id)
                if n_sessions > 0:
                    self.add_hot_sessions(mapping, n_sessions)
                elif n_sessions < 0:
                    self.remove_hot_sessions(-n_sessions)

        return {pu.pu_id: pu.status for pu in self.pu_twins.values()}

    def add_hot_sessions(self, mapping: MappingStrategy, n: int):
        for _ in range(n):
            queue_used: bool = False
            if self.last_srv_discards:              # Check if we can reuse previous predictions
                pu = self.last_srv_discards.pop()
            elif self.last_srv_costs.empty():  # If hot standby queue is empty, we cannot add more sessions
                break
            else:                                       # Otherwise, we take the best option from the queue
                queue_used = True
                _, pu = self.last_srv_costs.get()

            if self.last_srv not in self.hot_sessions:
                self.hot_sessions[self.last_srv] = list()
            self.hot_sessions[self.last_srv].append(pu)
            pu.start_starting_session(self.last_srv, 'hot_{}'.format(len(self.hot_sessions[self.last_srv])))
            pu.finish_starting_session(self.last_srv, 'hot_{}'.format(len(self.hot_sessions[self.last_srv])), True)

            if queue_used:                              # If used, we try to add an updated prediction to the queue
                new_cost = mapping.fitness_function(pu, self.last_srv)
                if new_cost is not None:
                    self.last_srv_costs.put((new_cost, pu))

    def remove_hot_sessions(self, n: int):
        for _ in range(n):
            pu = self.hot_sessions[self.last_srv].pop()
            pu.start_stopping_session(self.last_srv, 'hot_{}'.format(1 + len(self.hot_sessions[self.last_srv])))
            pu.finish_stopping_session(self.last_srv, 'hot_{}'.format(1 + len(self.hot_sessions[self.last_srv])), True)
            if not self.hot_sessions[self.last_srv]:
                self.hot_sessions.pop(self.last_srv)
            self.last_srv_discards.append(pu)

    def _reset_hot_standby(self):
        self.last_srv = None
        self.last_srv_discards = list()
        self.last_srv_costs = None
        self.extra_hot = dict()
        for pu_twin in self.pu_twins.values():
            pu_twin.reset()

    def _compute_required_sessions(self, starting: Dict[str, Dict[str, ProcessingUnitDigitalTwin]],
                                   started: Dict[str, Dict[str, ProcessingUnitDigitalTwin]],
                                   stopping: Dict[str, Dict[str, ProcessingUnitDigitalTwin]]) -> Dict[str, int]:
        current_sessions = defaultdict(lambda: 0)
        for states in (starting, started, stopping):
            for srv, sessions in states.items():
                current_sessions[srv] += len(sessions)

        sessions_required = dict()
        for srv in {*self.min_sessions, *self.extra_sessions, *self.hot_sessions}:
            min_sessions = self.min_sessions.get(srv, 0)
            extra_sessions = max(current_sessions[srv] - min_sessions + self.extra_sessions.get(srv, 0), 0)
            sessions = min_sessions + extra_sessions
            sessions_required[srv] = sessions - len(self.hot_sessions.get(srv, list()))
        return sessions_required
