from math import ceil
from .allocation_manager import AllocationManager
from .fog_model import FogModel


class Mercury:
    """M&S&O Framework of Fog Computing scenarios for Data Stream Analytics"""

    def __init__(self, name: str = 'mercury'):
        """initialization method for Mercury simulator.
        :param name: Mercury instance name
        """
        self.name = name
        self.allocation_manager = None
        self.fog_model = FogModel(name + '_fog_model')

        self.standard_edc_config = dict()

    def define_standard_edc_config(self, edc_racks_map, resource_manager_config, env_temp=298):
        for rack_id, rack_conf in edc_racks_map.items():
            rack_type = rack_conf[0]
            p_units_list = rack_conf[1]
            if rack_type not in self.fog_model.edc_rack_types:
                raise AssertionError("Rack type for rack {} is not defined".format(rack_id))
            for p_unit in p_units_list:
                if p_unit not in self.fog_model.p_units_config:
                    raise AssertionError("Processing Unit that conforms the EDC is not defined")
        self.standard_edc_config = {
            'edc_racks_map': edc_racks_map,
            'r_manager_config': resource_manager_config,
            'env_temp': env_temp
        }

    def init_allocation_manager(self, data, time_window=60, grid_res=40, plot=False):
        self.allocation_manager = AllocationManager(data, time_window, grid_res, plot)

    def auto_add_aps(self, prefix='ap_', plot=False):
        self.allocation_manager.allocate_aps(plot)
        aps = self.allocation_manager.aps
        for i in range(aps.shape[0]):
            x = aps[i, 0]
            y = aps[i, 1]
            ap_location = (x, y)
            self.add_ap(prefix + str(i), ap_location)

    def auto_add_edcs(self, p_unit_id, replication_factor=2, prefix='edc_', plot=False):
        if p_unit_id not in self.fog_model.p_units_config:
            raise TypeError('Processing unit {} is not yet defined in Fog Model'.format(p_unit_id))
        p_unit_std_u = 100 * self.fog_model.p_units_config[p_unit_id].std_to_spec_u
        print('Maximum Standard std_u of processing unit {}: {}'.format(p_unit_id, p_unit_std_u))

        total_u = 0
        for _, iot_device in self.fog_model.ues_config.items():
            for service in iot_device.service_config_list:
                total_u += service.std_u
        print('Total required standard std_u: {}'.format(total_u))

        min_p_units = ceil(total_u / p_unit_std_u)
        print('Minimum number of processing units {} for a single EDC: {}'.format(p_unit_id, min_p_units))
        self.standard_edc_config['p_units_id_list'] = [p_unit_id] * min_p_units

        self.allocation_manager.allocate_edcs(opt='n', n=replication_factor)
        edcs = self.allocation_manager.edcs
        for i in range(edcs.shape[0]):
            x = edcs[i, 0]
            y = edcs[i, 1]
            edc_location = (x, y)
            self.add_edc(prefix + str(i), edc_location)
        if plot:
            self.allocation_manager.plot_scenario()

    def add_ap(self, ap_id, ap_location, crosshaul_trx=None, radio_antenna=None):
        self.fog_model.add_ap_config(ap_id, ap_location, crosshaul_trx, radio_antenna)

    def add_edc(self, edc_id, edc_location, crosshaul_trx=None):
        self.fog_model.add_edc_config(edc_id, edc_location, crosshaul_trx=crosshaul_trx,
                                      **self.standard_edc_config)

    def add_ue(self, ue_id, service_list, mobility_name, mobility_config, radio_antenna=None):
        for service in service_list:
            if service not in self.fog_model.services_config:
                raise TypeError('Service {} not defined in Fog Model yet'.format(service))
        self.fog_model.add_ue_config(ue_id, service_list, radio_antenna, mobility_name, **mobility_config)

    def add_transducers(self, transducer, **kwargs):
        self.fog_model.add_transducers(transducer, **kwargs)

    def fog_model_quick_build(self, default_location=(0, 0), lite=False, shortcut=False):
        if self.fog_model.rac_config is None:
            self.fog_model.define_rac_config()
        if self.fog_model.fed_mgmt_config is None:
            self.fog_model.define_fed_mgmt_config()
        if self.fog_model.network_config is None:
            self.fog_model.define_network_config()
        if self.fog_model.core_config is None:
            self.fog_model.add_core_config('amf', 'sdn_controller', default_location)
        if self.fog_model.crosshaul_config is None:
            self.fog_model.add_crosshaul_config()
        if self.fog_model.radio_config is None:
            self.fog_model.add_radio_config()
        self.fog_model.build(lite, shortcut)

    def plot_delay(self, alpha=1):
        self.fog_model.plot_delay(alpha)

    def plot_edc_utilization(self, stacked=False, alpha=1):
        self.fog_model.plot_edc_utilization(stacked, alpha)

    def plot_edc_power_demand(self, stacked=False, alpha=1):
        self.fog_model.plot_edc_power_demand(stacked, alpha)

    def plot_edc_it_power(self, stacked=False, alpha=1):
        self.fog_model.plot_edc_it_power(stacked, alpha)

    def plot_edc_cooling_power(self, stacked=False, alpha=1):
        self.fog_model.plot_edc_cooling_power(stacked, alpha)

    def plot_ul_bw(self, alpha=1):
        self.fog_model.plot_ul_bw(alpha)

    def plot_dl_bw(self, alpha=1):
        self.fog_model.plot_dl_bw(alpha)
