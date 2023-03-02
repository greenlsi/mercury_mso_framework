from __future__ import annotations
import pandas as pd
from abc import ABC, abstractmethod
from collections import deque
from math import inf
from mercury.config.client import ClientConfig, WiredClientConfig, WirelessClientConfig, TransceiverConfig, LinkConfig
from numpy.random import poisson  # We use poisson from numpy as numpy is a dependency of Mercury
from random import gauss, uniform, expovariate
from typing import Any


class ClientGenerator(ABC):
    def __init__(self, **kwargs):
        """
        Client generator abstract class.
        :param list[str] services: list of the IDs of all the services on board of the clients.
        :param dict[str, Any] trx_config: configuration parameters for the client nodes transceiver.
        """
        self.services: set[str] = kwargs['services']
        self.trx_config: TransceiverConfig | None = None
        if 'trx_config' in kwargs:
            self.trx_config = TransceiverConfig(**kwargs['trx_config'])

    @abstractmethod
    def next_t(self) -> float:
        """@return simulation time at which one or more clients must be generated."""
        pass

    @abstractmethod
    def generate_clients(self) -> list[ClientConfig]:
        """@return a list of configurations for new clients to be generated."""
        pass


class ListClientGenerator(ClientGenerator):
    def __init__(self, **kwargs):
        """
        It creates clients according to a list of client configurations.
        :param dict[str, dict[str, Any]] clients: dictionary {client_id: {client configuration parameters}}
        """
        # First, we execute the __init__ method of the ClientGenerator class.
        super().__init__(**kwargs)
        # Now, we create the timeline of client generations
        self.clients_timeline: dict[float, list[ClientConfig]] = dict()
        for client_id, client_config in kwargs.get('clients', dict()).items():
            client_config = self.build_client_config(client_id, client_config)
            t_start = client_config.t_start
            if t_start not in self.clients_timeline:
                self.clients_timeline[t_start] = list()
            self.clients_timeline[t_start].append(client_config)
        # self.events is a double-ended queue with all the simulation instants at which we must create a new client
        self.events: deque[float] = deque(sorted(self.clients_timeline))

    def next_t(self) -> float:
        """Next generation happens at the first element of the events queue"""
        return self.events[0] if self.events else inf

    def generate_clients(self) -> list[ClientConfig]:
        """We clean the events and clients timeline and return the list of new client configurations"""
        return self.clients_timeline.pop(self.events.popleft()) if self.events else list()

    def build_client_config(self, client_id: str, client_config: dict[str, Any]) -> ClientConfig:
        t_start = client_config.get('t_start', 0)
        t_end = client_config.get('t_end', inf)
        gateway_id: str | None = client_config.get('gateway_id')
        # if gateway_id is not None, we assume that it is a wired client
        if gateway_id is not None:
            location = tuple(client_config['location'])
            dl_link_config: LinkConfig | None = None
            if 'dl_link_config' in client_config:
                dl_link_config = LinkConfig(**client_config['dl_link_config'])
            ul_link_config: LinkConfig | None = None
            if 'ul_link_config' in client_config:
                ul_link_config = LinkConfig(**client_config['ul_link_config'])
            return WiredClientConfig(client_id=client_id, gateway_id=gateway_id, services=self.services,
                                     t_start=t_start, t_end=t_end, location=location, trx_config=self.trx_config,
                                     dlink_config=dl_link_config, ulink_config=ul_link_config)
        # Otherwise, we assume that it is a wireless client
        mob_id: str = client_config.get('mob_id', 'still')
        mob_config: dict[str, Any] = client_config.get('mob_config', dict())
        return WirelessClientConfig(client_id=client_id, services=self.services, t_start=t_start, t_end=t_end,
                                    mob_id=mob_id, mob_config=mob_config, trx_config=self.trx_config)


class SyntheticClientGenerator(ClientGenerator):
    def __init__(self, **kwargs):
        # First, we execute the __init__ method of the ClientGenerator class.
        super().__init__(**kwargs)
        self.n_clients: int = 0
        self.generator_id: str = kwargs.get('generator_id', 'synthetic_generator')
        self.t_start: float = kwargs.get('t_start', 0)
        self.t_end: float = kwargs.get('t_end', inf)
        self.instant_generation: bool = kwargs.get('instant_generation', False)
        # Configuration parameters for synthetic client generation
        self.synth_generation_id: str = kwargs.get('synth_generation_id', 'constant')
        self.synth_generation_config: dict[str, Any] = kwargs.get('synth_generation_config', dict())
        SyntheticClientGenerator.check_synth_config(self.synth_generation_id, self.synth_generation_config)
        # Configuration parameters for synthetic client destruction
        self.synth_destruction_id: str = kwargs.get('synth_destruction_id', 'constant')
        self.synth_destruction_config: dict[str, Any] = kwargs.get('synth_destruction_config', dict())
        SyntheticClientGenerator.check_synth_config(self.synth_destruction_id, self.synth_destruction_config)
        # Configuration parameters for synthetic client location box (i.e., boundaries of the scenario generation)
        self.synth_location_box: dict[str, float] = kwargs.get('synth_location_box', dict())
        self.check_synth_location_box()
        # Configuration parameters for synthetic client initial location
        self.synth_location_id: str = kwargs.get('synth_location_id', 'constant')
        self.synth_location_config: dict[str, Any] = kwargs.get('synth_location_config', dict())
        self.check_synth_location_config()
        self.gateway_id: str | None = kwargs.get('gateway_id')
        if self.gateway_id is not None:
            # Configuration parameters for wired clients
            self.dl_link_config: LinkConfig | None = None
            self.ul_link_config: LinkConfig | None = None
            if 'dl_link_config' in kwargs:
                self.dl_link_config = LinkConfig(**kwargs['dl_link_config'])
            if 'ul_link_config' in kwargs:
                self.ul_link_config = LinkConfig(**kwargs['ul_link_config'])
        else:
            # Configuration parameters for wireless clients
            self.synth_mobility_id: str = kwargs.get('synth_mobility_id', 'still')
            self.synth_mobility_config: dict[str, Any] = kwargs.get('synth_mobility_config', dict())
            self.check_synth_mobility_config()
        # next_synth_generation corresponds to the next simulation time when we have to synthesize a new client
        self.next_synth_generation: float = self.t_start
        if not self.instant_generation:
            self.next_synth_generation += self.synthesize_value(self.synth_generation_id, self.synth_generation_config)

    def next_t(self) -> float:
        """Next generation corresponds to next_t if it is less that t_end. Otherwise, the generator is done"""
        return self.next_synth_generation if self.next_synth_generation < self.t_end else inf

    def generate_clients(self) -> list[ClientConfig]:
        """We clean the events and clients timeline and return the list of new client configurations"""
        client_id: str = f'{self.generator_id}_client_{self.n_clients}'
        location = self.synthesize_location()
        t_start = self.next_synth_generation
        t_end = t_start + self.synthesize_value(self.synth_destruction_id, self.synth_destruction_config)
        self.n_clients += 1
        self.next_synth_generation += self.synthesize_value(self.synth_generation_id, self.synth_generation_config)
        # If gateway_id is not None, we return a synthetic wired client
        if self.gateway_id is not None:
            return[WiredClientConfig(client_id=client_id, gateway_id=self.gateway_id, services=self.services,
                                     t_start=t_start, t_end=t_end, location=location, trx_config=self.trx_config,
                                     dlink_config=self.dl_link_config, ulink_config=self.ul_link_config)]
        # Otherwise, re generate a synthetic wireless client
        mob_id, mob_config = self.synthesize_mobility(location)
        return [WirelessClientConfig(client_id=client_id, services=self.services, t_start=t_start, t_end=t_end,
                                     mob_id=mob_id, mob_config=mob_config, trx_config=self.trx_config)]

    @staticmethod
    def check_synth_config(synth_id: str, synth_config: dict[str, Any]):
        if synth_id == 'constant':
            if 'period' not in synth_config:
                raise ValueError('constant synthetic configuration must know the value of period')
            if synth_config['period'] <= 0:
                raise ValueError('period must be greater than 0')
        elif synth_id == 'uniform':
            if 'min_t' not in synth_config:
                raise ValueError('uniform synthetic configuration must know the value of min_t')
            if synth_config['min_t'] <= 0:
                raise ValueError('min_t must be grater than 0')
            if 'max_t' not in synth_config:
                raise ValueError('uniform synthetic configuration must know the value of max_t')
            if synth_config['max_t'] < synth_config['min_t']:
                raise ValueError('max_t must be greater than or equal to min_t')
        elif synth_id == 'gaussian':
            if 'mu' not in synth_config:
                raise ValueError('gaussian synthetic configuration must know the value of mu')
            if synth_config['mu'] <= 0:
                raise ValueError('mu must be greater than 0')
            if synth_config.get('sigma', 0) < 0:
                raise ValueError('sigma must be greater than or equal to 0')
        elif synth_id == 'exponential':
            if 'lambda' not in synth_config:
                raise ValueError('exponential synthetic configuration must know the value of lambda')
            if synth_config['lambda'] <= 0:
                raise ValueError(f'lambda must be greater than 0')
        elif synth_id == 'poisson':
            if 't_interval' not in synth_config:
                raise ValueError('poisson synthetic configuration must know the value of t_interval')
            if synth_config['t_interval'] <= 0:
                raise ValueError('t_interval must be greater than 0')
            if synth_config.get('lambda', 0) < 0:
                raise ValueError(f'lambda must be greater than or equal to 0')
        else:
            raise ValueError(f'unknown synthetic configuration id: {synth_id}')

    @staticmethod
    def synthesize_value(synth_id: str, synth_config: dict[str, Any]) -> float:
        if synth_id == 'constant':
            return synth_config['period']
        elif synth_id == 'uniform':
            return uniform(synth_config['min_t'], synth_config['max_t'])
        elif synth_id == 'gaussian':
            return max(0., gauss(synth_config['mu'], synth_config.get('sigma', 0)))
        elif synth_id == 'exponential':
            return expovariate(synth_config['lambda'])
        elif synth_id == 'poisson':
            return synth_config['t_interval'] * poisson(synth_config.get('lambda', 0))
        raise ValueError(f'unknown synthetic configuration id: {synth_id}')

    def check_synth_location_box(self):
        for coord in 'x', 'y':
            min_coord = self.synth_location_box.get(f'min_{coord}', -inf)
            max_coord = self.synth_location_box.get(f'max_{coord}', inf)
            if not isinstance(min_coord, int) and not isinstance(min_coord, float):
                raise ValueError(f'min_{coord} must be a number')
            if not isinstance(max_coord, int) and not isinstance(max_coord, float):
                raise ValueError(f'max_{coord} must be a number')
            if max_coord < min_coord:
                raise ValueError(f'min_coord must be less than or equal to max_coord')

    def check_synth_location_config(self):
        for coord in 'x', 'y':
            min_box_coord = self.synth_location_box.get(f'min_{coord}', -inf)
            max_box_coord = self.synth_location_box.get(f'max_{coord}', inf)
            if self.synth_location_id == 'constant':
                coord_val = self.synth_location_config.get(coord, 0)
                if min_box_coord > coord_val > max_box_coord:
                    raise ValueError(f'{coord} is outside of the synthetic location box')
            elif self.synth_location_id == 'uniform':
                min_coord_val = self.synth_location_config.get(f'min_{coord}', 0)
                max_coord_val = self.synth_location_config.get(f'max_{coord}', 0)
                if min_coord_val < min_box_coord or min_coord_val > max_box_coord:
                    raise ValueError(f'min_{coord} is outside of the synthetic location box')
                if max_coord_val < min_box_coord or max_coord_val > max_box_coord:
                    raise ValueError(f'max_{coord} is outside of the synthetic location box')
                if max_coord_val < min_coord_val:
                    raise ValueError(f'min_coord must be less than or equal to max_coord')
            elif self.synth_location_id == 'gaussian':
                mu_coord = self.synth_location_config.get(f'mu_{coord}', 0)
                sigma_coord = self.synth_location_config.get(f'sigma_{coord}', 0)
                if mu_coord < min_box_coord or mu_coord > max_box_coord:
                    raise ValueError(f'mu_{coord} is outside of the synthetic location box')
                if sigma_coord < 0:
                    raise ValueError(f'sigma_{coord} must be greater than or equal to 0')
            else:
                raise ValueError(f'unknown synth_location_id ({self.synth_location_id})')

    def check_synth_mobility_config(self):
        if self.synth_mobility_id not in ['still', 'gradient']:
            raise ValueError(f'unknown synth_mobility_id ({self.synth_mobility_id})')

    def synthesize_location(self) -> tuple[float, ...]:
        location: list[float] = list()
        for coord in 'x', 'y':
            if self.synth_location_id == 'constant':
                location.append(self.synth_location_config.get(coord, 0))
            elif self.synth_location_id == 'uniform':
                min_coord = self.synth_location_config.get(f'min_{coord}', 0)
                max_coord = self.synth_location_config.get(f'max_{coord}', 0)
                location.append(uniform(min_coord, max_coord))
            elif self.synth_location_id == 'gaussian':
                min_box_coord = self.synth_location_box.get(f'min_{coord}', -inf)
                max_box_coord = self.synth_location_box.get(f'max_{coord}', inf)
                mu_coord = self.synth_location_config.get(f'mu_{coord}', 0)
                sigma_coord = self.synth_location_config.get(f'sigma_{coord}', 0)
                # If the location is outside the location box, we "fix" it (gaussian distributions are tricky)
                location.append(max(min_box_coord, min(max_box_coord, gauss(mu_coord, sigma_coord))))
            else:
                raise ValueError(f'unknown synth_location_id ({self.synth_location_id})')
        return tuple(location)

    def synthesize_mobility(self, initial_location: tuple[float, ...]) -> tuple[str, dict[str, Any]]:
        if self.synth_mobility_id == 'still':
            return 'still', {'location': initial_location}
        elif self.synth_mobility_id == 'gradient':
            return 'gradient', {**self.synth_mobility_config,
                                'initial_location': initial_location,
                                'synth_location_box': self.synth_location_box}
        raise ValueError(f'unknown synth_mobility_id ({self.synth_mobility_id})')


class HistoryClientGenerator(ClientGenerator, ABC):
    def __init__(self, **kwargs):
        """
        History file-based client generator abstract class. It has one file called lifetime CSV file.
        Lifetime CSV file must have these columns:
        CLIENT_ID: it corresponds to the ID of new clients
        T_START: it corresponds to the simulation time at which the client must be created.
        T_END: it corresponds to the simulation time at which the client must be removed.

        :param str lifetime_path: path to the lifetime CSV file.
        :param str lifetime_sep: character used in the lifetime CSV file to separate columns. By default, it is set to ','.
        :param str lifetime_client_id_column: column of the lifetime CSV for client IDs. By default, it is 'client_id'.
        :param str lifetime_t_start_column: column of the lifetime CSV for client start time. By default, it is 't_start'.
        :param str lifetime_t_end_column: column of the lifetime CSV for client end time. By default, it is 't_end'.
        :param float t_init: it corresponds to the time that we consider 0. By default, it is set to 0.
        :param float t_start: minimum start time to be considered. Clients that must be generated before t_start are discarded. By default, it is set to t_init.
        :param float t_end: maximum end time to be considered. Clients that must be deleted after t_end are discarded. By default, it is set to infinity.
        :param int max_n_clients: maximum number of clients to be generated. By default, it is None (i.e., no maximum)
        """
        # First, we execute the __init__ method of the ClientGenerator class.
        super().__init__(**kwargs)
        # Then, we generate the lifetime dataframe
        lifetime_path: str = kwargs['lifetime_path']
        lifetime_sep: str = kwargs.get('lifetime_sep', ',')
        self.clients_lifetime: pd.DataFrame = pd.read_csv(lifetime_path, sep=lifetime_sep)
        # Then, we obtain the column names for client IDs, start time, and stop time
        self.lifetime_client_id_column: str = kwargs.get('lifetime_client_id_column', 'client_id')
        self.lifetime_t_start_column: str = kwargs.get('lifetime_t_start_column', 't_start')
        self.lifetime_t_end_column: str = kwargs.get('lifetime_t_end_column', 't_end')
        # We filter the data frame to remove invalid rows:
        self.t_init: float = kwargs.get('t_init', 0)
        self.t_start: float = kwargs.get('t_start', self.t_init)
        self.t_end: float = kwargs.get('t_end', inf)
        max_n_clients: float | None = kwargs.get('max_n_clients')
        #    We remove those clients out of the time window
        self.clients_lifetime = self.clients_lifetime[self.clients_lifetime[self.lifetime_t_start_column] >= self.t_start]
        self.clients_lifetime = self.clients_lifetime[self.clients_lifetime[self.lifetime_t_end_column] <= self.t_end]
        #    If needed, we remove clients to stick to the maximum number of clients
        if max_n_clients is not None and 0 <= max_n_clients < self.clients_lifetime.shape[0]:
            self.clients_lifetime = self.clients_lifetime.sample(n=max_n_clients)
        # After this, we unbias time columns by subtracting the t_init thing
        self.clients_lifetime[self.lifetime_t_start_column] = self.clients_lifetime[self.lifetime_t_start_column] - self.t_init
        self.clients_lifetime[self.lifetime_t_end_column] = self.clients_lifetime[self.lifetime_t_end_column] - self.t_init
        # Now, we create the timeline of client generations
        self.clients_timeline: dict[float, list[ClientConfig]] = dict()
        for index, row in self.clients_lifetime.iterrows():
            client_config = self.build_client_config(row)
            t_start = row[self.lifetime_t_start_column]
            if t_start not in self.clients_timeline:
                self.clients_timeline[t_start] = list()
            self.clients_timeline[t_start].append(client_config)
        # self.events is a double-ended queue with all the simulation instants at which we must create a new client
        self.events: deque[float] = deque(sorted(self.clients_timeline))

    @abstractmethod
    def build_client_config(self, row: pd.Series) -> ClientConfig:
        """We produce the client configuration from a client configuration in the lifetime CSV"""
        pass

    def next_t(self) -> float:
        """Next generation happens at the first element of the events queue"""
        return self.events[0] if self.events else inf

    def generate_clients(self) -> list[ClientConfig]:
        """We clean the events and clients timeline and return the list of new client configurations"""
        return self.clients_timeline.pop(self.events.popleft()) if self.events else list()


class HistoryWiredClientGenerator(HistoryClientGenerator):
    def __init__(self, **kwargs):
        """
        This class considers that all the clients in the lifetime CSV file are Wired. The lifetime CSV file must have the following additional columns:
        X: the x coordinate of the client location.
        Y: the y coordinate of the client location.
        GATEWAY_ID: the ID of the gateway used by the client to connect to the network.

        :param str lifetime_x_column: column of the lifetime CSV for the x coordinate of clients. By default, it is 'x'.
        :param str lifetime_y_column: column of the lifetime CSV for the y coordinate of clients. By default, it is 'y'.
        :param str lifetime_gateway_id_column: column of the lifetime CSV for the gateway of clients. By default, it is 'gateway_id'.
        :param dict[str, Any] dl_link_config: configuration parameters for the downlinks from gateways to clients.
        :param dict[str, Any] ul_link_config: configuration parameters for the uplinks from clients to gateways.
        """
        # First, we obtain the column names for the additional columns (x, y, and gateway_id)
        self.lifetime_x_column: str = kwargs.get('lifetime_x_column', 'x')
        self.lifetime_y_column: str = kwargs.get('lifetime_y_column', 'y')
        self.lifetime_gateway_id_column: str = kwargs.get('lifetime_gateway_id_column', 'gateway_id')
        # Then, we check if there are any custom downlink and uplink configurations
        self.dl_link_config: LinkConfig | None = None
        if 'dl_link_config' in kwargs:
            self.dl_link_config = LinkConfig(**kwargs['dl_link_config'])
        self.ul_link_config: LinkConfig | None = None
        if 'ul_link_config' in kwargs:
            self.ul_link_config = LinkConfig(**kwargs['ul_link_config'])
        # Finally, we call the __init__ method of HistoryClientGenerator class
        super().__init__(**kwargs)

    def build_client_config(self, row: pd.Series) -> WiredClientConfig:
        return WiredClientConfig(client_id=row[self.lifetime_client_id_column],
                                 gateway_id=row[self.lifetime_gateway_id_column], services=self.services,
                                 t_start=row[self.lifetime_t_start_column], t_end=row[self.lifetime_t_end_column],
                                 location=tuple([row[self.lifetime_x_column], row[self.lifetime_y_column]]),
                                 trx_config=self.trx_config, dlink_config=self.dl_link_config,
                                 ulink_config=self.ul_link_config)


class HistoryWirelessClientGenerator(HistoryClientGenerator):
    clients_config: dict[str, WirelessClientConfig]

    def __init__(self, **kwargs):
        """
        This class considers that all the clients in the lifetime CSV file are Wireless.
        It expects an additional mobility traces CSV file must with the following columns:
        CLIENT_ID: ID of the client that changes its location.
        TIME: time at which the client changes its location.
        X: the x coordinate of the client location.
        Y: the y coordinate of the client location.

        :param str mobility_path: path to the mobility traces CSV file.
        :param str mobility_sep: character used in the mobility traces CSV file to separate columns. By default, it is set to ','.
        :param str mobility_client_id_column: column of the mobility CSV for the ID of clients. By default, it is 'client_id'.
        :param str mobility_time_column: column of the mobility CSV for the time. By default it is set to 'time'.
        :param str mobility_x_column: column of the mobility CSV for the x coordinate of clients. By default, it is 'x'.
        :param str mobility_y_column: column of the mobility CSV for the y coordinate of clients. By default, it is 'y'.
        """
        # First we parse the data frame with mobility traces
        mobility_path: str = kwargs['mobility_path']
        mobility_sep: str = kwargs.get('mobility_sep', ',')
        self.clients_mobility: pd.DataFrame = pd.read_csv(mobility_path, sep=mobility_sep)
        # We also obtain the relevant column IDs of the mobility dataframe
        self.mobility_client_id_column: str = kwargs.get('mobility_client_id_column', 'client_id')
        self.mobility_time_column: str = kwargs.get('mobility_time_column', 'time')
        self.mobility_x_column: str = kwargs.get('mobility_x_column', 'x')
        self.mobility_y_column: str = kwargs.get('mobility_y_column', 'y')
        # we unbias time columns by subtracting the t_init thing
        t_init: float = kwargs.get('t_init', 0)
        self.clients_mobility[self.mobility_time_column] = self.clients_mobility[self.mobility_time_column] - t_init
        # Finally, we call the super().__init__ function of the HistoryClientGenerator class.
        super().__init__(**kwargs)

    def build_client_config(self, row: pd.Series) -> WirelessClientConfig:
        # we get mobility traces from the target client
        client_id = row[self.lifetime_client_id_column]
        mobility_history = self.clients_mobility[self.clients_mobility[self.mobility_client_id_column] == client_id]
        return WirelessClientConfig(client_id=client_id, services=self.services,
                                    t_start=row[self.lifetime_t_start_column], t_end=row[self.lifetime_t_end_column],
                                    mob_id='history', mob_config={'t_column': self.mobility_time_column,
                                                                  't_init': 0,  # Time is already unbiased
                                                                  't_start': row[self.lifetime_t_start_column],
                                                                  't_end': row[self.lifetime_t_end_column],
                                                                  'history': mobility_history},
                                    trx_config=self.trx_config)
