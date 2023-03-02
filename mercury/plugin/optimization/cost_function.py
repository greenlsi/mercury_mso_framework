from __future__ import annotations
from abc import ABC, abstractmethod
import os
import pandas as pd
from typing import Callable


class CostFunction(ABC):
    def __init__(self, **kwargs):
        """
        Abstract cost function for the decision support system.

        :param map: callable function that modifies the cost after computing.
        :param kwargs: any other implementation-specific parameters.
        """
        self.map: Callable[[float], float] | None = kwargs.get('map')

    def cost(self, base_dir: str) -> float:
        """
        Calls the `_cost` method to compute the cost and, if applies, executes the map function before returning it.

        :param base_dir: path to the directory containing the scenario configuration and results.
        :return: cost of the configuration under study.
        """
        cost = self._cost(base_dir)
        return cost if self.map is None else self.map(cost)

    @abstractmethod
    def _cost(self, base_dir: str) -> float:
        """
        Computes the cost of the scenario.

        :param base_dir: path to the directory containing the scenario configuration and results.
        :return: cost of the configuration under study.
        """
        pass


class DeadlinesCost(CostFunction):
    def _cost(self, base_dir: str) -> float:
        """
        This returns the number of service requests that did not meet their deadline.

        :param base_dir: Path to the folder that contains all the simulation results.
        :return: the total number of unmet deadlines.
        """
        path = os.path.join(base_dir, 'transducer_srv_report_events.csv')
        delay_info = pd.read_csv(path)
        return delay_info['deadline_met'].tolist().count(False)


class EnergyCost(CostFunction):
    def _cost(self, base_dir: str) -> float:
        """
        This sums the accumulated energy cost of every EDC.

        :param base_dir: Path to the folder that contains all the simulation results.
        :return: the accumulated energy cost of all the EDCs.
        """
        path = os.path.join(base_dir, 'transducer_smart_grid_events.csv')
        df = pd.read_csv(path)
        total_acc_cost: float = 0
        for consumer_id, consumer_df in df.groupby('consumer_id'):
            total_acc_cost += consumer_df['acc_cost'].max()
        return total_acc_cost


# TODO add AggregatedCost (cuando estén las factorías)
