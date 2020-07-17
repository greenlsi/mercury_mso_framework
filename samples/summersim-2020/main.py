import pandas as pd
from mercury import Mercury, LinkConfiguration, TransceiverConfiguration, RadioConfiguration
from samples.models.pu_power.rx580_power_model import Rx580PowerModel


# Access Points configuration
ap_location_file = './data/summersim_2020_ap_location.csv'

# Edge Data Center management configuration
edc_location_file = './data/summersim_2020_edc_location.csv'
hw_dvfs_mode = False
gpus_per_edc = 10
max_start_stop = 1
n_hot_standby = 2
hw_power_off = True
disp_strategy = 'emptiest_rack_fullest_pu'

# Simulation time and UE guard time
sim_time = 600
max_guard_time = 0
# Number of UEs
n_ues = 10

# Multi-faceted Model type
lite = True
shortcut = False

# Reports root file
model_type = 'lite' if lite else 'shortcut' if shortcut else 'classic'
sim_id = '{}_{}'.format(model_type, n_ues)  # TODO

# Visualization stuff
alpha = 1
stacked = False


def prepare_ue_mobility(df, t_start, n):
    cab_ids = list(df.cab_id.unique())
    ue_mobilities = dict()
    i = 0
    for cab_id in cab_ids:
        i += 1
        if i > n:
            break
        data = df[df.cab_id == cab_id][['epoch', 'x', 'y']]
        mobility = ('history', {'t_start': t_start, 'history': data.values})
        ue_mobilities[cab_id] = mobility
    return ue_mobilities


if __name__ == '__main__':
    # Create instance of Mercury Framework
    summersim = Mercury()
    # Define processing unit types
    summersim.fog_model.add_custom_pu_power_model('Rx580', Rx580PowerModel)

    summersim.fog_model.define_rac_config(header=0, pss_period=1e-3, rrc_period=1e-3, timeout=0.2, bypass_amf=False)
    summersim.fog_model.define_fed_mgmt_config(header=0, edc_report_data=0)
    summersim.fog_model.define_network_config(header=0)

    aps = pd.read_csv(ap_location_file).values
    edcs = pd.read_csv(edc_location_file).values

    # CROSSHAUL STUFF
    xh_link = LinkConfiguration(bandwidth=1e9, carrier_freq=0, prop_speed=2e8, penalty_delay=0, loss_prob=0, header=0,
                                att_name='fiber', att_config={'loss_factor': 0.3},
                                noise_name='thermal', noise_config=None)
    xh_tx = TransceiverConfiguration(tx_power=10, gain=0, noise_name='thermal', default_eff=10)
    summersim.fog_model.add_crosshaul_config(base_link_config=xh_link, base_trx_config=xh_tx)

    # RADIO STUFF
    dl_link = LinkConfiguration(bandwidth=100e6, carrier_freq=4.2e9, prop_speed=3e8, penalty_delay=0, loss_prob=0,
                                header=0, att_name='fspl', noise_name='thermal')
    ul_link = LinkConfiguration(bandwidth=100e6, carrier_freq=3.3e9, prop_speed=3e8, penalty_delay=0, loss_prob=0,
                                header=0, att_name='fspl', noise_name='thermal')
    dl_tx = TransceiverConfiguration(tx_power=50, gain=0, noise_name='thermal', noise_conf={'temperature': 300},
                                     mcs_table=RadioConfiguration.DL_MCS_TABLE_5G)
    ul_tx = TransceiverConfiguration(tx_power=30, gain=0, noise_name='thermal', noise_conf={'temperature': 300},
                                     mcs_table=RadioConfiguration.UL_MCS_TABLE_5G)
    summersim.fog_model.add_radio_config(base_dl_config=dl_link, base_ul_config=ul_link, base_ap_antenna=dl_tx,
                                         base_ue_antenna=ul_tx, channel_div_name='proportional')

    summersim.fog_model.add_core_config(amf_id='amf', sdn_controller_id='sdnc', core_location=(0, 0))

    summersim.fog_model.define_p_unit_config(p_unit_id='Rx580',  # The ID must be unique
                                             max_u=100,  # Standard to Specific Utilization Factor
                                             max_start_stop=max_start_stop,  # Maximum number of simulatenous start/stop services
                                             dvfs_table={  # DVFS Table. At least configuration for 100% is required
                                                100: {
                                                    'memory_clock': 2000,
                                                    'core_clock': 1366
                                                }
                                             },
                                             t_on=1,  # Time required for switching on the processing unit
                                             t_off=1,  # Time required for switching off the processing unit
                                             t_start=0.2,
                                             t_stop=0.2,
                                             t_operation=0.1,  # Time required for performing an operation
                                             pwr_model_name='Rx580',
                                             pwr_model_config={'file_path_to_model_and_scalers': '../models/pu_power/rx580_power_model/power_model_rx580'})  # Processing Unit Power Consumption model
    # Define an EDC rack type (empty yet)
    summersim.fog_model.define_edc_rack_type('novec')

    # Define EDC dispatching strategy.
    r_manager_config = {
        'hw_dvfs_mode': hw_dvfs_mode,
        'hw_power_off': hw_power_off,
        'n_hot_standby': n_hot_standby,
        'disp_strategy_name': disp_strategy,
        'disp_strategy_config': {},
    }

    # Define services configurations
    summersim.fog_model.define_service_config(service_id='adas',  # Service ID must be unique
                                              service_u=20,  # Required Service standard std_u factor
                                              header=0,  # header of any service package
                                              generation_rate=1e6,  # data stream size in bits per second
                                              packaging_time=0.5,  # service packaging period in seconds
                                              min_closed_t=0.5,  # minimum time to stay closed for service sessions in seconds
                                              min_open_t=10,  # minimum time to stay open for service sessions in seconds
                                              service_timeout=0.2,  # service requests timeout in seconds
                                              window_size=1)  # Number of requests to be sent simultaneously with no acknowledgement

    # Add Edge Data Centers to the model
    edc_racks_map = {'rack_1': ('novec', ['Rx580'] * gpus_per_edc)}
    summersim.define_standard_edc_config(edc_racks_map=edc_racks_map,
                                         resource_manager_config=r_manager_config,
                                         env_temp=298)
    for i in range(edcs.shape[0]):
        summersim.add_edc(edcs[i, 0], (edcs[i, 1], edcs[i, 2]))

    for i in range(aps.shape[0]):
        summersim.add_ap(aps[i, 0], (aps[i, 1], aps[i, 2]))

    summersim.fog_model.set_max_guard_time(max_guard_time)
    # Define standard Fog Node configuration
    # add UEs
    df = pd.read_csv('./data/ue_mobility.csv', index_col=None)
    ue_mobilities = prepare_ue_mobility(df, 1212802200, n_ues)
    for ue_id, ue_mobility in ue_mobilities.items():
        summersim.add_ue(ue_id, ['adas'], ue_mobility[0], ue_mobility[1])

    summersim.add_transducers('csv', dir_path='results')
    # summersim.add_transducers('mysql', db='trial_' + sim_id)  # TODO

    summersim.fog_model_quick_build(lite=lite, shortcut=shortcut)
    summersim.fog_model.initialize_coordinator()
    summersim.fog_model.start_simulation(time_interv=sim_time)

    summersim.plot_delay(alpha)
    summersim.plot_edc_utilization(stacked, alpha)
    summersim.plot_edc_power_demand(stacked, alpha)
    if not lite and not shortcut:
        summersim.plot_ul_bw(alpha)
        summersim.plot_dl_bw(alpha)
