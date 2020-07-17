from abc import ABC, abstractmethod
from ......common.plugin_loader import load_plugins


class ProcessingUnitPowerModel(ABC):
    """
    Power model of a given processing unit.
    """
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def compute_power(self, status: bool, utilization: float, max_u: float, dvfs_index: int, dvfs_table: dict) -> float:
        """
        Compute power consumption according to a power model. This method is user-defined.
        :param status: PU status (True if switched on)
        :param utilization: Utilization factor of a given processing unit
        :param max_u: Maximum utilization factor of a given processing unit
        :param dvfs_index: current DVFS table index
        :param dvfs_table: DVFS table
        :returns power: Processing Unit power consumption (in Watts)
        """
        pass


class ProcessingUnitPowerModelFactory:
    def __init__(self):
        self._models = dict()
        for key, model in load_plugins('mercury.edc.pu_pwr.plugins').items():
            self.register_model(key, model)

    def register_model(self, key: str, model: ProcessingUnitPowerModel):
        self._models[key] = model

    def is_model_defined(self, key: str) -> bool:
        return key in self._models

    def create_model(self, key: str, **kwargs) -> ProcessingUnitPowerModel:
        model = self._models.get(key)
        return None if model is None else model(**kwargs)
