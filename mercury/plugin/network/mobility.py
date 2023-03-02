from __future__ import annotations
import pandas as pd
from abc import ABC
from math import inf
from numpy.random import poisson  # We use poisson from numpy as numpy is a dependency of Mercury
from random import gauss, uniform, expovariate
from typing import Any, Tuple
from ..common.event_generator import EventGenerator, DiracDeltaGenerator, EventHistoryGenerator


class NodeMobility(EventGenerator[Tuple[float, ...]], ABC):
    @property
    def location(self) -> Tuple[float, ...]:
        return self.last_val


class StillNodeMobility(NodeMobility, DiracDeltaGenerator[Tuple[float, ...]]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, initial_val=kwargs['location'])
        assert self.location is not None


class GradientNodeMobility(NodeMobility):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, initial_val=kwargs['initial_location'])
        # Configuration parameters for synthetic client location box (i.e., boundaries of the scenario generation)
        self.synth_location_box: dict[str, float] = kwargs.get('synth_location_box', dict())
        self.check_synth_location_box()

        # Configuration parameters for synthetic client generation
        self.synth_timestep_id: str = kwargs.get('synth_timestep_id', 'constant')
        self.synth_timestep_config: dict[str, Any] = kwargs.get('synth_timestep_config', dict())
        self.check_synth_timestep_config()

        # Configuration parameters for trajectory gradient
        synth_gradient_id: str = kwargs.get('synth_gradient_id', 'constant')
        synth_gradient_config: dict[str, Any] = kwargs.get('synth_gradient_config', dict())
        self.check_synth_location_vector_config(synth_gradient_id, synth_gradient_config)
        self.gradient = list(self.generate_location_vector(synth_gradient_id, synth_gradient_config))
        # We also make it random the initial direction
        for i in range(len(self.gradient)):
            if uniform(0, 1) > 0.5:
                self.gradient[i] = -self.gradient[i]

        # Configuration parameters for spurious variations in trajectory
        self.synth_spurious_id: str = kwargs.get('synth_spurious_id', 'constant')
        self.synth_spurious_config: dict[str, Any] = kwargs.get('synth_spurious_config', dict())
        self.check_synth_location_vector_config(self.synth_spurious_id, self.synth_spurious_config)

    def check_synth_location_box(self):
        location = self.location
        for coord, index in ('x', 0), ('y', 1):
            min_coord = self.synth_location_box.get(f'min_{coord}', -inf)
            max_coord = self.synth_location_box.get(f'max_{coord}', inf)
            if not isinstance(min_coord, int) and not isinstance(min_coord, float):
                raise ValueError(f'min_{coord} must be a number')
            if not isinstance(max_coord, int) and not isinstance(max_coord, float):
                raise ValueError(f'max_{coord} must be a number')
            if max_coord < min_coord:
                raise ValueError(f'min_coord must be less than or equal to max_coord')
            if location[index] < min_coord or location[index] > max_coord:
                raise ValueError(f'initial location is out of the location box')

    def check_synth_timestep_config(self):
        if self.synth_timestep_id == 'constant':
            if 'period' not in self.synth_timestep_config:
                raise ValueError('constant synthetic configuration must know the value of period')
            if self.synth_timestep_config['period'] <= 0:
                raise ValueError('period must be greater than 0')
        elif self.synth_timestep_id == 'uniform':
            if 'min_t' not in self.synth_timestep_config:
                raise ValueError('uniform synthetic configuration must know the value of min_t')
            if self.synth_timestep_config['min_t'] <= 0:
                raise ValueError('min_t must be grater than 0')
            if 'max_t' not in self.synth_timestep_config:
                raise ValueError('uniform synthetic configuration must know the value of max_t')
            if self.synth_timestep_config['max_t'] < self.synth_timestep_config['min_t']:
                raise ValueError('max_t must be greater than or equal to min_t')
        elif self.synth_timestep_id == 'gaussian':
            if 'mu' not in self.synth_timestep_config:
                raise ValueError('gaussian synthetic configuration must know the value of mu')
            if self.synth_timestep_config['mu'] <= 0:
                raise ValueError('mu must be greater than 0')
            if self.synth_timestep_config.get('sima', 0) < 0:
                raise ValueError('sigma must be greater than or equal to 0')
        elif self.synth_timestep_id == 'exponential':
            if 'lambda' not in self.synth_timestep_config:
                raise ValueError('exponential synthetic configuration must know the value of lambda')
            if self.synth_timestep_config['lambda'] <= 0:
                raise ValueError(f'lambda must be greater than 0')
        elif self.synth_timestep_id == 'poisson':
            if 't_interval' not in self.synth_timestep_config:
                raise ValueError('poisson synthetic configuration must know the value of t_interval')
            if self.synth_timestep_config['t_interval'] <= 0:
                raise ValueError('t_interval must be greater than 0')
            if self.synth_timestep_config.get('lambda', 0) < 0:
                raise ValueError(f'lambda must be greater than or equal to 0')
        else:
            raise ValueError(f'unknown synthetic configuration id: {self.synth_timestep_id}')

    @staticmethod
    def check_synth_location_vector_config(synth_id: str, synth_config: dict[str, Any]):
        for coord in 'x', 'y':
            if synth_id == 'uniform':
                min_coord_val = synth_config.get(f'min_{coord}', 0)
                max_coord_val = synth_config.get(f'max_{coord}', 0)
                if max_coord_val < min_coord_val:
                    raise ValueError(f'min_coord must be less than or equal to max_coord')
            elif synth_id == 'gaussian':
                sigma_coord = synth_config.get(f'sigma_{coord}', 0)
                if sigma_coord < 0:
                    raise ValueError(f'sigma_{coord} must be greater than or equal to 0')
            elif synth_id != 'constant':
                raise ValueError(f'unknown synth_id ({synth_id})')

    def _compute_next_ta(self) -> float:
        if self.synth_timestep_id == 'constant':
            return self.synth_timestep_config['period']
        elif self.synth_timestep_id == 'uniform':
            return uniform(self.synth_timestep_config['min_t'], self.synth_timestep_config['max_t'])
        elif self.synth_timestep_id == 'gaussian':
            return max(0., gauss(self.synth_timestep_config['mu'], self.synth_timestep_config.get('sigma', 0)))
        elif self.synth_timestep_id == 'exponential':
            return expovariate(self.synth_timestep_config['lambda'])
        elif self.synth_timestep_id == 'poisson':
            return self.synth_timestep_config['t_interval'] * poisson(self.synth_timestep_config.get('lambda', 0))
        raise ValueError(f'unknown synth_timestep_id: {self.synth_timestep_id}')

    def _compute_next_val(self) -> Tuple[float, ...]:
        spurious = self.generate_location_vector(self.synth_spurious_id, self.synth_spurious_config)
        new_location = [sum(coord) for coord in zip(self.location, self.gradient, spurious)]
        for coord, i in ('x', 0), ('y', 1):
            min_box_coord = self.synth_location_box.get(f'min_{coord}', -inf)
            max_box_coord = self.synth_location_box.get(f'max_{coord}', inf)
            if new_location[i] > max_box_coord:
                new_location[i] = max_box_coord
                self.gradient[i] = -self.gradient[i]
            if new_location[i] < min_box_coord:
                new_location[i] = min_box_coord
                self.gradient[i] = -self.gradient[i]
        return tuple(new_location)

    @staticmethod
    def generate_location_vector(synth_id: str, synth_config: dict[str, Any]) -> Tuple[float, ...]:
        location_vector: list[float] = list()
        for coord in 'x', 'y':
            if synth_id == 'constant':
                location_vector.append(synth_config.get(coord, 0))
            elif synth_id == 'uniform':
                min_coord = synth_config.get(f'min_{coord}', 0)
                max_coord = synth_config.get(f'max_{coord}', 0)
                location_vector.append(uniform(min_coord, max_coord))
            elif synth_id == 'gaussian':
                mu_coord = synth_config.get(f'mu_{coord}', 0)
                sigma_coord = synth_config.get(f'sigma_{coord}', 0)
                location_vector.append(gauss(mu_coord, sigma_coord))
            else:
                raise ValueError(f'unknown synth_config ({synth_config})')
        return tuple(location_vector)


class NodeMobility2DFunction(NodeMobility):
    def __init__(self, **kwargs):
        self.function = kwargs.get('function', lambda x: x)
        self.interval = kwargs.get('interval', (0, 0))
        initial_x = kwargs.get('initial_x', self.interval[0])
        assert self.interval[0] <= initial_x <= self.interval[1]
        initial_location = (initial_x, self.function(initial_x))
        self.delta = kwargs.get('delta', 0)
        direction = kwargs.get('direction', 1)
        assert direction in [-1, 1]
        self.direction = direction
        sigma = kwargs.get('sigma', inf)
        assert sigma > 0
        self.sigma = sigma
        super().__init__(**kwargs, initial_val=initial_location)

    def _compute_next_val(self) -> Tuple[float, ...]:
        next_x = self.location[0] + self.delta * self.direction
        if not (self.interval[0] < next_x < self.interval[1]):
            next_x = min(max(self.interval[0], next_x), self.interval[1])
            self.direction *= - 1
        return next_x, self.function(next_x)

    def _compute_next_ta(self) -> float:
        return self.sigma


class HistoryNodeMobility(NodeMobility, EventHistoryGenerator[Tuple[float, ...]]):
    def __init__(self, **kwargs):
        self.x_column = kwargs.get('x_column', 'x')
        self.y_column = kwargs.get('y_column', 'y')
        super().__init__(**kwargs)
        for column in (self.x_column, self.y_column):
            if not self.history_buffer.column_exists(column):
                raise ValueError(f"dataframe does not have the mandatory column {column}")

    def _pd_series_to_val(self, series: pd.Series) -> [Tuple[float, ...]]:
        return series[self.x_column].item(), series[self.y_column].item()
