from __future__ import annotations
from abc import ABC, abstractmethod
from math import inf
from mercury.msg.smart_grid import EnergyConsumption


class ConsumerManager(ABC):
    def __init__(self, **kwargs):
        """
        Abstract Base Class for smart grid consumer manager. This class manages the power storage resources.
        :param bool | None allow_charge: It indicates if the storage module can consume electricity from the
               grid for charging itself. By default, it is set to False.
        :param bool | None allow_discharge: It indicates if the consumer can use the energy stored in the storage
               module. By default, it is set to False.
        """
        self.allow_charge: bool = kwargs.get('allow_charge', False)
        self.allow_discharge: bool = kwargs.get('allow_discharge', False)

    def update(self, report: EnergyConsumption | None):
        self.allow_charge, self.allow_discharge = self.consumption_config(report)

    @abstractmethod
    def consumption_config(self, report: EnergyConsumption | None) -> tuple[bool, bool]:
        pass


class StaticConsumerManager(ConsumerManager):
    """This consumption manager doesn't depend on electricity cost. It always provides the initial configuration."""
    def consumption_config(self, report: EnergyConsumption | None) -> tuple[bool, bool]:
        return self.allow_charge, self.allow_discharge


class MinDischargeMaxChargeConsumerManager(ConsumerManager):
    def __init__(self, **kwargs):
        """
        This consumption manager sets a minimum cost threshold to discharge the storage device, as well as a maximum
        cost threshold to discharge the storage device.
        :param float | None max_charge_cost: if electricity cost is less than or equal to max_charge_cost,
               the consumer is allowed to consume electricity to charge the storage device. By default, it is set to 0.
        :param float | None min_discharge_cost: if electricity cost is greater than or equal to min_discharge_cost,
               the consumer is allowed to get electricity from the storage device. By default, it is set to infinity.
        :param kwargs: Any additional parameter. See ConsumptionManager for more details.
        """
        super().__init__(**kwargs)
        self.max_charge_cost: float = kwargs.get('max_charge_cost', 0)
        self.min_discharge_cost: float = kwargs.get('min_discharge_cost', inf)

    def consumption_config(self, report: EnergyConsumption | None) -> tuple[bool, bool]:
        if report is None:
            return self.allow_charge, self.allow_discharge
        charge_from_grid = report.energy_cost <= self.max_charge_cost
        allow_discharge = report.energy_cost >= self.min_discharge_cost
        return charge_from_grid, allow_discharge
