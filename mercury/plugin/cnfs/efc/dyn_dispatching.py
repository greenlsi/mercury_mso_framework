from abc import ABC, abstractmethod
from mercury.config.edcs import EdgeDataCenterConfig
from mercury.msg.edcs import DispatchingFunction
from typing import Any, Dict, Optional, Tuple


class DynamicMapping(ABC):
    def __init__(self, **kwargs):
        self.mapping_functions: Dict[str, Tuple[str, Dict[str, Any]]] = dict()

        edc_configs: Dict[str, EdgeDataCenterConfig] = kwargs.get('edcs_config')
        for edc_id, edc_config in edc_configs.items():
            rm_config = edc_config.r_manager_config
            self.mapping_functions[edc_id] = (rm_config.mapping_name, rm_config.mapping_config)

    def mapping(self, edc_id: str, cost: Optional[float],
                demand: Dict[str, Optional[float]]) -> Optional[DispatchingFunction]:
        new_function_id, new_function_config = self.assign_mapping(cost, demand)
        prev_function_name, prev_function_config = self.mapping_functions[edc_id]
        if new_function_id != prev_function_name or new_function_config != prev_function_config:
            self.mapping_functions[edc_id] = (new_function_id, new_function_config)
            return DispatchingFunction(edc_id, new_function_id, new_function_config)

    @abstractmethod
    def assign_mapping(self, cost: Optional[float],
                       demand: Dict[str, Optional[float]]) -> Tuple[str, Dict[str, Any]]:
        pass
