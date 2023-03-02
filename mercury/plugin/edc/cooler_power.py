from abc import ABC, abstractmethod
from typing import Callable


class CoolerPowerModel(ABC):
    def __init__(self, **kwargs):
        """
        Edge Data Center cooler power model.
        :param edc_temp: environment temperature of the EDC (in Kelvin).
        :param set_point_temp: target temperature (in Kelvin) to be maintained by the cooler.
        :param kwargs: configuration parameters of the model.
        """
        edc_temp: float = kwargs['edc_temp']
        if edc_temp < 0:
            raise ValueError(f'edc_temp ({edc_temp}) must be greater than or equal to 0')
        set_point_temp: float = max(kwargs.get('set_point_temp', edc_temp), edc_temp)
        self.edc_temp: float = edc_temp
        self.set_point_temp: float = set_point_temp  # TODO a qué temperatura tiene que estar el fluido

    @property
    def t_difference(self) -> float:
        return self.set_point_temp - self.edc_temp

    @abstractmethod
    def compute_power(self, it_power: float) -> float:
        """
        Return the cooling power consumption for a given IT power (in Watts)
        :param it_power: dictionary {pu_id: power (in Watts)} consumed by the IT equipment that has to be dissipated.
        :return: power consumption required for refrigerating the rack (in Watts)
        """
        pass


class ConstantCoolerPowerModel(CoolerPowerModel):
    def __init__(self, **kwargs):
        """
        Constant cooler power consumption model.
        :param float power: Cooling power (in Watts). By default, it is set to 0.
        """
        super().__init__(**kwargs)
        self.power: float = kwargs.get('power', 0)

    def compute_power(self, it_power: float) -> float:
        return self.power


class TwoPhaseImmersionCoolerPowerModel(CoolerPowerModel):
    def __init__(self, **kwargs):
        """
        Two-Phase Immersion cooling system power consumption model.
        :param float density: Density of the fluid (in g/cm^3). By default, it is set to 1 (i.e., water).
        :param float specific_heat: Specific heat of the fluid (in J/gK). By default, it is set to 4.184 (i.e., water).
        :param float t_difference: Desirable temperature difference (in K) between both sides of the pump.
        :param float min_flow_rate: Minimum flow rate (in m^3/h) to be provided by the pump. By default, it is set to 0.
        :param Callable[[float], float] power: Cooling power function. By default, it returns 0.
               cooling_power[W] = f(flow_rate [m^3/h])
        """
        super().__init__(**kwargs)
        self.density: float = kwargs.get('density', 1)
        self.specific_heat: float = kwargs.get('specific_heat', 4.184)
        self.min_flow_rate: float = kwargs.get('min_flow_rate', 0)
        self.power: Callable[[float], float] = kwargs.get('power', lambda x: 0)

    def compute_power(self, it_power: float) -> float:
        """
        Cooling power depends on the required  flow rate, which depends on the IT power.
        :param it_power: IT power (i.e., power to be dissipated).
        :return: cooling power.
        """
        flow_rate = self.min_flow_rate
        if self.t_difference > 0:
            flow_rate = max(flow_rate, it_power / (277.78 * self.density * self.specific_heat * self.t_difference))
        return self.power(flow_rate)
