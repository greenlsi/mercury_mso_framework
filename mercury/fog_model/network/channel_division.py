from abc import ABC, abstractmethod
from typing import Any, Tuple, Dict
from ..common.plugin_loader import load_plugins


class ChannelDivision(ABC):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def bandwidth_share(self, nodes_efficiency: Dict[str, Tuple[Any, float]]) -> Dict[str, float]:
        """
        Computes the channel bandwidth division rate for a given amount of connected nodes
        :param nodes_efficiency: Used spectral efficiency for each connected node
        :return: Channel division for every connected node
        """
        pass


class EqualChannelDivision(ChannelDivision):
    def bandwidth_share(self, nodes_efficiency: Dict[str, Tuple[Any, float]]) -> Dict[str, float]:
        n_ues = len(nodes_efficiency)
        return {ue_id: 1/n_ues for ue_id in nodes_efficiency}


class ProportionalChannelDivision(ChannelDivision):
    def bandwidth_share(self, nodes_efficiency: Dict[str, Tuple[Any, float]]) -> Dict[str, float]:
        if not nodes_efficiency:
            return dict()
        inverse = 1 / sum([1 / eff[1] for eff in nodes_efficiency.values()])
        return {ue_id: inverse / eff[1] for ue_id, eff in nodes_efficiency.items()}


class ChannelDivisionFactory:
    def __init__(self):
        self._division = dict()
        for key, division in load_plugins('mercury.network.channel_division.plugins').items():
            self.register_division(key, division)

    def register_division(self, key: str, division: ChannelDivision):
        self._division[key] = division

    def is_division_defined(self, key: str) -> bool:
        return key in self._division

    def create_division(self, key, **kwargs) -> ChannelDivision:
        division = self._division.get(key)
        if not division:
            raise ValueError(key)
        return division(**kwargs)
