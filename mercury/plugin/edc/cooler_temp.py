from abc import ABC, abstractmethod
from typing import Dict


class EdgeDataCenterCoolerTemperatureModel(ABC):
    def __init__(self, **kwargs):
        """
        Edge Data Center Cooler Temperature Model (Abstract class).
        :param kwargs: any parameter required for initializing the model.
        """
        pass

    @abstractmethod
    def compute_cooler_temperature(self, pu_temperatures: Dict[str, float]) -> float:
        """
        :param pu_temperatures: dictionary {pu_id: temp (in Kelvin)}.
        :return: temperature of the Edge Data Center.
        """
        pass
