from abc import ABC, abstractmethod
from ......common.plugin_loader import load_plugins


class ProcessingUnitTemperatureModel(ABC):
    """
    Temperature model of a given processing unit.
    """
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def compute_temperature(self, status, utilization, max_u, dvfs_index, dvfs_table):
        """
        Compute temperature according to a temperature model. This method is user-defined.
        :param bool status: PU status (True if switched on)
        :param float utilization: Utilization factor of a given processing unit
        :param flaot max_u: Maximum utilization factor of a given processing unit
        :param int dvfs_index: current DVFS table index
        :param dict dvfs_table: DVFS table
        :returns power: Processing Unit power consumption
        """
        pass


class ProcessingUnitTemperatureModelFactory:
    def __init__(self):
        self._models = dict()
        for key, model in load_plugins('mercury.edc.pu_temp.plugins').items():
            self.register_model(key, model)

    def register_model(self, key: str, model: ProcessingUnitTemperatureModel):
        self._models[key] = model

    def is_model_defined(self, key: str) -> bool:
        return key in self._models

    def create_model(self, key: str, **kwargs) -> ProcessingUnitTemperatureModel:
        model = self._models.get(key)
        return model(**kwargs) if model is not None else None
