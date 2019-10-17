from math import ceil
from .allocation_manager import AllocationManager
from .fog_model import FogModel, ResourceManagerConfiguration, UEMobilityConfiguration, \
    CrosshaulTransceiverConfiguration


class Mercury:
    """M&S&O Framework of Fog Computing scenarios for Data Stream Analytics"""

    def __init__(self, name='mercury'):
        """initialization method for Mercury simulator.

        :param name: Mercury instance name
        :type name: str
        """
        self.name = name
        self.allocation_manager = None
        self.fog_model = FogModel(name + '_fog_model')

        self.standard_crosshaul_transceiver = CrosshaulTransceiverConfiguration(0, 10e9, 1)
        self.standard_ue_config = dict()
        self.standard_ap_config = dict()
        self.standard_edc_config = dict()

    def define_standard_crosshaul_transceiver_config(self, power, bandwidth, spectral_efficiency):
        self.standard_crosshaul_transceiver = CrosshaulTransceiverConfiguration(power, bandwidth, spectral_efficiency)

    def define_standard_ue_config(self, antenna_power, antenna_gain, antenna_temperature=300, antenna_sensitivity=None):
        self.standard_ue_config = {
            'antenna_power': antenna_power,
            'antenna_gain': antenna_gain,
            'antenna_temperature': antenna_temperature,
            'antenna_sensitivity': antenna_sensitivity,
        }

    def define_standard_ap_config(self, antenna_power, antenna_gain, antenna_temperature=300, antenna_sensitivity=None):
        self.standard_ap_config = {
            'antenna_power': antenna_power,
            'antenna_gain': antenna_gain,
            'antenna_temperature': antenna_temperature,
            'antenna_sensitivity': antenna_sensitivity,
        }

    def define_standard_edc_config(self, p_units_id_list, resource_manager_config, base_temp=298):
        for p_unit in p_units_id_list:
            if p_unit not in self.fog_model.p_units_config:
                raise TypeError('Processing Unit {} not defined in Fog Model yet.'.format(p_unit))
        if not isinstance(resource_manager_config, ResourceManagerConfiguration):
            raise TypeError('Resource Manager Configuration is not instance of ResourceManagerConfiguration')
        self.standard_edc_config = {
            'p_units_id_list': p_units_id_list,
            'r_manager_config': resource_manager_config,
            'base_temp': base_temp
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
        print('Maximum Standard utilization of processing unit {}: {}'.format(p_unit_id, p_unit_std_u))

        total_u = 0
        for _, iot_device in self.fog_model.ues_config.items():
            for service in iot_device.service_config_list:
                total_u += service.std_u
        print('Total required standard utilization: {}'.format(total_u))

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

    def add_ap(self, ap_id, ap_location):
        self.fog_model.add_ap_config(ap_id, ap_location,
                                     crosshaul_transceiver_config=self.standard_crosshaul_transceiver,
                                     **self.standard_ap_config)

    def add_edc(self, edc_id, edc_location):
        self.fog_model.add_edc_config(edc_id, edc_location,
                                      crosshaul_transceiver_config=self.standard_crosshaul_transceiver,
                                      **self.standard_edc_config)

    def add_ue(self, ue_id, service_list, mobility):
        for service in service_list:
            if service not in self.fog_model.services_config:
                raise TypeError('Service {} not defined in Fog Model yet'.format(service))
        if not isinstance(mobility, UEMobilityConfiguration):
            raise TypeError('Mobility configuration is not instance of UEMobilityConfiguration')
        self.fog_model.add_ue_config(ue_id, service_list, mobility, **self.standard_ue_config)

    def fog_model_quick_build(self, default_location=(0, 0), dirpath=None):
        if self.fog_model.rac_config is None:
            self.fog_model.define_rac_config()
        if self.fog_model.fed_mgmt_config is None:
            self.fog_model.define_fed_mgmt_config()
        if self.fog_model.network_config is None:
            self.fog_model.define_network_config()
        if self.fog_model.fed_controller_config is None:
            self.fog_model.define_fed_controller_config('fed_controller_config', default_location,
                                                        self.standard_crosshaul_transceiver)
        if self.fog_model.core_config is None:
            self.fog_model.add_core_config('amf', 'sdn_controller', default_location,
                                           self.standard_crosshaul_transceiver)
        if self.fog_model.crosshaul_config is None:
            self.fog_model.add_crosshaul_config()
        if self.fog_model.radio_config is None:
            self.fog_model.add_radio_config()
        if dirpath is not None:
            self.fog_model.add_edc_transducer(dirpath + '/edc_report.csv')
            self.fog_model.add_radio_transducer(dirpath + '/radio_ul.csv', dirpath + '/radio_dl.csv')
            self.fog_model.add_delay_transducer(dirpath + '/ue_report.csv')
        self.fog_model.build()

    def plot_delay(self, alpha=1):
        self.fog_model.plot_delay(alpha)

    def plot_edc_utilization(self, stacked=False, alpha=1):
        self.fog_model.plot_edc_utilization(stacked, alpha)

    def plot_edc_power(self, stacked=False, alpha=1):
        self.fog_model.plot_edc_power(stacked, alpha)

    def plot_ul_bw(self, alpha=1):
        self.fog_model.plot_ul_bw(alpha)

    def plot_dl_bw(self, alpha=1):
        self.fog_model.plot_dl_bw(alpha)
