from abc import ABC, abstractmethod
from ......common.plugin_loader import load_plugins


class RackPowerModel(ABC):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def compute_rack_power(self, it_power: float, rack_temp: float, env_temp: float) -> float:
        """
        :param it_power: Power consumed by the IT equipment that has to be dissipated
        :param rack_temp: temperature of the track (in K)
        :param env_temp: temperature of the environment within the EDC that contains the rack (in K)
        :return: power consumption required for refrigerating the rack (in Watts)
        """
        pass


class RackPowerModelFactory:
    def __init__(self):
        self._models = dict()
        for key, model in load_plugins('mercury.edc.rack_pwr.plugins').items():
            self.register_model(key, model)

    def register_model(self, key: str, model: RackPowerModel):
        self._models[key] = model

    def is_model_defined(self, key: str) -> bool:
        return key in self._models

    def create_model(self, key: str, **kwargs) -> RackPowerModel:
        model = self._models.get(key)
        return model(**kwargs) if model is not None else None
