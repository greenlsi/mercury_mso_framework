from typing import Dict, Optional, Tuple
from mercury.config.edcs import CoolerConfig
from mercury.msg.edcs import CoolerReport


class EdgeDataCenterCooler:  # TODO enable division of PUs into multiple coolers
    def __init__(self, edc_id: str, cooler_config: CoolerConfig, base_temp: float):
        """
        Edge Data Center cooler model.
        :param edc_id: ID of the EDC that contains the rack
        :param cooler_config: configuration parameters of the rack cooler
        :param base_temp: base temperature (i.e., cooler set point)
        """
        from mercury.plugin import AbstractFactory, EdgeDataCenterCoolerPowerModel, EdgeDataCenterCoolerTemperatureModel

        self.edc_id: str = edc_id
        self.cooler_type: str = cooler_config.cooler_type

        self.power_model: Optional[EdgeDataCenterCoolerPowerModel] = None
        power_model_name = cooler_config.power_name
        power_model_config = cooler_config.power_config
        if power_model_name is not None:
            self.power_model = AbstractFactory.create_edc_cooler_pwr(power_model_name, **power_model_config)

        self.temp_model: Optional[EdgeDataCenterCoolerTemperatureModel] = None
        temp_model_name = cooler_config.temp_name
        temp_model_config = cooler_config.temp_config
        if temp_model_name is not None:
            self.temp_model = AbstractFactory.create_edc_cooler_temp(temp_model_name, **temp_model_config)

        self.it_power: float = 0
        self.cooling_power: float = 0
        self.temp: float = base_temp
        self.base_temp: float = base_temp

    def predict_rack_temp(self, pu_temps: Dict[str, float]) -> float:
        """
        returns a prediction of the temperature of the rack. It does not modify internal values of the cooler
        :param pu_temps: list containing the temperature of each PU within the rack to be considered for the prediction
        :return: prediction of the temperature of the rack
        """
        if self.temp_model is not None:
            return self.temp_model.compute_cooler_temperature(pu_temps)
        else:
            return self.base_temp

    def predict_cooling_power(self, it_power: Dict[str, float]) -> float:
        """
        returns a prediction of the cooling power of the rack. It does not modify internal values of the cooler
        :param it_power: IT power consumption of each PU to be considered for the prediction
        :return: prediction of the cooling power of the rack.
        """
        if self.power_model is not None:
            return self.power_model.compute_cooling_power(it_power)
        else:
            return 0

    def predict_temperature_and_power(self, temps: Dict[str, float], powers: Dict[str, float]) -> Tuple[float, float]:
        """
        returns prediction of both temperature and cooling power consumption of the EDC.
        :param temps: dictionary containing the temperature (in Kelvin) of each PU to be considered for the prediction.
        :param powers: dictionary containing the power (in Watts) of each PU to be considered for the prediction.
        :return: prediction of both temperature and cooling power consumption of the rack.
        """
        temp = self.predict_rack_temp(temps)
        cooling = self.predict_cooling_power(powers)
        return temp, cooling

    def refresh_cooler(self, temps: Dict[str, float], powers: Dict[str, float]):
        """
        Using the prediction function, this method modifies the internal values (i.e., they are not predictions anymore)
        :param temps: dictionary containing the temperature (in Kelvin) of each PU.
        :param powers: dictionary containing the power (in Watts) of each PU.
        """
        self.it_power = sum(power for power in powers.values())
        self.temp, self.cooling_power = self.predict_temperature_and_power(temps, powers)

    def get_cooler_report(self) -> CoolerReport:
        return CoolerReport(self.edc_id, self.cooler_type, self.temp, self.it_power, self.cooling_power)
