from mercury import Mercury
import random
from mercury.fog_model import ResourceManagerConfiguration, IdleActivePowerModel
from mercury.fog_model import MaximumDispatchingStrategy, MinimumDispatchingStrategy, \
    UEMobilityStraightLine

# Edge Data Center management configuration
hw_dvfs_mode = False
hw_power_off = False
# Choose one dispatching algorithm
disp_strategy = MinimumDispatchingStrategy
# disp_strategy = MaximumDispatchingStrategy

# Number of elements
n_edcs = 2  # EDCs
pus_per_edc = 18  # PUs per EDC
n_aps = 10  # APs
n_ues = 10  # UEs

# Road configuration and velocity
road_range = (0, 10000)
velocity_vector = 28

# Simulation time and UE guard time
sim_time = 30
max_guard_time = 1

# Reports root file
transducer_root = './results'

# Visualization stuff
alpha = 0.1
stacked = False

if __name__ == '__main__':

    # create instance of Mercury's fog computing model
    summersim = Mercury(name='summersim')

    # define processing units that are to be used in the simulation
    power_model = IdleActivePowerModel(idle_power=100,  # PUs consume 100 Watts when idling
                                       active_power=150)  # PUs consume 150 Watts when active
    summersim.fog_model.define_p_unit_config(p_unit_id='p_unit',
                                   std_to_spec_u=1,
                                   dvfs_table={100: {'memory_clock': 2000, 'core_clock': 1366}},
                                   t_off_on=1,
                                   t_on_off=1,
                                   t_operation=0.2,
                                   power_model=power_model)

    # Define EDC dispatching strategy.
    resource_manager_config = ResourceManagerConfiguration(hw_dvfs_mode=hw_dvfs_mode,
                                                           hw_power_off=hw_power_off,
                                                           disp_strategy=disp_strategy)

    # Define services configurations
    summersim.fog_model.define_service_config(service_id='adas',  # Service ID must be unique
                                              service_u=20,  # Required Service standard utilization factor
                                              header=0,  # header of any service package
                                              generation_rate=1e6,  # data stream size in bits per second
                                              packaging_time=0.5,  # service packaging period in seconds
                                              min_closed_t=1,  # minimum time to stay closed for service sessions in seconds
                                              min_open_t=10,  # minimum time to stay open for service sessions in seconds
                                              service_timeout=0.2,  # service requests timeout in seconds
                                              window_size=3)  # Number of requests to be sent simultaneously with no acknowledgement

    # Add Edge Data Centers to the model
    summersim.define_standard_edc_config(p_units_id_list=['p_unit'] * pus_per_edc,
                                         resource_manager_config=resource_manager_config,
                                         base_temp=298)
    edcs_locations = [(road_range[1]/2/n_edcs + road_range[1]/n_edcs*i, 100) for i in range(n_edcs)]
    for i in range(n_edcs):
        summersim.add_edc(edc_id='edc_' + str(i),  # the ID must be unique
                          edc_location=edcs_locations[i])    # location of the EDC (x, y) [m]

    # define APs
    summersim.define_standard_ap_config(antenna_power=50,
                                        antenna_gain=0,
                                        antenna_temperature=300,
                                        antenna_sensitivity=None)
    ap_locations = [(road_range[1]/2/n_aps + road_range[1]/n_aps*i, 100) for i in range(n_aps)]
    for i in range(n_aps):
        summersim.add_ap(ap_id='ap_' + str(i),  # Access Point ID must be unique
                         ap_location=ap_locations[i])  # Access Point location (x, y) [m]

    summersim.fog_model.set_max_guard_time(max_guard_time)

    # add UEs
    summersim.define_standard_ue_config(antenna_power=30,
                                        antenna_gain=0,
                                        antenna_temperature=300,
                                        antenna_sensitivity=None)
    for i in range(n_ues):
        summersim.add_ue(ue_id='ue_' + str(i),
                                service_list=['adas'],
                                mobility=UEMobilityStraightLine(line_range=road_range,
                                                                velocity_vector=velocity_vector - 2 * velocity_vector * (random.randint(0, 1)),
                                                                initial_position=(random.random() * road_range[1], 0),
                                                                time_step=5))

    summersim.fog_model_quick_build(default_location=(0, 1000), dirpath=transducer_root)
    summersim.fog_model.initialize_coordinator()
    summersim.fog_model.start_simulation(time_interv=sim_time)

    summersim.plot_delay(alpha)
    summersim.plot_edc_utilization(stacked, alpha)
    summersim.plot_edc_power(stacked, alpha)
    summersim.plot_dl_bw(alpha)
    summersim.plot_ul_bw(alpha)
