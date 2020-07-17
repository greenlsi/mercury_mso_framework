from abc import ABC, abstractmethod
from ......common.plugin_loader import load_plugins


class RackTemperatureModel(ABC):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def compute_rack_temperature(self, pu_temperatures_list: list) -> float:
        """
        :param pu_temperatures_list: list of floats that represent the temperature of processing units within the rack
        :return: temperature of the rack
        """
        pass


class RackTemperatureModelFactory:
    def __init__(self):
        self._models = dict()
        for key, model in load_plugins('mercury.edc.rack_temp.plugins').items():
            self.register_model(key, model)

    def register_model(self, key: str, model: RackTemperatureModel):
        self._models[key] = model

    def is_model_defined(self, key: str) -> bool:
        return key in self._models

    def create_model(self, key: str, **kwargs) -> RackTemperatureModel:
        model = self._models.get(key)
        return model(**kwargs) if model is not None else None
