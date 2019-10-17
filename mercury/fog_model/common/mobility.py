from xdevs import INFINITY
from abc import ABC, abstractmethod
import pandas as pd


class NewLocation:
    def __init__(self, node_id, location):
        self.node_id = node_id
        self.location = location


class UEMobilityConfiguration(ABC):
    def __init__(self, initial_position):
        self.position = initial_position

    @abstractmethod
    def get_next_sigma(self, time):
        pass

    @abstractmethod
    def get_location_and_advance(self):
        pass


class UEMobilityHistory(UEMobilityConfiguration):
    def __init__(self, t_start, location_history):
        history = pd.DataFrame(data=location_history, index=None, columns=['time', 'x', 'y'])
        history = history.sort_values(by='time', ascending=True)
        history['time'] = history['time'] - t_start
        history = history[history['time'] >= 0]
        initial_x = history.iloc[0]['x']
        initial_y = history.iloc[0]['y']
        initial_position = (initial_x, initial_y)
        super().__init__(initial_position)
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


class UEMobilityStill(UEMobilityConfiguration):
    def __init__(self, position):
        super().__init__(position)

    def get_next_sigma(self, time):
        return INFINITY

    def get_location_and_advance(self):
        return self.position


class UEMobilityStraightLine(UEMobilityConfiguration):
    def __init__(self, initial_position, line_range=(0, 100), velocity_vector=10, time_step=5):

        if line_range[0] > line_range[1]:
            raise ValueError('Line range values are incorrect.')
        self.line_range = line_range

        if initial_position is None:
            initial_position = (line_range[0], 0)
        if not line_range[0] <= initial_position[0] <= line_range[1]:
            raise ValueError('Initial position must be within the line range')
        super().__init__(initial_position)

        self.velocity_vector = velocity_vector
        self.time_step = time_step

    def get_next_sigma(self, time):
        return self.time_step - (time % self.time_step)

    def get_location_and_advance(self):
        new_location = [self.position[0] + self.velocity_vector, 0]
        if not (self.line_range[0] < new_location[0] < self.line_range[1]):
            new_location[0] = min(max(self.line_range[0], new_location[0]), self.line_range[1])
            self.velocity_vector *= - 1
        prev_position = (self.position[0], self.position[1])
        self.position = tuple(new_location)
        return prev_position
