from abc import ABC, abstractmethod
from math import inf
from typing import Tuple, Optional


class ConsumptionManager(ABC):
    def __init__(self, **kwargs):
        """
        Abstract Base Class for consumption manager. This class decides how to manage the power storage resources.
        :param Optional[bool] charge_from_grid: It indicates if the storage module can consume electricity from the
               grid for charging itself. By default, it is set to False.
        :param Optional[bool] allow_discharge: It indicates if the consumer can use the energy stored in the storage
               module. By default, it is set to False.
        """
        self.charge_from_grid: bool = kwargs.get('charge_from_grid', False)
        self.allow_discharge: bool = kwargs.get('allow_discharge', False)

    def refresh_consumption_config(self, offer: Optional[float]):
        self.charge_from_grid, self.allow_discharge = self.consumption_config(offer)

    @abstractmethod
    def consumption_config(self, offer: Optional[float]) -> Tuple[bool, bool]:
        pass


class StaticConsumptionManager(ConsumptionManager):
    """This consumption manager doesn't depend on electricity cost. It always provides the initial configuration."""
    def consumption_config(self, offer: Optional[float]) -> Tuple[bool, bool]:
        return self.charge_from_grid, self.allow_discharge


class MinDischargeMaxChargeConsumptionManager(ConsumptionManager):
    def __init__(self, **kwargs):
        """
        This consumption manager sets a minimum cost threshold to discharge the storage device, as well as a maximum
        cost threshold to discharge the storage device.
        :param Optional[float] max_charge_cost: if electricity cost is less than or equal to max_charge_cost,
               the consumer is allowed to consume electricity to charge the storage device. By default, it is set to 0.
        :param Optional[float] min_discharge_cost: if electricity cost is greater than or equal to min_discharge_cost,
               the consumer is allowed to get electricity from the storage device. By default, it is set to infinity.
        :param kwargs: Any additional parameter. See ConsumptionManager for more details.
        """
        super().__init__(**kwargs)
        self.max_charge_cost: float = kwargs.get('max_charge_cost', 0)
        self.min_discharge_cost: float = kwargs.get('min_discharge_cost', inf)

    def consumption_config(self, offer: Optional[float]) -> Tuple[bool, bool]:
        if offer is None:
            return self.charge_from_grid, self.allow_discharge
        charge_from_grid = offer <= self.max_charge_cost
        allow_discharge = offer >= self.min_discharge_cost
        return charge_from_grid, allow_discharge
