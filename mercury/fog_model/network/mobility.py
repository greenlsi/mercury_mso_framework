import pandas as pd
from xdevs import INFINITY
from typing import Tuple
from abc import ABC, abstractmethod
from ..common.plugin_loader import load_plugins


class NodeLocation:
    def __init__(self, node_id: str, location: Tuple[float, ...]):
        self.node_id = node_id
        self.location = location


class NodeMobility(ABC):
    def __init__(self, **kwargs):
        """

        :param tuple initial_position: Initial position of the node
        """
        self.position = tuple(kwargs.get('initial_position'))

    @abstractmethod
    def get_next_sigma(self, time):
        pass

    @abstractmethod
    def get_location_and_advance(self):
        pass


class NodeMobilityStill(NodeMobility):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_next_sigma(self, time):
        return INFINITY

    def get_location_and_advance(self):
        return self.position


class NodeMobility2DFunction(NodeMobility):
    def __init__(self, **kwargs):
        self.function = kwargs.get('function', lambda x: x)
        self.interval = kwargs.get('interval', (0, 0))
        initial_x = kwargs.get('initial_x', 0)
        assert self.interval[0] <= initial_x <= self.interval[1]
        initial_position = (initial_x, self.function(initial_x))
        self.delta = kwargs.get('delta', 0)
        direction = kwargs.get('direction', 1)
        assert direction in [-1, 1]
        self.direction = direction
        sigma = kwargs.get('sigma', INFINITY)
        assert sigma > 0
        self.sigma = sigma
        super().__init__(initial_position=initial_position)

    def get_next_sigma(self, time):
        return self.sigma - (time % self.sigma)

    def get_location_and_advance(self):
        next_x = self.position[0] + self.delta * self.direction
        if not (self.interval[0] < next_x < self.interval[1]):
            next_x = min(max(self.interval[0], next_x), self.interval[1])
            self.direction *= - 1
        new_location = (next_x, self.function(next_x))
        prev_position = (self.position[0], self.position[1])
        self.position = new_location
        return prev_position


class NodeMobilityHistory(NodeMobility):
    def __init__(self, **kwargs):
        location_history = kwargs.get('history')
        t_start = kwargs.get('t_start', 0)

        history = pd.DataFrame(data=location_history, index=None, columns=['time', 'x', 'y'])
        history = history.sort_values(by='time', ascending=True)
        history['time'] = history['time'] - t_start
        history = history[history['time'] >= 0]
        initial_x = history.iloc[0]['x']
        initial_y = history.iloc[0]['y']
        initial_position = (initial_x, initial_y)

        super().__init__(initial_position=initial_position)

        self.history = history
        self.pointer = 0

    def get_next_sigma(self, time):
        next_pointer = self.pointer + 1
        if next_pointer >= self.history.shape[0]:
            return INFINITY
        else:
            next_time = self.history.iloc[next_pointer]['time']
            return max(next_time - time, 0)

    def get_location_and_advance(self):
        x = self.history.iloc[self.pointer]['x']
        y = self.history.iloc[self.pointer]['y']
        self.pointer += 1
        return x, y


class MobilityFactory:
    def __init__(self):
        self._mobility = dict()
        for key, mobility in load_plugins('mercury.mobility.plugins').items():
            self.register_mobility(key, mobility)

    def register_mobility(self, key: str, mobility: NodeMobility):
        self._mobility[key] = mobility

    def is_mobility_defined(self, key: str) -> bool:
        return key in self._mobility

    def create_mobility(self, key, **kwargs) -> NodeMobility:
        mobility = self._mobility.get(key)
        if not mobility:
            raise ValueError(key)
        return mobility(**kwargs)
