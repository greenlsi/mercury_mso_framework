from math import ceil
from typing import Optional
from .allocation_manager import AllocationManager
from .fog_model import FogModel


class Mercury:
    """M&S&O Framework of Fog Computing scenarios for Data Stream Analytics"""

    def __init__(self, name: str = 'mercury'):
        """initialization method for Mercury simulator.
        :param name: Mercury instance name
        """
        self.name = name
        self.allocation_manager: Optional[AllocationManager] = None
        self.fog_model: FogModel = FogModel(name + '_fog_model')

        self.standard_edc_config = dict()

    def define_standard_edc_config(self, edc_racks_map, resource_manager_config, power_sources=None,
                                   power_storage_name=None, power_storage_config=None, env_temp=298):
        for rack_id, rack_conf in edc_racks_map.items():
            rack_type = rack_conf[0]
            p_units_list = rack_conf[1]
            if rack_type not in self.fog_model.cooler_configs:
                raise AssertionError("Rack type for rack {} is not defined".format(rack_id))
            for p_unit in p_units_list:
                if p_unit not in self.fog_model.pu_configs:
                    raise AssertionError("Processing Unit that conforms the EDC is not defined")
        self.standard_edc_config = {
            'edc_racks_map': edc_racks_map,
            'r_manager_config': resource_manager_config,
            'power_sources': power_sources,
            'power_storage_name': power_storage_name,
            'power_storage_config': power_storage_config,
            'env_temp': env_temp
        }

    def init_allocation_manager(self, data, time_window=60, grid_res=40):
        self.allocation_manager = AllocationManager(data, time_window, grid_res)

    def auto_add_aps(self, prefix='ap_', plot=False):
        self.allocation_manager.allocate_aps(plot)
        aps = self.allocation_manager.aps
        for i in range(aps.shape[0]):
            x = aps[i, 0]
            y = aps[i, 1]
            ap_location = (x, y)
            self.fog_model.add_ap_config(prefix + str(i), ap_location)

    def auto_add_edcs(self, p_unit_id, replication_factor=2, prefix='edc_', plot=False):
        if p_unit_id not in self.fog_model.pu_configs:
            raise TypeError('Processing unit {} is not yet defined in Fog Model'.format(p_unit_id))
        p_unit_std_u = 100 * self.fog_model.pu_configs[p_unit_id].std_to_spec_u
        print('Maximum Standard utilization of processing unit {}: {}'.format(p_unit_id, p_unit_std_u))

        total_u = 0
        for _, iot_device in self.fog_model.ue_configs.items():
            for service in iot_device.srv_configs:
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

    def add_edc(self, edc_id, edc_location, crosshaul_trx=None):
        self.fog_model.add_edc_config(edc_id, edc_location, edc_trx=crosshaul_trx,
                                      **self.standard_edc_config)

    def add_transducers(self, transducer, **kwargs):
        self.fog_model.add_transducers(transducer, **kwargs)

    def fog_model_quick_build(self, default_location=(0, 0), lite=False, shortcut=False):
        if self.fog_model.core_config is None:
            self.fog_model.add_core_config(default_location)
        if self.fog_model.xh_config is None:
            self.fog_model.add_xh_config()
        if self.fog_model.radio_config is None:
            self.fog_model.add_radio_config()
        self.fog_model.build(lite, shortcut)
