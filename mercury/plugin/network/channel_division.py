from abc import ABC, abstractmethod
from typing import Dict


class ChannelDivision(ABC):
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def bandwidth_share(self, nodes_efficiency: Dict[str, float]) -> Dict[str, float]:
        """
        Computes the channel bandwidth division rate for a given amount of connected nodes
        :param nodes_efficiency: Used spectral efficiency for each connected node
        :return: Channel division for every connected node
        """
        pass


class EqualChannelDivision(ChannelDivision):
    def bandwidth_share(self, nodes_efficiency: Dict[str, float]) -> Dict[str, float]:
        n_ues = len(nodes_efficiency)
        return {ue_id: 1/n_ues for ue_id in nodes_efficiency}


class ProportionalChannelDivision(ChannelDivision):
    def bandwidth_share(self, nodes_efficiency: Dict[str, float]) -> Dict[str, float]:
        if not nodes_efficiency:
            return dict()
        inverse = 1 / sum([1 / eff for eff in nodes_efficiency.values()])
        return {ue_id: inverse / eff for ue_id, eff in nodes_efficiency.items()}
