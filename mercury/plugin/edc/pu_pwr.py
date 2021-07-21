from abc import ABC, abstractmethod
from typing import Dict, Any


class ProcessingUnitPowerModel(ABC):
    def __init__(self, **kwargs):
        """
        Processing Unit power model
        :param kwargs: additional configuration parameters
        """
        pass

    @abstractmethod
    def compute_power(self, status: bool, utilization: float, dvfs_config: Any) -> float:
        """
        Compute power consumption according to a power model. This method is user-defined.
        :param status: PU status (True if switched on)
        :param utilization: Utilization factor of a given processing unit
        :param dvfs_config: DVFS configuration parameters
        :returns power: Processing Unit power consumption (in Watts)
        """
        pass


class IdleActivePowerModel(ProcessingUnitPowerModel):
    def __init__(self, **kwargs):
        """
        Idle/active power model for processing unit.
            If switched off, power consumption is 0.
            If switched on but with no services ongoing, power consumption is idle_power.
            If switched on and with services ongoing, power consumption is active_power.
        :param float idle_power: power consumption when processing unit is idling.
        :param float active_power: power consumption when processing unit is working.
        """
        super().__init__()
        self.idle_power: float = kwargs.get('idle_power', 0)
        self.active_power: float = kwargs.get('active_power', 0)

    def compute_power(self, status: bool, utilization: float, dvfs_config: Any) -> float:
        return 0 if not status else self.idle_power if utilization == 0 else self.active_power


class StaticDynamicPowerModel(ProcessingUnitPowerModel):
    def __init__(self, **kwargs):
        """
        Static + Dynamic power model for processing unit.
        If switched off, power consumption is 0.
        If switched on, power consumption is Pstatic + Pdynamic, where Pdynamic is:
            Pdyn = alpha*V(t)^2 + f(t)*u(t)
                alpha: constant
                V(t): working voltage (it is substracted from the DVFS configuration)
                f(t): working frequency in GHz (it is substracted from the DVFS configuration)
                u(t) instantaneous utilzation factor
        :param float static_power: static power consumption.
        :param float alpha: alpha constant.
        :param string voltage_dvfs_label: label for taking voltage from the DVFS table.
        :param string frequency_dvfs_label: label for taking frequency from DVFS table.
        """
        super().__init__()
        self.static_power = kwargs.get('static_power', 0)
        self.alpha = kwargs.get('alpha', 0)
        self.voltage_dvfs_label = kwargs.get('voltage_dvfs_label', 'v')
        self.frequency_dvfs_label = kwargs.get('frequency_dvfs_label', 'f')

    def compute_power(self, status: bool, utilization: float, dvfs_config: Dict[str, float]) -> float:
        power = 0
        if status:
            power = self.static_power
            v = dvfs_config.get(self.voltage_dvfs_label, 0)
            pow_1 = self.alpha * (v ** 2)
            f = dvfs_config.get(self.frequency_dvfs_label, 0)
            pow_2 = f * utilization
            power += pow_1 + pow_2
        return power
