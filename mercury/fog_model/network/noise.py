from abc import ABC, abstractmethod
from typing import Union
from ..common.plugin_loader import load_plugins

from scipy.constants import k


class Noise(ABC):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def noise_density(self, link) -> Union[float, None]:
        """Returns noise spectral density (in W/Hz)"""
        pass

    @abstractmethod
    def noise_watts(self, link, bandwidth: float) -> float:
        """Returns noise power (in W)"""
        pass


class ThermalNoise(Noise):
    def __init__(self, **kwargs):
        """
        Johnson-Nyquist noise model
        :param float temperature: temperature of the link (in Kelvin). By default, it is set to 298 K
        """
        super().__init__(**kwargs)
        self.temperature = kwargs.get("temperature", 298)

    def noise_density(self, link) -> float:
        """Returns noise spectral density (in W/Hz)"""
        return k * self.temperature

    def noise_watts(self, link, bandwidth: float) -> float:
        """Returns noise power (in W)"""
        density = self.noise_density(link)
        return density * bandwidth


class NoiseFactory:
    def __init__(self):
        self._noise = dict()
        for key, noise in load_plugins('mercury.network.noise.plugins').items():
            self.register_noise(key, noise)

    def register_noise(self, key: str, noise: Noise):
        self._noise[key] = noise

    def is_noise_defined(self, key: str) -> bool:
        return key in self._noise

    def create_noise(self, key, **kwargs) -> Noise:
        noise = self._noise.get(key)
        if not noise:
            raise ValueError(key)
        return noise(**kwargs)
