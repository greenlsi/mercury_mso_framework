from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, Tuple, TypeVar


class ProcessingUnitPowerModel(ABC):
    def __init__(self, **kwargs):
        """
        Processing unit power consumption model.
        :param int max_parallel_tasks: maximum number of tasks that the processing unit can execute in parallel.
        :param kwargs: any additional configuration parameter.
        """
        self.max_parallel_tasks: int = kwargs['max_parallel_tasks']

    def utilization(self, n_tasks: int) -> float:
        """:return: the utilization factor of the processing unit."""
        return min(n_tasks / self.max_parallel_tasks, 1)

    def compute_power(self, n_tasks: int) -> float:
        """
        Compute power consumption depending on the number of tasks running concurrently.
        :param n_tasks: number of active tasks.
        :return: power consumption (in Watts) of the processing unit.
        """
        if n_tasks < 0 or n_tasks > self.max_parallel_tasks:
            raise ValueError("Invalid number of tasks being executed by PU")
        return self._compute_power(n_tasks)

    @abstractmethod
    def _compute_power(self, n_tasks: int) -> float:
        """
        Compute power consumption depending on the number of tasks running concurrently.
        :param n_tasks: number of active tasks.
        :return: power consumption (in Watts) of the processing unit.
        """
        pass


T = TypeVar('T')


class DVFSPowerModel(ProcessingUnitPowerModel, ABC, Generic[T]):
    def __init__(self, **kwargs):
        """
        Dynamic Voltage and Frequency Scaling-based processing unit power model.
        :param dict[float, T] dvfs_table: {maximum utilization: DVFS configuration}
                                          The maximum utilization 1 is mandatory and must be in the table.
        :param kwargs: any additional configuration parameter.
        """
        super().__init__(**kwargs)
        dvfs: dict[float, T] = kwargs['dvfs_table']
        if 1 not in dvfs:
            raise ValueError(f'DVFS table must contain a configuration for utilization smaller than or equal to 1')
        dvfs_table: list[tuple[float, T]] = list()
        for utilization, configuration in dvfs.items():
            if 0 > utilization > 1:
                raise ValueError(f'DVFS utilization ({utilization}) must be between 0 and 1')
            dvfs_table.append((utilization, configuration))
        dvfs_table.sort()
        for _, configuration in dvfs_table:
            self.check_dvfs_configuration(configuration)
        self._dvfs_table = dvfs_table

    def _compute_power(self, n_tasks: int) -> float:
        return self.compute_dvfs_power(n_tasks, self.get_dvfs_config(n_tasks))

    def get_dvfs_config(self, n_tasks: int) -> T:
        """
        Returns the DVFS configuration used by the processing unit according to the tasks executed.
        :param n_tasks: number of tasks being executed.
        :return: DVFS configuration
        """
        utilization: float = self.utilization(n_tasks)
        for max_u, configuration in self._dvfs_table:
            if max_u >= utilization:
                return configuration

    @abstractmethod
    def check_dvfs_configuration(self, configuration: T):
        """
        Abstract method to check that a given DVFS configuration has valid parameters.
        :param configuration: DVFS configuration.
        """
        pass

    @abstractmethod
    def compute_dvfs_power(self, n_tasks: int, configuration: T):
        """
        Compute power consumption according to the power model.
        :param n_tasks: number of active tasks.
        :param configuration: current DVFS configuration.
        :return: power consumption (in Watts) of the processing unit.
        """
        pass


class ConstantPowerModel(ProcessingUnitPowerModel):
    def __init__(self, **kwargs):
        """
        Constant power model for processing unit.
        :param float | list[float] power: power consumption (in W) of processing unit. By default, it is set to 0.
                                          If float, power must be greater than or equal to 0.
                                          If list, the length of power must be equal to 1 + max_parallel_tasks.
                                          If list, the first element of power is the power consumption when idling.
                                          If list, all the elements of power must be greater than or equal to 0.
                                          If list, power[i] must be greater than or equal to power[i - 1].
        """
        super().__init__(**kwargs)

        self.power: float | list[float] = kwargs.get('power', 0)
        if isinstance(self.power, list):
            if len(self.power) != self.max_parallel_tasks + 1:
                raise ValueError(f"Length of power ({len(self.power)}) must be 1 + max_parallel_tasks ({1 + self.max_parallel_tasks})")
            for i, t in enumerate(self.power):
                if t < 0:
                    raise ValueError(f'power for {i} tasks ({t}) must be greater than or equal to 0')
                if i > 0 and self.power[i - 1] > t:
                    raise ValueError(f'power for {i} tasks ({t}) is less than power for {i - 1} tasks ({self.power[i - 1]})')
        elif self.power < 0:
            raise ValueError(f'power ({self.power}) must be greater than or equal to 0')

    def _compute_power(self, n_tasks: int) -> float:
        return self.power[n_tasks] if isinstance(self.power, list) else self.power


class IdleActivePowerModel(ProcessingUnitPowerModel):
    def __init__(self, **kwargs):
        """
        Idle-active power model for processing unit.
        If PU not executing any task, the power consumption is idle_power. Otherwise, it is active_power.
        :param float idle_power: power consumption (in Watts) when PU is idling. By default, it is set to 0.
                                 idle_power must be greater than or equal to 0.
        :param float active_power: power consumption (in Watts) when PU is working. By default, it is set to idle_power.
                                   active_power must be greater than or equal to idle_power.
        :param kwargs: any additional configuration parameter.
        """
        super().__init__(**kwargs)
        idle_power: float = kwargs.get('idle_power', 0)
        if idle_power < 0:
            raise ValueError(f'idle_power ({idle_power}) must be greater than or equal to 0')
        active_power: float = kwargs.get('active_power', idle_power)
        if active_power < idle_power:
            raise ValueError(f'active_power ({active_power}) must be greater than/equal to idle_power ({idle_power})')
        self.idle_power: float = idle_power
        self.active_power: float = active_power

    def _compute_power(self, n_tasks: int) -> float:
        return self.active_power if n_tasks > 0 else self.idle_power


class LinearPowerModel(ProcessingUnitPowerModel):
    def __init__(self, **kwargs):
        """
        Linear power consumption model. Power consumption is proportional to PU's utilization:
        P(t) = Pmin + (Pmax - Pmin) * u(t)
            Pmin: minimum power consumption of PU.
            Pmax: maximum power consumption of PU.
            u(t): utilization factor of PU at time t.
        :param float min_power: power consumption (in Watts) of PU when idling. By default, it is set to 0.
                                min_power must be greater than or equal to 0.
        :param float max_power: power consumption (in Watts) of PU when utilization is 1. By default, it is min_power.
                                max_power must be greater than or equal to min_power.
        :param kwargs: any additional configuration parameter.
        """
        super().__init__(**kwargs)
        min_power: float = kwargs.get('min_power', 0)
        if min_power < 0:
            raise ValueError(f'min_power ({min_power}) must be greater than or equal to 0')
        max_power: float = kwargs.get('max_power', min_power)
        if max_power < min_power:
            raise ValueError(f'max_power ({max_power}) must be greater than or equal to min_power ({min_power})')
        self.min_power: float = min_power
        self.max_power: float = max_power

    def _compute_power(self, n_tasks: int) -> float:
        return self.min_power + (self.max_power - self.min_power) * self.utilization(n_tasks)


class StaticDynamicPowerModel(DVFSPowerModel[Tuple[float, float]]):
    def __init__(self, **kwargs):
        """
        Static + Dynamic power model for processing unit.
        P(t) = Pstatic + Pdynamic(t), where Pdynamic(t) is:
            Pdynamic(t) = alpha * V(t)^2 * f(t) * u(t)
                alpha: constant
                V(t): working voltage (in V) at time t (deduced from the DVFS configuration)
                f(t): working frequency (in GHz) at time t (deduced from the DVFS configuration)
                u(t) utilization factor of PU at time t
        :param dict[float, tuple[float, float] dvfs_table: {maximum utilization: {voltage (in V), frequency (ni GHz)}
        :param float static_power: static power consumption.
        :param float alpha: alpha constant. ~ 5
        :param string voltage_dvfs_label: label for taking voltage from the DVFS table.
        :param string frequency_dvfs_label: label for taking frequency from DVFS table.
        """
        if 'dvfs_table' not in kwargs:
            kwargs['dvfs_table'] = {1: (0, 0)}
        super().__init__(**kwargs)
        static_power: float = kwargs.get('static_power', 0)
        if static_power < 0:
            raise ValueError(f'static_power ({static_power}) must be greater than or equal to 0')
        alpha: float = kwargs.get('alpha', 0)
        if alpha < 0:
            raise ValueError(f'alpha ({alpha}) must be greater than or equal to 0')
        self.static_power = static_power
        self.alpha: float = alpha

    def check_dvfs_configuration(self, configuration: tuple[float, float]):
        voltage, frequency = configuration
        if voltage < 0 or frequency < 0:
            raise ValueError(f'voltage ({voltage} and frequency ({frequency} must be greater than or equal to 0')

    def _compute_dvfs_power(self, n_tasks: int, configuration: tuple[float, float]):
        voltage, frequency = configuration
        return self.static_power + self.alpha * (voltage ** 2) * frequency * self.utilization(n_tasks) * 100
