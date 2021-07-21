# import sys; sys.path.append("../..")

import pandas as pd
from typing import Set, Optional
import mercury.logger as logger
from mercury import Mercury
from mercury.config import ResourceManagerConfig, PowerSourceConfig, EnergyStorageConfig
from samples.models.pu_power.rx580_power_model import Rx580PowerModel

stacked = False
alpha = 1

MIN_EPOCH = 1212735600
USE_ALLOCATION_MANAGER = False
USE_SMART_GRID = False

PUS_PER_EDC = 20
N_VEHICLES = 0


def prepare_ues_config(services: Set[str], lifetime_path: str, traces_path: str, t_init: float, max_rows: Optional[int] = None):
    ues_lifetime = pd.read_csv(lifetime_path, sep=';')
    if max_rows is not None and 0 <= max_rows < ues_lifetime.shape[0]:
        ues_lifetime = ues_lifetime.sample(n=max_rows)
    ues_traces = pd.read_csv(traces_path, sep=';')

    ue_configs = dict()
    for index, row in ues_lifetime.iterrows():
        ue_configs[row['cab_id']] = {
            'ue_id': row['cab_id'],
            'services_id': services,
            'radio_antenna': None,
            't_start': row['t_start'] - t_init,
            't_end': row['t_end'] - t_init,
            'mobility_name': 'history',
            'mobility_config': {
                't_column': 'epoch',
                't_init': t_init,
                't_start': row['t_start'] - t_init,
                't_end': row['t_end'] - t_init,
                'history': ues_traces[ues_traces['cab_id'] == row['cab_id']][['epoch', 'x', 'y']]
            }
        }
    return ue_configs


if __name__ == '__main__':

    mercury = Mercury()

    # Set logging if needed
    logger.set_logger_level('INFO')
    logger.add_stream_handler()
    logger.add_file_handler('simulation_info.log')
    logger.add_file_handler('simulation_warning.log', level="WARNING")

    """ PART 1: OBTAINING THE LOCATION OF ALL THE APs AND EDCs IN THE SCENARIO (IF REQUIRED) """
    if USE_ALLOCATION_MANAGER:
        df = pd.read_csv('data/mobility/2008-06-06-harbor-xy-traces.csv', sep=';', index_col=None)
        mercury.init_allocation_manager(df)
        mercury.allocation_manager.plot_grid(pdf_path='scenario_density.pdf')

        mercury.allocation_manager.allocate_aps(plot=True)
        mercury.allocation_manager.allocate_edcs(opt='n', n=3)

        mercury.allocation_manager.plot_scenario(pdf_path='scenario.pdf')

        data_ap = {
            'ap_id': ['ap_{}'.format(i) for i in range(mercury.allocation_manager.aps.shape[0])],
            'x': mercury.allocation_manager.aps[:, 0],
            'y': mercury.allocation_manager.aps[:, 1]
        }
        data_edc = {
            'edc_id': ['edc_{}'.format(i) for i in range(mercury.allocation_manager.edcs.shape[0])],
            'x': mercury.allocation_manager.edcs[:, 0],
            'y': mercury.allocation_manager.edcs[:, 1]
        }
        data_ap = pd.DataFrame(data=data_ap)
        data_edc = pd.DataFrame(data=data_edc)
        print('AP info: {}'.format(data_ap))
        print('EDC info: {}'.format(data_edc))
        data_ap.to_csv('./ap_location.csv', sep=';', index=False)
        data_edc.to_csv('./edc_location.csv', sep=';', index=False)

    """ PART 2: LOADING ALL THE CUSTOM MODELS """
    mercury.fog_model.add_custom_pu_power_model('Rx580', Rx580PowerModel)

    """ PART 3: DEFINING ALL THE UE-RELATED PARAMETERS """
    mercury.fog_model.max_guard_time = 10
    # 3.1: define ADAS service configuration
    mercury.fog_model.define_srv_config(service_id='adas',  # Service ID must be unique
                                        header=0,  # header of any service package
                                        content=1000000,
                                        req_profile_name='periodic',
                                        req_profile_config={'period': 1200},
                                        req_timeout=5,
                                        max_batches=3,
                                        session_profile_name='periodic',
                                        session_profile_config={'period': 1200},
                                        session_timeout=10,
                                        session_duration_name='fixed',
                                        session_duration_config={'duration': 900},
                                        demand_estimator_name='history',
                                        demand_estimator_config={
                                                'history': pd.read_csv('data/demand/mean_friday_demand.csv', sep=';'),
                                                't_column': 'hour',
                                                'estimation_column': 'demand',
                                                't_init': MIN_EPOCH,
                                                'modifiers': {
                                                    'demand': lambda x: x * 1.1,
                                                }
                                        })

    # 3.2: define all the UEs that conform the scenario (it will take a while, there are almost 10,000 UEs)
    ue_configs = prepare_ues_config({'adas'}, 'data/mobility/2008-06-06-harbor-lifetime.csv',
                                    'data/mobility/2008-06-06-harbor-xy-traces.csv', MIN_EPOCH, N_VEHICLES)
    for ue_config in ue_configs.values():
        mercury.fog_model.add_ue_config(**ue_config)

    """ PART 4: DEFINING STANDARD CONFIGURATIONS """
    # Define the Radio Access Network service parameters
    mercury.fog_model.define_rac_config()
    # Define network layer-level packets
    mercury.fog_model.define_network_config()  # Network layer-level header size (in bits)
    # Define edge federation management service parameters
    mercury.fog_model.define_fed_mgmt_config()  # EDC report size (in bits)

    mercury.fog_model.add_xh_config()
    mercury.fog_model.add_radio_config()

    """ PART 5: DEFINING ALL THE SMART GRID PROVIDERS (if applies)"""
    if USE_SMART_GRID:  # TODO define smart grid
        mercury.fog_model.add_smart_grid_energy_provider('provider', 'history', {'history': pd.read_csv('data/smart_grid/electricity_offer.csv')})

    """ PART 6: DEFINING ALL THE EDC-RELATED PARAMETERS """
    edcs = pd.read_csv('./edc_location.csv', sep=";").values

    # 4.1: define Processing Units configurations
    mercury.fog_model.define_pu_type_config(pu_type='Rx580',
                                            services={
                                                'adas': {
                                                    'u_busy': 20,
                                                    'u_idle': 20,   # Computing resources per service session
                                                    't_start': 1,      # Time required for starting a session
                                                    't_stop': 0.2,       # Time required for stopping a session
                                                    't_process': 0.1,    # Time required for processing an operation
                                                }
                                            },
                                            dvfs_table={100: {
                                                'memory_clock': 2000,
                                                'core_clock': 1366
                                            }},
                                            t_on=60,  # Time required for switching on the PU
                                            t_off=10,  # Time required for switching off the PU
                                            pwr_model_name='Rx580',  # We want to use the custom Rx580 power model
                                            pwr_model_config={
                                                'file_path_to_model_and_scalers': '../models/pu_power/rx580_power_model/power_model_rx580',
                                            })

    mercury.fog_model.define_edc_rack_cooler_type('immersion',
                                                  pwr_model_name='static',
                                                  pwr_model_config={
                                                      'power': 15,
                                                  })

    r_manager_config = ResourceManagerConfig(mapping_name='less_it_pwr',  # Sessions to fullest PU
                                             hot_standby_name='full',     # it will be dynamic -> this is temporary
                                             hot_standby_config={'standby': True},
                                             cool_down=1)
    for row in edcs:
        mercury.fog_model.add_edc_config(row[0], (row[1], row[2]), r_manager_config,
                                         {'pu_{}'.format(i): 'Rx580' for i in range(PUS_PER_EDC)}, 'immersion')

        if USE_SMART_GRID:
            mercury.fog_model.add_smart_grid_consumer(row[0], 'provider',
                                                      storage_config=EnergyStorageConfig(
                                                          capacity=2280,
                                                          max_charge_rate=1200,
                                                          max_discharge_rate=-1200,
                                                          initial_charge=0
                                                      ),  # TODO
                                                      consumption_manager_name='min_max',  # TODO
                                                      consumption_manager_config={
                                                          'max_charge_cost': 20e-6,
                                                          'min_discharge_cost': 35e-6,
                                                      },
                                                      sources_config={
                                                          'pv_system': PowerSourceConfig(
                                                              source_type='history',
                                                              source_config={
                                                                  'history': pd.read_csv(f'data/smart_grid/generation_{row[0]}.csv')
                                                              }
                                                          )
                                                      })


    """ PART 6: DEFINING ALL THE AP-RELATED PARAMETERS """
    aps = pd.read_csv('./ap_location.csv', sep=';').values
    for row in aps:
        mercury.fog_model.add_ap_config(row[0], (row[1], row[2]))

    # TODO define CNFs configuration
    mercury.fog_model.add_core_config((0, 0), sdn_strategy_name='smart_grid_closest')
    mercury.fog_model.add_edge_fed_config()  # By default congestion is 100% and no slicing is applied
    mercury.fog_model.add_efc_config(demand_share_name='trend', dyn_hot_standby_name='session', cool_down=900)

    #TODO add transducers
    mercury.fog_model.add_transducers('transducer', 'csv', output_dir='res/')

    # TODO build model and run simulation
    mercury.fog_model.build(lite=True)
    mercury.fog_model.start_simulation(time_interv=86400, log_time=True)  # simulate 24 hours
