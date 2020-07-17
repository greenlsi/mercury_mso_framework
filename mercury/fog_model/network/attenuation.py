from abc import ABC, abstractmethod
from math import pow
from ..common.plugin_loader import load_plugins

from scipy.constants import c, pi


def from_db_to_natural(x):
    """Converts from logarithmic to linear"""
    return 0 if x is None else pow(10, x / 10)


class Attenuation(ABC):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def attenuation(self, link, distance: float) -> float:
        """
        Returns attenuation (in W/W) depending on a given distance
        :param link: Link that causes the attenuation
        :param distance: distance"""
        pass


class FreeSpacePathLossAttenuation(Attenuation):
    """ Model of power attenuation in free space """
    def attenuation(self, link, distance: float) -> float:
        frequency = link.frequency
        return 1 if distance == 0 or frequency == 0 else pow((4 * pi * distance * frequency / c), 2)


class FiberLinkAttenuation(Attenuation):
    def __init__(self, **kwargs):
        """
        Model of power attenuation in a fiber link
        :param float loss_factor: Fiber link loss factor (in dB/km)
        :param float splice_loss: Loss (in dB) per each splice in the fiber link
        :param int n_splices: number of splices in the link
        """
        super().__init__(**kwargs)
        self.loss_factor = kwargs.get('loss_factor', 0)
        self.splice_loss = kwargs.get('splice_loss', 0)
        self.n_splices = kwargs.get('n_splices', 0)

    def attenuation(self, link, distance: float) -> float:
        loss_db = self.loss_factor * distance + self.splice_loss * self.n_splices
        return from_db_to_natural(loss_db)


class AttenuationFactory:
    def __init__(self):
        self._attenuation = dict()
        for key, attenuation in load_plugins('mercury.network.attenuation.plugins').items():
            self.register_attenuation(key, attenuation)

    def register_attenuation(self, key: str, attenuation: Attenuation):
        self._attenuation[key] = attenuation

    def is_attenuation_defined(self, key: str) -> bool:
        return key in self._attenuation

    def create_attenuation(self, key, **kwargs) -> Attenuation:
        attenuation = self._attenuation.get(key)
        if not attenuation:
            raise ValueError(key)
        return attenuation(**kwargs)
