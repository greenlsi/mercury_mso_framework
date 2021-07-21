from abc import ABC, abstractmethod
from typing import Any


class ProcessingUnitTemperatureModel(ABC):
    def __init__(self, **kwargs):
        """
        Processing Unit Temperature Model
        :param kwargs: additional configuration parameters
        """
        pass

    @abstractmethod
    def compute_temperature(self, status: bool, utilization: float, dvfs_config: Any) -> float:
        """
        Compute temperature according to a temperature model. This method is user-defined.
        :param status: PU status (True if switched on)
        :param utilization: Utilization factor of a given processing unit
        :param dvfs_config: current DVFS configuration
        :returns temperature: Processing Unit temperature (in Kelvin)
        """
        pass
