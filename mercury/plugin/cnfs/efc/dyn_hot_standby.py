import mercury.config.edcs as config
import mercury.msg.edcs as msg
from abc import ABC, abstractmethod
from math import ceil
from typing import Dict, Tuple, Any, Optional


EdgeDataCenterConfig = config.EdgeDataCenterConfig
HotStandbyFunction = msg.HotStandbyFunction


class DynamicHotStandby(ABC):

    def __init__(self, **kwargs):
        self.hot_standby_functions: Dict[str, Tuple[str, Dict[str, Any]]] = dict()

        edc_configs: Dict[str, EdgeDataCenterConfig] = kwargs.get('edcs_config')
        for edc_id, edc_config in edc_configs.items():
            rm_config = edc_config.r_manager_config
            self.hot_standby_functions[edc_id] = (rm_config.hot_standby_name, rm_config.hot_standby_config)

    def hot_standby(self, edc_id: str, cost: Optional[float],
                    demand: Dict[str, Optional[float]]) -> Optional[HotStandbyFunction]:
        new_function_id, new_function_config = self.assign_hot_standby(cost, demand)
        prev_function_id, prev_function_config = self.hot_standby_functions[edc_id]
        if new_function_id != prev_function_id or new_function_config != prev_function_config:
            self.hot_standby_functions[edc_id] = (new_function_id, new_function_config)
            return HotStandbyFunction(edc_id, new_function_id, new_function_config)

    @abstractmethod
    def assign_hot_standby(self, cost: Optional[float],
                           demand: Dict[str, Optional[float]]) -> Tuple[str, Dict[str, Any]]:
        pass


class SessionDynamicHotStandby(DynamicHotStandby):
    def __init__(self, **kwargs):
        """
        Session-based dynamic hot standby strategy.
        :param default_n_sessions: Default number of sessions per service. If demand is unknown or too low, the number
                                   of hot standby sessions will be selected from the default.
        :param kwargs: any additional configuration parameter. For more information, see DynamicHotStandby.
        """
        super().__init__(**kwargs)
        self.default_n_sessions: Dict[str, int] = kwargs.get('default_n_sessions', dict())

    def assign_hot_standby(self, cost: Optional[float],
                           demand: Dict[str, Optional[float]]) -> Tuple[str, Dict[str, Any]]:
        function_config: Dict[str, int] = dict()
        for service, n_users in demand.items():
            n_sessions: int = max(self.default_n_sessions.get(service, 0), 0 if n_users is None else ceil(n_users))
            function_config[service] = n_sessions
        return 'session', {'min_sessions': function_config}
