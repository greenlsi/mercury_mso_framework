from abc import ABC, abstractmethod
from ....common.plugin_loader import load_plugins
from math import inf


class ResourceManagerDispatchingStrategy(ABC):
    maximum = staticmethod(lambda new, best:  0 <= new <= best)
    minimum = staticmethod(lambda new, best: new >= best)
    initial_max = inf
    initial_min = 0

    def __init__(self, **kwargs):
        pass

    def allocate_task(self, service_id: str, session_id: str, service_u: float, expected_u: dict, max_u: dict) -> tuple:
        """
        :param service_id: ID of the service
        :param session_id: ID of the session
        :param service_u: utilization factor of the service to be allocated
        :param expected_u: {rack_id: {pu_index: expected_u}}
        :param max_u: {rack_id: {pu_index: max_u}}
        :return: rack ID and index of the processing unit that is to allocate the new session
        """
        pu_index = None
        rack_reports = {rack_id: sum(p_units.values()) for rack_id, p_units in expected_u.items()}
        rack_max = {rack_id: sum(p_units.values()) for rack_id, p_units in max_u.items()}
        initial_value, condition = self.get_rack_conditions()
        rack_id = self.allocate_in_unit(rack_reports, rack_max, service_u, initial_value, condition)
        if rack_id is not None:
            initial_value, condition = self.get_pu_conditions()
            pu_index = self.allocate_in_unit(expected_u[rack_id], max_u[rack_id], service_u, initial_value, condition)
        return rack_id, pu_index

    @abstractmethod
    def get_rack_conditions(self):
        pass

    @abstractmethod
    def get_pu_conditions(self):
        pass

    def change_p_units_status(self, expected_created, max_u, hw_power_off, n_hot_standby):
        """
        :param dict expected_created: {rack_id: {pu_index: [services]}
        :param dict max_u: {rack_id: {pu_index: max_u}}
        :param bool hw_power_off: Unused hardware strategy
        :param int n_hot_standby: Number of required PUs in hot standby
        :return dict: {rack_id: {pu_index: new_status}}
        """
        res = {rack_id: {pu_index: (not hw_power_off or bool(services)) for pu_index, services in p_units.items()}
               for rack_id, p_units in expected_created.items()}
        empty = {rack_id: {pu_index: 0 for pu_index, status in p_units.items() if not status}
                 for rack_id, p_units in res.items()}
        for i in range(n_hot_standby):
            rack_id, pu_index = self.allocate_task('hot_standby', str(i), 0, empty, max_u)
            if rack_id is None or pu_index is None:
                break
            res[rack_id][pu_index] = True
            empty[rack_id].pop(pu_index)
        return res

    @staticmethod
    def set_dvfs_mode(expected_dvfs, hw_dvfs_mode):
        """
        :param dict expected_dvfs: {rack_id: {pu_index: expected_dvfs_mode}}
        :param bool hw_dvfs_mode: Unused hardware strartegy
        :return dict: {rack_id: {pu_index: new_dvfs_mode}}
        """
        res = dict()
        for rack_id, p_units in expected_dvfs.items():
            for pu_index, expected in p_units.items():
                if expected != hw_dvfs_mode:
                    if rack_id not in res:
                        res[rack_id] = dict()
                    res[rack_id][pu_index] = hw_dvfs_mode
        return res

    @staticmethod
    def allocate_in_unit(report_set, max_u_set, utilization, initial_space, lambda_condition):
        unit_id = None
        best_unit_space = initial_space
        for unit, u in report_set.items():
            unit_space = max_u_set[unit] - u - utilization
            if lambda_condition(unit_space, best_unit_space):
                unit_id = unit
                best_unit_space = unit_space
        return unit_id


class EmptiestRackEmptiestProcessingUnit(ResourceManagerDispatchingStrategy):
    def get_rack_conditions(self):
        return self.initial_min, self.minimum

    def get_pu_conditions(self):
        return self.initial_min, self.minimum


class EmptiestRackFullestProcessingUnit(ResourceManagerDispatchingStrategy):
    def get_rack_conditions(self):
        return self.initial_min, self.minimum

    def get_pu_conditions(self):
        return self.initial_max, self.maximum


class FullestRackEmptiestProcessingUnit(ResourceManagerDispatchingStrategy):
    def get_rack_conditions(self):
        return self.initial_max, self.maximum

    def get_pu_conditions(self):
        return self.initial_min, self.minimum


class FullestRackFullestProcessingUnit(ResourceManagerDispatchingStrategy):
    def get_rack_conditions(self):
        return self.initial_max, self.maximum

    def get_pu_conditions(self):
        return self.initial_max, self.maximum


class DispatchingStrategyFactory:
    def __init__(self):
        self._strategy = dict()
        for key, strategy in load_plugins('mercury.edc.dispatching.plugins').items():
            self.register_strategy(key, strategy)

    def register_strategy(self, key: str, strategy: ResourceManagerDispatchingStrategy):
        self._strategy[key] = strategy

    def is_strategy_defined(self, key: str) -> bool:
        return key in self._strategy

    def create_strategy(self, key, **kwargs) -> ResourceManagerDispatchingStrategy:
        strategy = self._strategy.get(key)
        if not strategy:
            raise ValueError(key)
        return strategy(**kwargs)
