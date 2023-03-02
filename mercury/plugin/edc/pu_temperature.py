from abc import ABC, abstractmethod


class ProcessingUnitTemperatureModel(ABC):
    def __init__(self, **kwargs):
        """
        Processing unit temperature model.
        :param float edc_temp: temperature (in Kelvin) of the EDC that contains the PU.
        :param kwargs: additional configuration parameters.
        """
        edc_temp: float = kwargs['edc_temp']
        if edc_temp < 0:
            raise ValueError(f'edc_temp ({edc_temp}) must be greater than or equal to 0')
        self.edc_temp: float = edc_temp

    def compute_temperature(self, power: float) -> float:
        return max(self.edc_temp, self._compute_temperature(power))

    @abstractmethod
    def _compute_temperature(self, power: float) -> float:
        """
        Compute temperature according to the temperature model.
        :param power: current power consumption (in Watts).
        :return: temperature (in Kelvin) of the processing unit.
        """
        pass


class ConstantTemperatureModel(ProcessingUnitTemperatureModel):
    def __init__(self, **kwargs):
        """
        Constant temperature model for processing unit.
        :param float temperature: temperature (in Kelvin) of processing unit. It must be greater than or equal to 0.
        :param kwargs: any additional configuration parameter.
        """
        super().__init__(**kwargs)
        temperature: float = kwargs.get('temperature', self.edc_temp)
        if temperature < 0:
            raise ValueError(f'temperature ({temperature}) must be greater than or equal to 0')
        self.temperature: float = temperature

    def _compute_temperature(self, power: float) -> float:
        return self.temperature
