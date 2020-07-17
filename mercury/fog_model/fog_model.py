import datetime
import logging
from typing import List, Dict, Tuple

from xdevs.models import Coupled
from xdevs.sim import Coordinator
from .common.packet.apps.service import ServiceConfiguration
from .common.packet.apps.federation_management import FederationManagementConfiguration
from .common.packet.apps.ran import RadioAccessNetworkConfiguration
from .common.packet.packet import NetworkPacketConfiguration
from .common.edge_fed.edge_fed import EdgeDataCenterConfiguration, ResourceManagerConfiguration
from .common.edge_fed.pu import ProcessingUnitConfiguration
from .common.edge_fed.rack import RackNodeConfiguration, RackConfiguration

from .shortcut import Shortcut, NetworkMultiplexer

from .edge_fed import EdgeFederation
from .edge_fed.edc.rack.pu import ProcessingUnit
from .edge_fed.edc.rack.rack_node import RackNode
from .edge_fed.edc.r_manager import ResourceManager
from .core.sdnc import SoftwareDefinedNetworkController
from .network.link import Link
from .network.network import MasterNetwork
from .network.node import NodeConfiguration, Nodes

from .network import LinkConfiguration, TransceiverConfiguration
from .core import CoreLayerConfiguration, Core, CoreLite
from .crosshaul import Crosshaul, CrosshaulConfiguration
from .access_points import AccessPointConfiguration, AccessPoints
from .radio import RadioConfiguration, Radio, RadioShortcut
from .iot_devices import UserEquipmentConfiguration, IoTDevicesLayerConfiguration, IoTDevices, IoTDevicesLite
from ..visualization import *

from .transducers.transducers import TransducerBuilderFactory

AP_CONFIG = 'ap_config'
AP_POWER = 'ap_power'
AP_GAIN = 'ap_gain'
AP_TEMPERATURE = 'ap_temperature'
AP_SENSITIVITY = 'ap_sensitivity'


class FogModel:
    """
    Edge Computing for Data Stream Analytics Model

    :param str name: Mercury Edge model instance name
    """
    def __init__(self, name='fog_model'):
        self.name = name
        self.model = None
        self.coordinator = None

        self.rac_config = None
        self.fed_mgmt_config = None
        self.network_config = None
        self.edc_rack_types = dict()
        self.p_units_config = dict()
        self.services_config = dict()

        self.edcs_config = dict()
        self.aps_config = dict()
        self.ues_config = dict()
        self.fed_controller_config = None

        self.core_config = None
        self.crosshaul_config = None
        self.radio_config = None
        self.max_guard_time = 0

        # Create all the factories
        self.transducer_builder_factory = TransducerBuilderFactory()

        # Transducers to be added
        self.transducer_keys = dict()
        self.edc_transducers = list()
        self.radio_transducers = list()
        self.ue_delay_transducers = list()

    def define_rac_config(self, header=0, pss_period=0, rrc_period=0, timeout=0.5, bypass_amf=False):
        """
        Define configuration for all the services related with radio access operations.

        :param int header: size (in bits) of the header of radio access application messages
        :param float pss_period: period (in seconds) of Primary Synchronization Signals
        :param float rrc_period: period (in seconds) of Radio Resource Control Signals
        :param float timeout: time (in seconds) to wait before an unacknowledged message is considered timed out
        :param bypass_amf:
        """
        self.rac_config = RadioAccessNetworkConfiguration(header, pss_period, rrc_period, timeout, bypass_amf)

    def define_fed_mgmt_config(self, header=0, edc_report_data=0):
        """
        Define configuration for all federation management-related messages.

        :param int header: size (in bits) of the header of radio access application messages
        :param int edc_report_data: size (in bits) of the body of EDC report messages
        """
        self.fed_mgmt_config = FederationManagementConfiguration(header, edc_report_data)

    def define_network_config(self, header=0):
        """
        Define configuration for all the network packets.

        :param int header: size (in bits) of the header of network packets.
        """
        self.network_config = NetworkPacketConfiguration(header)

    @staticmethod
    def add_custom_rack_node_temp_model(key, model):
        RackNode.rack_temp_factory.register_model(key, model)

    @staticmethod
    def add_custom_rack_node_power_model(key, model):
        RackNode.rack_power_factory.register_model(key, model)

    def define_edc_rack_type(self, rack_id, temp_model_name=None, temp_model_config=None, pwr_model_name=None,
                             pwr_model_config=None):
        """
        :param str rack_id: ID for the rack type
        :param str temp_model_name: Temperature model name for the rack type
        :param dict temp_model_config: Temperature model configuration parameters
        :param str pwr_model_name: Heat dissipation power model name for the rack type
        :param dict pwr_model_config: Power model configuration parameters
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if rack_id in self.edc_rack_types:
            raise AssertionError("EDC Rack ID matches with other already defined")
        self.edc_rack_types[rack_id] = RackNodeConfiguration(rack_id, temp_model_name, temp_model_config,
                                                             pwr_model_name, pwr_model_config)

    @staticmethod
    def add_custom_pu_power_model(key, model):
        ProcessingUnit.pu_power_factory.register_model(key, model)

    @staticmethod
    def add_custom_pu_temp_model(key, model):
        ProcessingUnit.pu_temp_factory.register_model(key, model)

    def define_p_unit_config(self, p_unit_id, dvfs_table=None, max_u=100, max_start_stop=0, t_on=0, t_off=0, t_start=0,
                             t_stop=0, t_operation=0, pwr_model_name=None, pwr_model_config=None, temp_model_name=None,
                             temp_model_config=None):
        """
        Define a new Processing Unit type.
        :param str p_unit_id: Processing Unit type ID. It must be unique.
        :param dict dvfs_table: DVFS table. Keys are maximum specific std_u factor for using this DVFS
                                configuration. Values are hardware configuration for the given DVFS configuration
        :param float max_u: Processing Unit maximum utilization factor
        :param int max_start_stop: Maximum number of services that can be simultaneously started and/or stopped
        :param float t_on: time required for the processing unit to switch on [s]
        :param float t_off: time required for the processing unit to switch off [s]
        :param float t_start: time required for the processing unit to start a session [s]
        :param float t_stop: time required for the processing unit to stop a session [s]
        :param float t_operation: time required for the processing unit to perform an operation [s]
        :param str pwr_model_name: Processing unit power model name
        :param dict pwr_model_config: Processing unit power model configuration
        :param str temp_model_name: Processing unit temperature model name
        :param dict temp_model_config: Processing unit temperature model configuration
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if p_unit_id in self.p_units_config:
            raise AssertionError("Processing Unit ID matches with other already defined")
        p_unit_config = ProcessingUnitConfiguration(p_unit_id, dvfs_table, max_u, max_start_stop, t_on, t_off, t_start,
                                                    t_stop, t_operation, pwr_model_name, pwr_model_config,
                                                    temp_model_name, temp_model_config)
        self.p_units_config[p_unit_id] = p_unit_config

    def define_service_config(self, service_id, service_u, header, generation_rate, packaging_time, min_closed_t,
                              min_open_t, service_timeout, window_size=1):
        """
        Define Service to be ran by UEs

        :param str service_id: Service configuration ID. It must be unique among all the services defined in the model
        :param float service_u: Standard EDC std_u factor required by the service
        :param int header: size (in bits) of headers of a given service
        :param float generation_rate: data stream generation rate (in bps)
        :param float packaging_time: time (in seconds) encapsulated in each service session message
        :param float min_closed_t: minimum time (in seconds) to wait before opening a service session
        :param float min_open_t: minimum time (in seconds) to wait before closing a service session
        :param float service_timeout: time (in seconds) to wait before considering a message without response timed out
        :param int window_size: maximum number of session requests that can be sent simultaneously with no response
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if service_id in self.services_config:
            raise AssertionError("Service ID already defined")

        new_service = ServiceConfiguration(service_id, service_u, header, generation_rate, packaging_time, min_closed_t,
                                           min_open_t, service_timeout, window_size)
        self.services_config[service_id] = new_service

    @staticmethod
    def add_custom_dispatch_strategy(key, model):
        ResourceManager.dispatching_factory.register_strategy(key, model)

    def add_edc_config(self, edc_id: str, edc_location: Tuple[float, ...], crosshaul_trx: TransceiverConfiguration,
                       r_manager_config: Dict, edc_racks_map: Dict[str, Tuple[str, List[ProcessingUnitConfiguration]]],
                       env_temp: float = 298):
        """
        :param edc_id:
        :param edc_location:
        :param crosshaul_trx:
        :param r_manager_config:
        :param edc_racks_map:
        :param env_temp:
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if edc_id in self.edcs_config:
            raise AssertionError("Edge Data Center already defined")
        rack_configs = dict()

        hw_dvfs_mode = r_manager_config.get('hw_dvfs_mode', False)
        hw_power_off = r_manager_config.get('hw_power_off', False)
        n_hot_standby = r_manager_config.get('n_hot_standby', 0)

        disp_strategy_name = r_manager_config.get('disp_strategy_name', 'emptiest_rack_emptiest_pu')
        disp_strategy_config = r_manager_config.get('disp_strategy_config', None)

        r_manager_conf = ResourceManagerConfiguration(hw_dvfs_mode, hw_power_off, n_hot_standby, disp_strategy_name,
                                                      disp_strategy_config)

        for rack_id, rack_conf in edc_racks_map.items():
            rack_type = rack_conf[0]
            p_units_list = rack_conf[1]
            if rack_type not in self.edc_rack_types:
                raise AssertionError("Rack type for rack {} is not defined".format(rack_id))
            for p_unit in p_units_list:
                if p_unit not in self.p_units_config:
                    raise AssertionError("Processing Unit that conforms the EDC is not defined")
            p_units_config_list = [self.p_units_config[p_unit_id] for p_unit_id in p_units_list]
            rack_node_config = self.edc_rack_types[rack_type]
            rack_configs[rack_id] = RackConfiguration(rack_id, p_units_config_list, rack_node_config)

        new_edc = EdgeDataCenterConfiguration(edc_id, edc_location, crosshaul_trx,
                                              r_manager_conf, rack_configs, env_temp)
        self.edcs_config[edc_id] = new_edc

    @staticmethod
    def add_custom_sdn_strategy(key, model):
        SoftwareDefinedNetworkController.sdn_strategy_factory.register_strategy(key, model)

    def add_core_config(self, amf_id, sdn_controller_id, core_location, crosshaul_transceiver_config=None,
                        sdn_strategy_name='closest', sdn_strategy_config=None):
        """
        Add core_config layer to Mercury model

        :param str amf_id: Access and Mobility Management Function ID
        :param str sdn_controller_id: Software-Defined Network Function ID
        :param tuple core_location: Core network elements (SDN controller, AMF) ue_location (x, y) [m]
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver_config: Crosshaul transceiver configuration
        :param str sdn_strategy_name: SDN Controller name
        :param dict sdn_strategy_config: SDN Controller configuration
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")

        self.core_config = CoreLayerConfiguration(amf_id, sdn_controller_id, core_location,
                                                  crosshaul_transceiver_config, sdn_strategy_name, sdn_strategy_config)

    @staticmethod
    def add_custom_link_attenuation(key, model):
        Link.attenuation_factory.register_attenuation(key, model)

    @staticmethod
    def add_custom_link_noise(key, model):
        Link.noise_factory.register_noise(key, model)

    def add_crosshaul_config(self, base_link_config: LinkConfiguration = None,
                             base_trx_config: TransceiverConfiguration = None):
        """

        :param base_link_config:
        :param base_trx_config:
        :return:
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.crosshaul_config = CrosshaulConfiguration(base_link_config, base_trx_config)

    def add_ap_config(self, ap_id: str, ap_location: Tuple[float, ...],
                      crosshaul_trx_config: TransceiverConfiguration = None,
                      radio_antenna_config: TransceiverConfiguration = None):
        """
        Access Point Configuration
        :param ap_id: ID of the Access Point (it must be unique)
        :param ap_location: location of the AP expressed as a tuple (in meters)
        :param crosshaul_trx_config:  AP's crosshaul transceiver configuration
        :param radio_antenna_config: AP's radio antenna configuration
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if ap_id in self.aps_config:
            raise AssertionError("Access Point already defined")
        new_ap = AccessPointConfiguration(ap_id, ap_location, crosshaul_trx_config, radio_antenna_config)
        self.aps_config[ap_id] = new_ap

    @staticmethod
    def add_custom_channel_division_strategy(key, model):
        MasterNetwork.channel_div_factory.register_division(key, model)

    @staticmethod
    def add_custom_node_mobility(key, model):
        NodeConfiguration.mobility_factory.register_mobility(key, model)

    def add_radio_config(self, base_dl_config: LinkConfiguration = None, base_ul_config: LinkConfiguration = None,
                         base_ap_antenna: TransceiverConfiguration = None,
                         base_ue_antenna: TransceiverConfiguration = None, channel_div_name: str = None,
                         channel_div_config: Dict = None):
        """

        :param base_dl_config:
        :param base_ul_config:
        :param base_ap_antenna:
        :param base_ue_antenna:
        :param channel_div_name:
        :param channel_div_config:
        :return:
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.radio_config = RadioConfiguration(base_dl_config, base_ul_config, base_ap_antenna, base_ue_antenna,
                                               channel_div_name, channel_div_config)

    def add_ue_config(self, ue_id: str, services_id: List[str], radio_antenna: TransceiverConfiguration = None,
                      mobility_name: str = None, **kwargs):
        """

        :param ue_id:
        :param services_id:
        :param radio_antenna:
        :param mobility_name:
        :param kwargs:
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if ue_id in self.ues_config:
            raise AssertionError('User Equipment ID already defined')
        for service_id in services_id:
            if service_id not in self.services_config:
                raise AssertionError("Service that conforms the UE is not defined")
        service_config_list = [self.services_config[service_id] for service_id in services_id]

        new_ue = UserEquipmentConfiguration(ue_id, service_config_list, radio_antenna, mobility_name, **kwargs)
        self.ues_config[ue_id] = new_ue

    def set_max_guard_time(self, max_guard_time):
        """
        Add a guard time generator in order to prevent from similar, simultaneous UE behaviour

        :param float max_guard_time: upper limit of the uniform distribution
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.max_guard_time = max_guard_time

    def add_transducers(self, key, **kwargs):
        if not self.transducer_builder_factory.is_builder_defined(key):
            raise ValueError("Transducer builder is not defined.")
        if key in self.transducer_keys:
            raise ValueError("Transducer already defined")
        self.transducer_keys[key] = kwargs

    def build(self, lite=False, shortcut=False):
        """ Build Mercury model """
        if self.network_config is None:
            raise Exception
        if self.fed_mgmt_config is None:
            raise Exception

        logging.info("Mercury: Building Layers...")

        logging.info("    Building Edge Federation Layer...")
        federation = EdgeFederation(self.name + '_edge_fed', self.edcs_config,
                                    self.services_config, self.fed_mgmt_config, self.network_config,
                                    self.core_config.sdnc_id, lite=lite)
        logging.info("    Edge Federation Layer built")

        logging.info("    Building Core Layer...")
        aps_location = {ap_id: ap_config.ap_location for ap_id, ap_config in self.aps_config.items()}
        edcs_location = {edc_id: edc_config.edc_location for edc_id, edc_config in self.edcs_config.items()}
        ues_location = {ue_id: ue_config.ue_location for ue_id, ue_config in self.ues_config.items()}
        services_id = [service_id for service_id in self.services_config]
        if lite:
            core = CoreLite(self.name + '_core', self.core_config, self.fed_mgmt_config, self.network_config,
                            ues_location, aps_location, edcs_location, services_id)
        else:
            if self.rac_config is None:
                raise Exception
            core = Core(self.name + '_core', self.core_config, self.rac_config, self.fed_mgmt_config,
                        self.network_config,
                        aps_location, edcs_location, services_id)
        logging.info("    Core Layer built")

        crosshaul = None
        access = None
        radio = None
        if not lite:
            if not shortcut:
                logging.info("    Building Crosshaul Layer...")
                ap_nodes = {ap_id: ap_config.crosshaul_node for ap_id, ap_config in self.aps_config.items()}
                edc_nodes = {edc_id: edc_config.crosshaul_node for edc_id, edc_config in self.edcs_config.items()}
                core_functions = self.core_config.core_nodes
                crosshaul = Crosshaul(self.name + '_crosshaul', self.crosshaul_config, ap_nodes, edc_nodes,
                                      core_functions)
                logging.info("    Crosshaul Layer built")

            logging.info("    Building Access Points Layer...")
            access = AccessPoints(self.name + '_access', self.aps_config, self.core_config.amf_id, self.rac_config,
                                  self.network_config)
            logging.info("    Access Points Layer built")

            logging.info("    Building Radio Layer...")
            ap_nodes = {ap_id: ap_config.radio_node for ap_id, ap_config in self.aps_config.items()}
            ue_nodes = {ue_id: ue_config.radio_node for ue_id, ue_config in self.ues_config.items()}
            if shortcut:
                radio = RadioShortcut(self.name + '_radio', self.radio_config, ue_nodes, ap_nodes)
            else:
                radio = Radio(self.name + '_radio', self.radio_config, ue_nodes, ap_nodes)
            logging.info("    Radio Layer built")

        logging.info("    Building IoT Devices Layer...")
        iot_config = IoTDevicesLayerConfiguration(self.ues_config, self.max_guard_time)
        if lite:
            iot_devices = IoTDevicesLite(self.name + '_iot_devices', iot_config, self.network_config,
                                         self.core_config.sdnc_id)
        else:
            iot_devices = IoTDevices(self.name + '_iot_devices', iot_config, self.rac_config, self.network_config)
        logging.info("    IoT Devices Layer built")

        logging.info("    Building Transducers...")
        scenario_config = dict()
        scenario_config['edcs'] = list(self.edcs_config.values())
        scenario_config['aps'] = list(self.aps_config.values())
        scenario_config['services'] = list(self.services_config.values())
        scenario_config['ues'] = list(self.ues_config.values())

        for key, config in self.transducer_keys.items():
            builder = self.transducer_builder_factory.create_transducer_builder(scenario_config, key, **config)
            self.edc_transducers.append(builder.create_edc_transducer())
            self.radio_transducers.append(builder.create_radio_transducer())
            self.ue_delay_transducers.append(builder.create_ue_delay_transducer())
        logging.info("    Transducers built")

        logging.info("Mercury: Layers built successfully")

        logging.info("Mercury: Building model...")
        if lite:
            ue_nodes = {ue_id: ue_config.radio_node for ue_id, ue_config in self.ues_config.items()}
            mobility = Nodes('ue_mobility', ue_nodes)
            self.model = MercuryLite(self.name, federation, core, iot_devices, mobility, self.ue_delay_transducers,
                                     self.edc_transducers)
        elif shortcut:
            self.model = MercuryFogModelShortcut(self.name, federation, core, access, radio, iot_devices,
                                                 self.ue_delay_transducers, self.edc_transducers)
        else:
            self.model = MercuryFogModel(self.name, federation, core, crosshaul, access, radio, iot_devices,
                                         self.ue_delay_transducers, self.edc_transducers, self.radio_transducers)
        logging.info("Mercury: model built successfully")

    def initialize_coordinator(self):
        """ Initialize Mercury xDEVS coordinator """
        if self.model is None:
            raise AssertionError('Mercury model has not been built yet.')
        logging.info("Mercury: Starting Coordinator initialization...")
        self.coordinator = Coordinator(self.model)
        self.coordinator.initialize()
        logging.info("Mercury: Coordinator initialization finished successfully")

    def start_simulation(self, time_interv=10000):
        """ Start Mercury model simulation """
        start_date = datetime.datetime.now()
        if self.coordinator is None:
            raise AssertionError("Mercury Coordinator has not been initialized yet")
        self.coordinator.simulate_time(time_interv=time_interv)
        finish_date = datetime.datetime.now()
        sim_time = finish_date - start_date
        print("*********************")
        print('It took {} seconds to simulate'.format(sim_time))
        print("*********************")
        return sim_time

    def plot_delay(self, alpha=1):
        if not self.ue_delay_transducers:
            raise ValueError("There is not any defined delay transducer")
        delay_transducer = self.ue_delay_transducers[0]
        t, ue_id, delay = delay_transducer.get_delay_data()
        plot_ue_service_delay(t, ue_id, delay, alpha)

    def plot_edc_utilization(self, stacked=False, alpha=1):
        if not self.edc_transducers:
            raise ValueError("There is not any defined EDC transducer")
        edc_transducer = self.edc_transducers[0]
        t, edc_id, utilization = edc_transducer.get_edc_utilization_data()
        plot_edc_utilization(t, edc_id, utilization, stacked=stacked, alpha=alpha)

    def plot_edc_power_demand(self, stacked=False, alpha=1):
        if not self.edc_transducers:
            raise ValueError("There is not any defined EDC transducer")
        edc_transducer = self.edc_transducers[0]
        t, edc_id, power = edc_transducer.get_edc_power_demand_data()
        plot_edc_power(t, edc_id, power, stacked=stacked, alpha=alpha)

    def plot_edc_it_power(self, stacked=False, alpha=1):
        if not self.edc_transducers:
            raise ValueError("There is not any defined EDC transducer")
        edc_transducer = self.edc_transducers[0]
        t, edc_id, power = edc_transducer.get_edc_it_power_data()
        plot_edc_power(t, edc_id, power, stacked=stacked, alpha=alpha, nature='Demand (only IT)')

    def plot_edc_cooling_power(self, stacked=False, alpha=1):
        if not self.edc_transducers:
            raise ValueError("There is not any defined EDC transducer")
        edc_transducer = self.edc_transducers[0]
        t, edc_id, power = edc_transducer.get_edc_cooling_power_data()
        plot_edc_power(t, edc_id, power, stacked=stacked, alpha=alpha, nature='Demand (only Cooling)')

    def plot_edc_power_consumption(self, stacked=False, alpha=1):
        if not self.edc_transducers:
            raise ValueError("There is not any defined EDC transducer")
        edc_transducer = self.edc_transducers[0]
        t, edc_id, power = edc_transducer.get_edc_power_consumption_data()
        plot_edc_power(t, edc_id, power, stacked=stacked, alpha=alpha, nature='Consumption')

    def plot_edc_charging_power(self, stacked=False, alpha=1):
        if not self.edc_transducers:
            raise ValueError("There is not any defined EDC transducer")
        edc_transducer = self.edc_transducers[0]
        t, edc_id, power = edc_transducer.get_edc_charging_power_data()
        plot_edc_power(t, edc_id, power, stacked=stacked, alpha=alpha, nature='Storage')

    def plot_edc_power_generation(self, stacked=False, alpha=1):
        if not self.edc_transducers:
            raise ValueError("There is not any defined EDC transducer")
        edc_transducer = self.edc_transducers[0]
        t, edc_id, power = edc_transducer.get_edc_power_generation_data()
        plot_edc_power(t, edc_id, power, stacked=stacked, alpha=alpha, nature='Generation')

    def plot_edc_energy_stored(self, alpha=1):
        if not self.edc_transducers:
            raise ValueError("There is not any defined EDC transducer")
        edc_transducer = self.edc_transducers[0]
        t, edc_id, energy = edc_transducer.get_edc_energy_stored_data()
        plot_edc_energy(t, edc_id, energy, alpha=alpha)

    def plot_ul_bw(self, alpha=1):
        if not self.radio_transducers:
            raise ValueError("There is not any defined radio transducer")
        radio_transducer = self.radio_transducers[0]
        time, ue_id, ap_id, bandwidth, rate, efficiency = radio_transducer.get_ul_radio_data()
        plot_bw(time, ue_id, ap_id, bandwidth, rate, efficiency, alpha=alpha)

    def plot_dl_bw(self, alpha=1):
        if not self.radio_transducers:
            raise ValueError("There is not any defined radio transducer")
        radio_transducer = self.radio_transducers[0]
        time, ue_id, ap_id, bandwidth, rate, efficiency = radio_transducer.get_dl_radio_data()
        plot_bw(time, ue_id, ap_id, bandwidth, rate, efficiency, link='Downlink', alpha=alpha)


class MercuryFogModel(Coupled):
    def __init__(self, name, edge_fed, core, crosshaul, access_points, radio, iot_devices, ue_delay_transducers,
                 edc_transducers, radio_transducers):
        """
        :param str name: xDEVS model name
        :param EdgeFederation edge_fed: Edge Federation Layer Model
        :param Core core: Core Network Layer Model
        :param Crosshaul crosshaul: Crosshaul Network Layer Model
        :param AccessPoints access_points: Access Points Layer Model
        :param Radio radio: Radio Network Layer Model
        :param IoTDevices iot_devices: IoT devices Layer Model
        :param list ue_delay_transducers: list of User Equipment Delay transducers
        :param list edc_transducers: list of Edge Data Center transducers
        :param list radio_transducers: list of Radio Interface transducers
        """
        super().__init__(name)

        # Add components
        logging.info("    Adding Layers...")
        for component in [edge_fed, crosshaul, core, access_points, radio, iot_devices]:
            self.add_component(component)
        logging.info("    Layers added")

        logging.info("    Coupling Layers...")
        self.internal_edge_fed_crosshaul(edge_fed, crosshaul)
        self.internal_core_crosshaul(core, crosshaul)
        self.internal_crosshaul_access_points(crosshaul, access_points)
        self.internal_access_points_radio(access_points, radio)
        self.internal_radio_iot_devices(radio, iot_devices)
        self.internal_access_points_iot_devices(access_points, iot_devices)
        logging.info("    Layers Coupled")

        logging.info("    Adding and Coupling Transducers...")
        self.internal_transducers(iot_devices, ue_delay_transducers, edge_fed,
                                  edc_transducers, radio, radio_transducers)
        logging.info("    Transducers Added and Coupled")

    def internal_edge_fed_crosshaul(self, edge_fed: EdgeFederation, crosshaul: Crosshaul):
        self.add_coupling(edge_fed.output_crosshaul, crosshaul.input_data)
        for edc_id in edge_fed.edcs:
            self.add_coupling(crosshaul.outputs_node_to[edc_id], edge_fed.inputs_crosshaul[edc_id])

    def internal_core_crosshaul(self, core: Core, crosshaul: Crosshaul):
        self.add_coupling(core.output_crosshaul, crosshaul.input_data)
        for function in core.core_functions:
            self.add_coupling(crosshaul.outputs_node_to[function], core.inputs_crosshaul[function])

    def internal_crosshaul_access_points(self, crosshaul: Crosshaul, access_points: AccessPoints):
        self.add_coupling(access_points.output_crosshaul, crosshaul.input_data)
        for ap_id in access_points.ap_ids:
            self.add_coupling(crosshaul.outputs_node_to[ap_id], access_points.inputs_crosshaul[ap_id])

    def internal_access_points_radio(self, access_points: AccessPoints, radio: Radio):
        self.add_coupling(access_points.output_radio_bc, radio.input_pbch)
        self.add_coupling(access_points.output_radio_control_dl, radio.input_pdcch)
        self.add_coupling(access_points.output_radio_transport_dl, radio.input_pdsch)
        self.add_coupling(access_points.output_connected_ues, radio.input_enable_channels)
        for ap_id in access_points.ap_ids:
            self.add_coupling(radio.outputs_pucch[ap_id], access_points.inputs_radio_control_ul[ap_id])
            self.add_coupling(radio.outputs_pusch[ap_id], access_points.inputs_radio_transport_ul[ap_id])

    def internal_radio_iot_devices(self, radio: Radio, iot_devices: IoTDevices):
        self.add_coupling(iot_devices.output_radio_control_ul, radio.input_pucch)
        self.add_coupling(iot_devices.output_radio_transport_ul, radio.input_pusch)
        for ue_id in iot_devices.ue_ids:
            self.add_coupling(radio.outputs_pbch[ue_id], iot_devices.inputs_radio_bc[ue_id])
            self.add_coupling(radio.outputs_pdcch[ue_id], iot_devices.inputs_radio_control_dl[ue_id])
            self.add_coupling(radio.outputs_pdsch[ue_id], iot_devices.inputs_radio_transport_dl[ue_id])
            # self.add_coupling(iot_devices.output_repeat_location, radio.input_repeat_location)

    def internal_access_points_iot_devices(self, access_points: AccessPoints, iot_devices: IoTDevices):
        self.add_coupling(iot_devices.output_repeat_location, access_points.input_repeat_pss)

    def internal_transducers(self, iot_devices: IoTDevices, ue_delay_transducers: List, edge_fed: EdgeFederation,
                             edc_transducers: List, radio: Radio, radio_transducers: List):
        for delay_transducer in ue_delay_transducers:
            self.add_component(delay_transducer)
            self.add_coupling(iot_devices.output_service_delay_report, delay_transducer.input_service_delay_report)
        for edge_fed_transducer in edc_transducers:
            self.add_component(edge_fed_transducer)
            self.add_coupling(edge_fed.output_edc_report, edge_fed_transducer.input_edc_report)
        for radio_transducer in radio_transducers:
            self.add_component(radio_transducer)
            self.add_coupling(radio.output_ul_report, radio_transducer.input_new_ul_mcs)
            self.add_coupling(radio.output_dl_report, radio_transducer.input_new_dl_mcs)


class MercuryFogModelShortcut(Coupled):
    def __init__(self, name, edge_fed: EdgeFederation, core: Core, access_points: AccessPoints,
                 radio: RadioShortcut, iot_devices: IoTDevices, ue_delay_transducers, edc_transducers):
        super().__init__(name)

        logging.info("    Building Shortcut Module...")
        ue_ids_list = [ue_id for ue_id in iot_devices.ue_ids]
        ap_ids_list = [ap_id for ap_id in access_points.ap_ids]
        edc_ids_list = [edc_id for edc_id in edge_fed.edcs]
        core_ids_list = [core_id for core_id in core.core_functions]
        shortcut = Shortcut(ue_ids_list, ap_ids_list, edc_ids_list, core_ids_list, 'shortcut')
        logging.info("    Shortcut Module built")

        logging.info("    Adding Layers...")
        for component in [edge_fed, core, access_points, radio, iot_devices, shortcut]:
            self.add_component(component)
        logging.info("    Layers added")

        logging.info("    Coupling Layers...")
        self.add_coupling(edge_fed.output_crosshaul, shortcut.input_xh)
        for edc in edc_ids_list:
            self.add_coupling(shortcut.outputs_xh[edc], edge_fed.inputs_crosshaul[edc])

        self.add_coupling(core.output_crosshaul, shortcut.input_xh)
        for function in core_ids_list:
            self.add_coupling(shortcut.outputs_xh[function], core.inputs_crosshaul[function])

        self.add_coupling(access_points.output_crosshaul, shortcut.input_xh)
        self.add_coupling(access_points.output_radio_bc, radio.input_pbch)
        self.add_coupling(access_points.output_radio_control_dl, shortcut.input_radio_control)
        self.add_coupling(access_points.output_radio_transport_dl, shortcut.input_radio_transport)
        for ap in ap_ids_list:
            self.add_coupling(shortcut.outputs_xh[ap], access_points.inputs_crosshaul[ap])
            self.add_coupling(shortcut.outputs_radio_control[ap], access_points.inputs_radio_control_ul[ap])
            self.add_coupling(shortcut.outputs_radio_transport[ap], access_points.inputs_radio_transport_ul[ap])

        self.add_coupling(iot_devices.output_repeat_location, access_points.input_repeat_pss)
        self.add_coupling(iot_devices.output_radio_control_ul, shortcut.input_radio_control)
        self.add_coupling(iot_devices.output_radio_transport_ul, shortcut.input_radio_transport)
        for ue in ue_ids_list:
            self.add_coupling(radio.outputs_pbch[ue], iot_devices.inputs_radio_bc[ue])
            self.add_coupling(shortcut.outputs_radio_control[ue], iot_devices.inputs_radio_control_dl[ue])
            self.add_coupling(shortcut.outputs_radio_transport[ue], iot_devices.inputs_radio_transport_dl[ue])
        logging.info("    Layers Coupled")

        logging.info("    Adding and Coupling Transducers...")
        for delay_transducer in ue_delay_transducers:
            self.add_component(delay_transducer)
            self.add_coupling(iot_devices.output_service_delay_report, delay_transducer.input_service_delay_report)
        for edge_fed_transducer in edc_transducers:
            self.add_component(edge_fed_transducer)
            self.add_coupling(edge_fed.output_edc_report, edge_fed_transducer.input_edc_report)
        logging.info("    Transducers Added and Coupled")


class MercuryLite(Coupled):
    def __init__(self, name, edge_fed: EdgeFederation, core: CoreLite, iot_devices: IoTDevicesLite, mobility: Nodes,
                 ue_delay_transducers, edc_transducers):
        super().__init__(name)

        logging.info("    Building Multiplexer Module...")
        mux = NetworkMultiplexer([*edge_fed.edcs, core.sdn_controller_id, *iot_devices.ue_ids])
        logging.info("    Multiplexer Module built")

        logging.info("    Adding Layers...")
        for component in [edge_fed, core, iot_devices, mobility, mux]:
            self.add_component(component)
        logging.info("    Layers added")

        logging.info("    Coupling Layers...")
        self.add_coupling(edge_fed.output_crosshaul, mux.input)
        self.add_coupling(core.output_network, mux.input)
        self.add_coupling(iot_devices.output_network, mux.input)
        self.add_coupling(mobility.output_node_location, core.input_node_location)
        for edc_id in edge_fed.edcs:
            self.add_coupling(mux.outputs[edc_id], edge_fed.inputs_crosshaul[edc_id])
        self.add_coupling(mux.outputs[core.sdn_controller_id], core.input_network)
        for ue_id in iot_devices.ue_ids:
            self.add_coupling(mux.outputs[ue_id], iot_devices.inputs_network[ue_id])
        logging.info("    Layers Coupled")

        logging.info("    Adding and Coupling Transducers...")
        for delay_transducer in ue_delay_transducers:
            self.add_component(delay_transducer)
            self.add_coupling(iot_devices.output_service_delay_report, delay_transducer.input_service_delay_report)
        for edge_fed_transducer in edc_transducers:
            self.add_component(edge_fed_transducer)
            self.add_coupling(edge_fed.output_edc_report, edge_fed_transducer.input_edc_report)
        logging.info("    Transducers Added and Coupled")
