from __future__ import annotations
import datetime
from .optimization.allocation_manager import AllocationManager
from .config.config import MercuryConfig, TransceiverConfig
from .model.model import MercuryModelABC
from .visualization import *
from xdevs.sim import Coordinator


class Mercury:
    def __init__(self, model: MercuryModelABC):
        """
        M&S&O Framework of Fog Computing scenarios for Data Stream Analytics.
        :param model:
        """
        self.allocation_manager: AllocationManager | None = None
        self.model: MercuryModelABC = model

    @property
    def config(self) -> MercuryConfig:
        return self.model.config

    # TODO mover el allocation manager a config?
    def init_allocation_manager(self, data, time_window: float = 60, grid_res: float = 40):
        self.allocation_manager = AllocationManager(data, time_window, grid_res)

    def auto_add_aps(self, prefix: str = 'ap', plot: bool = False,
                     xh_trx: TransceiverConfig = None, acc_trx: TransceiverConfig = None):
        if self.config.gws_config is None:
            raise ValueError('You must first define a configuration for gateways')
        self.allocation_manager.allocate_aps(plot)
        aps = self.allocation_manager.aps
        for i in range(aps.shape[0]):
            x = aps[i, 0]
            y = aps[i, 1]
            ap_location = (x, y)
            self.config.gws_config.add_gateway(f'{prefix}_{i}', ap_location, False, xh_trx, acc_trx)

    def auto_add_edcs(self, n: int = 2, prefix='edc', r_manager_id: str = None, cooler_id: str = None,
                      edc_temp: float = 298, edc_trx: TransceiverConfig = None, plot=False):
        self.allocation_manager.allocate_edcs(opt='n', n=n)
        edcs = self.allocation_manager.edcs
        for i in range(edcs.shape[0]):
            x = edcs[i, 0]
            y = edcs[i, 1]
            edc_location = (x, y)
            self.config.edcs_config.add_edc_config(f'{prefix}_{i}', edc_location, r_manager_id,
                                                   cooler_id, edc_temp, edc_trx)
        if plot:
            self.allocation_manager.plot_scenario()

    def start_simulation(self, time_interv: float = 10000, log_time: bool = False):
        """ Initialize Mercury xDEVS coordinator """
        start_date = datetime.datetime.now()
        if not self.model.built:
            self.model.build()

        self.coordinator = Coordinator(self.model)
        for transducer in self.model.transducers:
            self.coordinator.add_transducer(transducer)
        self.coordinator.initialize()

        finish_date = datetime.datetime.now()
        engine_time = finish_date - start_date
        if log_time:
            print("*********************")
            print(f'It took {engine_time} seconds to create the engine')
            print("*********************")

        start_date = datetime.datetime.now()
        self.coordinator.simulate_time(time_interv=time_interv)
        finish_date = datetime.datetime.now()
        sim_time = finish_date - start_date
        if log_time:
            print("*********************")
            print(f'It took {sim_time} seconds to simulate')
            print("*********************")
        for transducer in self.model.transducers:
            transducer.exit()
        return engine_time, sim_time

    @staticmethod
    def plot_srv_delay(dirname: str, sep: str = ',', client_id: str = None,
                       service_id: str = None, req_type: str = None, alpha: float = 1):
        df = pd.read_csv(f'{dirname}/transducer_srv_report_events.csv', sep=sep)
        if client_id is not None:
            df = df[df['client_id'] == client_id]
        if service_id is not None:
            df = df[df['service_id'] == service_id]
        if req_type is not None:
            df = df[df['req_type'] == req_type]
        plot_service_delay(df['time'], df['t_delay'], client_id, service_id, req_type, alpha)

    @staticmethod
    def plot_edc_power_demand(path: str, sep: str = ',', stacked: bool = False, alpha: float = 1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['edc_id'], df['power_demand'], stacked=stacked, alpha=alpha)

    @staticmethod
    def plot_edc_it_power(path: str, sep: str = ',', stacked: bool = False, alpha: float = 1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['edc_id'], df['it_power'],
                       stacked=stacked, alpha=alpha, nature='Demand (only IT)')

    @staticmethod
    def plot_edc_cooling_power(path: str, sep: str = ',', stacked: bool = False, alpha: float = 1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['edc_id'], df['cooling_power'],
                       stacked=stacked, alpha=alpha, nature='Demand (only Cooling)')

    @staticmethod
    def plot_edc_power_consumption(path: str, sep: str = ',', stacked: bool = False, alpha: float = 1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['consumer_id'], df['power_consumption'],
                       stacked=stacked, alpha=alpha, nature='Consumption')

    @staticmethod
    def plot_edc_power_storage(path: str, sep: str = ',', stacked: bool = False, alpha: float = 1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['consumer_id'], df['power_storage'],
                       stacked=stacked, alpha=alpha, nature='Storage')

    @staticmethod
    def plot_edc_power_generation(path: str, sep: str = ',', stacked: bool = False, alpha: float = 1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['consumer_id'], df['power_generation'],
                       stacked=stacked, alpha=alpha, nature='Generation')

    @staticmethod
    def plot_edc_energy_stored(path: str, sep: str = ',', alpha: float = 1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_energy(df['time'], df['consumer_id'], df['energy_stored'], alpha=alpha)

    @staticmethod
    def plot_network_bw(path: str, sep: str = ',', node_from: str = None, node_to: str = None, alpha: float = 1):
        df = pd.read_csv(path, sep=sep)
        subtitle = None
        if node_from is not None:
            df = df[df['node_from'] == node_from]
            subtitle = f'(from {node_from}'
        if node_to is not None:
            df = df[df['node_to'] == node_to]
            subtitle = f'(to {node_to}' if subtitle is None else f'{subtitle} to {node_to}'
        if subtitle is not None:
            subtitle = f'{subtitle})'
        plot_network_bw(df['time'], df['bandwidth'], df['rate'], df['eff'], subtitle, alpha)
