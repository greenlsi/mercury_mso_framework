from __future__ import annotations
from mercury.config.edcs import CoolerConfig
from mercury.msg.edcs import CoolerReport


class Cooler:
    def __init__(self, edc_id: str, cooler_config: CoolerConfig, edc_temp: float):
        """
        Edge data center cooler model.
        :param edc_id: ID of the EDC that contains the cooler.
        :param cooler_config: ID of the cooler model.
        :param edc_temp: EDC temperature.
        """
        from mercury.plugin import AbstractFactory, CoolerPowerModel

        self.edc_id: str = edc_id
        self.cooler_config: CoolerConfig = cooler_config
        power_config = {**self.cooler_config.power_config, 'edc_temp': edc_temp}
        self.power_model: CoolerPowerModel = AbstractFactory.create_edc_cooler_pwr(self.cooler_config.power_id,
                                                                                   **power_config)
        self.it_power: float = 0
        self.cooling_power: float = self.power_model.compute_power(self.it_power)
        self.edc_temp: float = edc_temp

    @property
    def total_power(self) -> float:
        return self.it_power + self.cooling_power

    @property
    def pue(self) -> float:
        return self.total_power / self.it_power if self.it_power > 0 else 0

    def compute_power(self, it_power: float) -> float:
        """
        For a given IT power, it returns the cooling power of the cooler.
        :param it_power: IT power consumption.
        :return: cooling power of the cooler.
        """
        return self.power_model.compute_power(it_power)

    def update_cooler(self, it_power: float):
        """
        It computes the cooling power of the cooler and modifies the internal values.
        :param it_power: IT power (in Watts).
        """
        self.it_power = it_power
        self.cooling_power = self.compute_power(self.it_power)

    def cooler_report(self) -> CoolerReport:
        """:return: EDC cooler report"""
        return CoolerReport(self.edc_id, self.cooler_config.cooler_id, self.edc_temp, self.it_power, self.cooling_power)
