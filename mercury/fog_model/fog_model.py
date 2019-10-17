import datetime
import os
import logging
from xdevs.models import Coupled
from xdevs.sim import Coordinator
from .common.packet.application.service import ServiceConfiguration
from .common.packet.application.federation_management import FederationManagementConfiguration
from .common.packet.application.ran import RadioAccessNetworkConfiguration
from .common.packet.network import NetworkPacketConfiguration
from .common.edge_fed import EdgeDataCenterConfiguration, EdgeFederationControllerConfiguration, \
    ProcessingUnitConfiguration, ProcessingUnitPowerModel
from .edge_fed import EdgeFederation
from .common.core import CoreLayerConfiguration, SDNStrategy
from .core import Core
from .common.crosshaul import CrosshaulConfiguration, CrosshaulTransceiverConfiguration
from .crosshaul import Crosshaul
from .common.access_points import AccessPointConfiguration
from .access_points import AccessPoints
from .common.radio import RadioConfiguration, RadioAntennaConfig, FrequencyDivisionStrategy
from .radio import Radio
from .common.mobility import UEMobilityConfiguration
from .common.iot_devices import UserEquipmentConfiguration, IoTDevicesLayerConfiguration
from .iot_devices import IoTDevices
from .transducers.delay_transducer import PerceivedDelayTransducer
from .transducers.edge_fed_transducer import EdgeFederationTransducer
from .transducers.radio_transducer import RadioTransducer
from ..visualization import *

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
        self.p_units_config = dict()
        self.services_config = dict()

        self.edcs_config = dict()
        self.aps_config = dict()
        self.ues_config = dict()
        self.fed_controller_config = None

        self.core_config = None
        self.sdn_strategy = None
        self.crosshaul_config = None
        self.radio_config = None
        self.max_guard_time = 0

        self.delay_file_path = None
        self.edc_file_path = None
        self.ul_file_path = None
        self.dl_file_path = None

    def define_rac_config(self, header=0, pss_period=0, rrc_period=0, timeout=0.5):
        """
        Define configuration for all the services related with radio access operations.

        :param int header: size (in bits) of the header of radio access application messages
        :param float pss_period: period (in seconds) of Primary Synchronization Signals
        :param float rrc_period: period (in seconds) of Radio Resource Control Signals
        :param float timeout: time (in seconds) to wait before an unacknowledged message is considered timed out
        """
        self.rac_config = RadioAccessNetworkConfiguration(header, pss_period, rrc_period, timeout)

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

    def define_p_unit_config(self, p_unit_id, dvfs_table=None, std_to_spec_u=1, t_off_on=0, t_on_off=0, t_operation=0,
                             power_model=None):
        """
        Define a new Processing Unit type. This method should be invoked for every hardware to be used in an EDC.

        :param str p_unit_id: Processing Unit type ID. It must be unique.
        :param dict dvfs_table: DVFS table. Keys are maximum specific utilization factor for using this DVFS
                                configuration. Values are hardware configuration for the given DVFS configuration
        :param float std_to_spec_u: Processing Unit standard-to-specific utilization factor relationship
        :param float t_off_on: time required for the processing unit to switch on [s]
        :param float t_on_off: time required for the processing unit to switch off [s]
        :param float t_operation: time required for the processing unit to perform an operation [s]
        :param ProcessingUnitPowerModel power_model: Processing unit power model
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if p_unit_id in self.p_units_config:
            raise AssertionError("Processing Unit ID matches with other already defined")
        p_unit_config = ProcessingUnitConfiguration(p_unit_id, dvfs_table, std_to_spec_u, t_off_on, t_on_off,
                                                    t_operation, power_model)
        self.p_units_config[p_unit_id] = p_unit_config

    def define_service_config(self, service_id, service_u, header, generation_rate, packaging_time, min_closed_t,
                              min_open_t, service_timeout, window_size=1):
        """
        Define Service to be ran by UEs

        :param str service_id: Service configuration ID. It must be unique among all the services defined in the model
        :param float service_u: Standard EDC utilization factor required by the service
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

    def define_fed_controller_config(self, controller_id, controller_location, crosshaul_transceiver_config):
        """
        Define federation controller configuration for Mercury model

        :param str controller_id: Federation Controller ID
        :param tuple controller_location: Federation Controller ue_location <x, y> (in meters)
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver_config: crosshaul transceiver configuration
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.fed_controller_config = EdgeFederationControllerConfiguration(controller_id, controller_location,
                                                                           crosshaul_transceiver_config)

    def add_edc_config(self, edc_id, edc_location, crosshaul_transceiver_config, r_manager_config, p_units_id_list,
                       base_temp=298):
        """
        :param str edc_id: ID of the Edge Data Center
        :param tuple edc_location: Access Point coordinates <x, y> (in meters)
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver_config: Crosshaul transceiver configuration
        :param list p_units_id_list: Configuration list of Processing Units that compose the EDC
        :param ResourceManagerConfiguration r_manager_config: Resource Manager Configuration
        :param float base_temp: Edge Data Center base temperature (in Kelvin)
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if edc_id in self.edcs_config:
            raise AssertionError("Edge Data Center already defined")
        for p_unit in p_units_id_list:
            if p_unit not in self.p_units_config:
                raise AssertionError("Processing Unit that conforms the EDC is not defined")
        p_units_config_list = [self.p_units_config[p_unit_id] for p_unit_id in p_units_id_list]

        new_edc = EdgeDataCenterConfiguration(edc_id, edc_location, crosshaul_transceiver_config, r_manager_config,
                                              p_units_config_list, base_temp)
        self.edcs_config[edc_id] = new_edc

    def add_core_config(self, amf_id, sdn_controller_id, core_location, crosshaul_transceiver_config, edc_slicing=None,
                        congestion=100, sdn_strategy=None):
        """
        Add core_config layer to Mercury model

        :param str amf_id: Access and Mobility Management Function ID
        :param str sdn_controller_id: Software-Defined Network Function ID
        :param tuple core_location: Core network elements (SDN controller, AMF) ue_location (x, y) [m]
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver_config: Crosshaul transceiver configuration
        :param dict edc_slicing: Maximum utilization factor for an EDC to be considered as available
        :param float congestion: minimum utilization (in %) for considering an EDC congested (0 <= congestion <= 100)
        :param SDNStrategy sdn_strategy: SDN Controller configuration
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        # If edc_slicing is not defined, make all EDCs 100% available for all the services
        if edc_slicing is None:
            edc_slicing = dict()
            for edc_id in self.edcs_config:
                edc_slicing[edc_id] = dict()
                for service_id in self.services_config:
                    edc_slicing[edc_id][service_id] = 100

        for edc_id, slicing in edc_slicing.items():
            if edc_id not in self.edcs_config:
                raise AssertionError("EDC in slicing configuration is not defined.")
            for service_id, max_u in slicing.items():
                if service_id not in self.services_config:
                    raise AssertionError("Service configuration is not defined.")
                if 0 < max_u < 100:
                    raise AssertionError("Maximum utilization factor is not valid.")

        self.sdn_strategy = sdn_strategy
        self.core_config = CoreLayerConfiguration(amf_id, sdn_controller_id, core_location,
                                                  crosshaul_transceiver_config, edc_slicing, congestion, sdn_strategy)

    def add_crosshaul_config(self, prop_speed=0, penalty_delay=0, ul_frequency=193414489e6,
                             dl_frequency=193414489e6, ul_attenuator=None, dl_attenuator=None, header=0):
        """
        Add Crosshaul layer to Mercury model

        :param float prop_speed: Propagation speed (in m/s)
        :param float penalty_delay: Penalty delay (in s)
        :param float ul_frequency: up link carrier frequency of messages sent through the crosshaul network
        :param float dl_frequency: down link carrier frequency for messages sent through the crosshaul network
        :param Attenuator ul_attenuator: Up Link attenuator
        :param Attenuator dl_attenuator: Down Link attenuator
        :param int header: size (in bits) of the header of physical messages
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.crosshaul_config = CrosshaulConfiguration(prop_speed, penalty_delay, ul_frequency, dl_frequency,
                                                       ul_attenuator, dl_attenuator, header)

    def add_ap_config(self, ap_id, ap_location, crosshaul_transceiver_config, antenna_power, antenna_gain,
                      antenna_temperature, antenna_sensitivity):
        """
        Access Point Configuration

        :param str ap_id: ID of the Access Point
        :param tuple ap_location: Access Point coordinates <x, y> (in meters)
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver_config: crosshaul transceiver configuration
        :param float antenna_power: antenna transmitting power (in dBm)
        :param float antenna_gain: antenna gain (in dB)
        :param float antenna_temperature: antenna's equivalent noise temperature (in K)
        :param antenna_sensitivity: antenna sensitivity (in dBm) <NOT IMPLEMENTED YET>
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if ap_id in self.aps_config:
            raise AssertionError("Access Point already defined")
        radio_antenna = RadioAntennaConfig(antenna_power, antenna_gain, None, None, antenna_temperature,
                                           antenna_sensitivity)
        new_ap = AccessPointConfiguration(ap_id, ap_location, radio_antenna, crosshaul_transceiver_config)
        self.aps_config[ap_id] = new_ap

    def add_radio_config(self, frequency=33e9, bandwidth=100e6, division_strategy=None, prop_speed=0,
                         penalty_delay=0, attenuator=None, header=0, ul_mcs=None, dl_mcs=None):
        """
        Radio Layer Configuration

        :param float frequency: carrier frequency for physical channels
        :param float bandwidth: channel bandwidth (in Hz)
        :param FrequencyDivisionStrategy division_strategy: Frequency division strategy
        :param float prop_speed: propagation speed (in m/s)
        :param float penalty_delay: penalty delay (in seconds)
        :param Attenuator attenuator: attenuator function
        :param int header: physical messages service_header size
        :param dict ul_mcs: Modulation and codification Scheme table for up link
        :param dict dl_mcs: Modulation and codification Scheme table for down link
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.radio_config = RadioConfiguration(frequency, bandwidth, division_strategy, prop_speed, penalty_delay,
                                               attenuator, header, ul_mcs, dl_mcs)

    def add_ue_config(self, ue_id, services_id_list, ue_mobility_config, antenna_power, antenna_gain,
                      antenna_temperature, antenna_sensitivity):
        """
        User Equipment Configuration

        :param str ue_id: ID of the User Equipment
        :param list services_id_list: List of the configuration of all the services_config within a User Equipment
        :param UEMobilityConfiguration ue_mobility_config: User Equipment Mobility Configuration
        :param float antenna_power: antenna transmitting power (in dBm)
        :param float antenna_gain: antenna gain (in dB)
        :param float antenna_temperature: antenna's equivalent noise temperature (in K)
        :param antenna_sensitivity: antenna sensitivity (in dBm) <NOT IMPLEMENTED YET>
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if ue_id in self.ues_config:
            raise AssertionError('User Equipment ID already defined')
        for service_id in services_id_list:
            if service_id not in self.services_config:
                raise AssertionError("Service that conforms the UE is not defined")
        service_config_list = [self.services_config[service_id] for service_id in services_id_list]

        antenna_config = RadioAntennaConfig(antenna_power, antenna_gain, None, None, antenna_temperature,
                                            antenna_sensitivity)
        new_ue = UserEquipmentConfiguration(ue_id, service_config_list, ue_mobility_config, antenna_config)
        self.ues_config[ue_id] = new_ue

    def set_max_guard_time(self, max_guard_time):
        """
        Add a guard time generator in order to prevent from similar, simultaneous UE behaviour

        :param float max_guard_time: upper limit of the uniform distribution
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.max_guard_time = max_guard_time

    def add_delay_transducer(self, file_path):
        """
        Add Delay transducer to Mercury model (this module is optional. Add it only if you want to capture UE delay).

        :param file_path: File path for CSV file committed to store UE delay data
        :type file_path str
        :raises FileExistsError
        """
        # If file already exists, ask before erasing its content
        if os.path.isfile(file_path):
            raise FileExistsError('File already exists. Please, erase file or change destination file path.')
        self.delay_file_path = file_path

    def add_edc_transducer(self, file_path):
        """
        Add EDC transducer to Mercury model.

        :param file_path: File path for CSV file committed to store EDC data
        :type file_path str
        :raises FileExistsError
        """
        # If file already exists, ask before erasing its content
        if os.path.isfile(file_path):
            raise FileExistsError('File already exists. Please, erase file or change destination file path.')
        self.edc_file_path = file_path

    def add_radio_transducer(self, ul_file_path, dl_file_path):
        """
        Add radio transducer to Mercury model.

        :param ul_file_path: File path for CSV file committed to store uplink radio_config data
        :type ul_file_path: str
        :param dl_file_path: File path for CSV file committed to store downlink radio_config data
        :type dl_file_path: str
        :raises FileExistsError
        """
        # If file already exists, ask before erasing its content
        if os.path.isfile(ul_file_path) or os.path.isfile(dl_file_path):
            raise FileExistsError('File already exists. Please, erase file or change destination file path.')
        self.ul_file_path = ul_file_path
        self.dl_file_path = dl_file_path

    def build(self):
        """
        Build Mercury model
        """
        if self.rac_config is None:
            raise Exception
        if self.network_config is None:
            raise Exception
        if self.fed_mgmt_config is None:
            raise Exception

        logging.info("Mercury: Building Layers...")

        logging.info("    Building Edge Federation Layer...")
        federation = EdgeFederation(self.name + '_edge_fed', self.edcs_config, self.fed_controller_config,
                                    self.services_config, self.fed_mgmt_config, self.network_config,
                                    self.crosshaul_config, self.core_config.sdn_controller_id)
        logging.info("    Edge Federation Layer built")

        logging.info("    Building Core Layer...")
        aps_location = {ap_id: ap_config.ap_location for ap_id, ap_config in self.aps_config.items()}
        services_id = [service_id for service_id in self.services_config]
        edcs_location = {edc_id: edc_config.edc_location for edc_id, edc_config in self.edcs_config.items()}
        core = Core(self.name + '_core', self.core_config, self.rac_config, self.fed_mgmt_config, self.network_config,
                    self.crosshaul_config, aps_location, edcs_location, self.fed_controller_config.controller_id,
                    services_id)
        logging.info("    Core Layer built")

        logging.info("    Building Crosshaul Layer...")
        fed_controller_location = {self.fed_controller_config.controller_id:
                                   self.fed_controller_config.controller_location}
        amf_location = {self.core_config.amf_id: self.core_config.core_location}
        sdn_controller_location = {self.core_config.sdn_controller_id: self.core_config.core_location}
        crosshaul = Crosshaul(self.name + '_crosshaul', self.crosshaul_config, aps_location, edcs_location,
                              fed_controller_location, amf_location, sdn_controller_location)
        logging.info("    Crosshaul Layer built")

        logging.info("    Building Access Points Layer...")
        for ap_config in self.aps_config.values():
            ap_config.radio_antenna_config.tx_mcs = self.radio_config.dl_mcs_list
            ap_config.radio_antenna_config.rx_mcs = self.radio_config.ul_mcs_list
        access = AccessPoints(self.name + '_access', self.aps_config, self.core_config.amf_id, self.rac_config,
                              self.network_config, self.crosshaul_config, self.radio_config)
        logging.info("    Access Points Layer built")

        logging.info("    Building Radio Layer...")
        ues_location = {ue.ue_id: ue.ue_mobility_config.position for ue in self.ues_config.values()}
        radio = Radio(self.name + '_radio', self.radio_config, ues_location, aps_location)
        logging.info("    Radio Layer built")

        logging.info("    Building IoT Devices Layer...")
        for ue_config in self.ues_config.values():
            ue_config.antenna_config.tx_mcs = self.radio_config.ul_mcs_list
            ue_config.antenna_config.rx_mcs = self.radio_config.dl_mcs_list
        iot_config = IoTDevicesLayerConfiguration(self.ues_config, self.max_guard_time)
        iot_devices = IoTDevices(self.name + '_iot_devices', iot_config, self.rac_config, self.network_config,
                                 self.radio_config)
        logging.info("    IoT Devices Layer built")

        logging.info("    Building Transducers...")
        delay_transducer = None
        if self.delay_file_path is not None:
            delay_transducer = PerceivedDelayTransducer(self.name + '_delay_sniffer', self.delay_file_path)

        edc_transducer = None
        if self.edc_file_path is not None:
            edc_transducer = EdgeFederationTransducer(self.name + '_edc_sniffer', self.edc_file_path)

        radio_transducer = None
        if self.dl_file_path is not None and self.ul_file_path is not None:
            radio_transducer = RadioTransducer(self.name + '_radio_sniffer', self.ul_file_path, self.dl_file_path)
        logging.info("    Transducers built")

        logging.info("Mercury: Layers built successfully")

        logging.info("Mercury: Building model...")
        self.model = MercuryFogModelCoupled(self.name, federation, core, crosshaul, access, radio, iot_devices,
                                            delay_transducer, edc_transducer, radio_transducer)
        logging.info("Mercury: model built successfully")

    def initialize_coordinator(self):
        """
        Initialize Mercury xdevs coordinator
        """
        if self.model is None:
            raise AssertionError('Mercury model has not been built yet.')
        logging.info("Mercury: Starting Coordinator initialization...")
        self.coordinator = Coordinator(self.model)
        self.coordinator.initialize()
        logging.info("Mercury: Coordinator initialization finished successfully")

    def start_simulation(self, time_interv=10000):
        """
        Start Mercury model simulation
        """
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
        if self.delay_file_path is None:
            raise ValueError('No delay file path is registered')
        if not os.path.isfile(self.delay_file_path):
            raise FileNotFoundError('File containing delay data does not exist')
        plot_ue_service_delay(self.delay_file_path, alpha=alpha)

    def plot_edc_utilization(self, stacked=False, alpha=1):
        if self.edc_file_path is None:
            raise ValueError('No EDC utilization factor file path is registered')
        if not os.path.isfile(self.edc_file_path):
            raise FileNotFoundError('File containing EDC data does not exist')
        plot_edc_utilization(self.edc_file_path, stacked=stacked, alpha=alpha)

    def plot_edc_power(self, stacked=False, alpha=1):
        if self.edc_file_path is None:
            raise ValueError('No EDC file path is registered')
        if not os.path.isfile(self.edc_file_path):
            raise FileNotFoundError('File containing EDC data does not exist')
        plot_edc_power(self.edc_file_path, stacked=stacked, alpha=alpha)

    def plot_ul_bw(self, alpha=1):
        if self.ul_file_path is None:
            raise ValueError('No Uplink file path is registered')
        if not os.path.isfile(self.ul_file_path):
            raise FileNotFoundError('File containing Uplink data does not exist')
        plot_bw(self.ul_file_path, link='Uplink', alpha=alpha)

    def plot_dl_bw(self, alpha=1):
        if self.dl_file_path is None:
            raise ValueError('No Downlink file path is registered')
        if not os.path.isfile(self.dl_file_path):
            raise FileNotFoundError('File containing Downlink data does not exist')
        plot_bw(self.dl_file_path, link='Downlink', alpha=alpha)


class MercuryFogModelCoupled(Coupled):
    def __init__(self, name, edge_fed, core, crosshaul, access_points, radio, iot_devices, delay_transducer=None,
                 edge_fed_transducer=None, radio_transducer=None):
        """
        :param str name: xDEVS model name
        :param EdgeFederation edge_fed: Edge Federation Layer Model
        :param Core core: Core Network Layer Model
        :param Crosshaul crosshaul: Crosshaul Network Layer Model
        :param AccessPoints access_points: Access Points Layer Model
        :param Radio radio: Radio Network Layer Model
        :param IoTDevices iot_devices: IoT devices Layer Model
        :param PerceivedDelayTransducer delay_transducer: User Equipment Delay transducer
        :param EdgeFederationTransducer edge_fed_transducer: Edge Data Center Status transducer
        :param RadioTransducer radio_transducer: Radio Interface transducer

        """
        super().__init__(name)

        # Add components
        logging.info("    Adding Layers...")
        self.add_component(edge_fed)
        self.add_component(core)
        self.add_component(crosshaul)
        self.add_component(access_points)
        self.add_component(radio)
        self.add_component(iot_devices)
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
        self.internal_transducers(iot_devices, delay_transducer, edge_fed, edge_fed_transducer, access_points,
                                  radio_transducer)
        logging.info("    Transducers Added and Coupled")

    def internal_edge_fed_crosshaul(self, edge_fed, crosshaul):
        """
        :param EdgeFederation edge_fed:
        :param Crosshaul crosshaul:
        """
        self.add_coupling(crosshaul.output_edc_ul, edge_fed.input_edc_crosshaul_ul)
        self.add_coupling(crosshaul.output_fed_controller_ul, edge_fed.input_fed_controller_crosshaul_ul)
        self.add_coupling(edge_fed.output_crosshaul_dl, crosshaul.input_crosshaul_dl)
        self.add_coupling(edge_fed.output_crosshaul_ul, crosshaul.input_crosshaul_ul)

    def internal_core_crosshaul(self, core, crosshaul):
        """
        :param Core core:
        :param Crosshaul crosshaul:
        """
        self.add_coupling(crosshaul.output_amf_ul, core.input_amf_ul)
        self.add_coupling(crosshaul.output_sdn_controller_ul, core.input_sdn_controller_ul)
        self.add_coupling(core.output_crosshaul_dl, crosshaul.input_crosshaul_dl)

    def internal_crosshaul_access_points(self, crosshaul, access_points):
        """
        :param Crosshaul crosshaul:
        :param AccessPoints access_points:
        """
        self.add_coupling(crosshaul.output_ap_dl, access_points.input_crosshaul_dl)
        self.add_coupling(crosshaul.output_ap_ul, access_points.input_crosshaul_ul)
        self.add_coupling(access_points.output_crosshaul_dl, crosshaul.input_crosshaul_dl)
        self.add_coupling(access_points.output_crosshaul_ul, crosshaul.input_crosshaul_ul)

    def internal_access_points_radio(self, access_points, radio):
        """
        :param AccessPoints access_points:
        :param Radio radio:
        """
        self.add_coupling(radio.output_radio_pucch, access_points.input_radio_control_ul)
        self.add_coupling(radio.output_radio_pusch, access_points.input_radio_transport_ul)
        self.add_coupling(access_points.output_radio_bc, radio.input_radio_pbch)
        self.add_coupling(access_points.output_radio_control_dl, radio.input_radio_pxcch)
        self.add_coupling(access_points.output_radio_transport_dl, radio.input_radio_pxsch)

    def internal_radio_iot_devices(self, radio, iot_devices):
        """
        :param Radio radio:
        :param IoTDevices iot_devices:
        """
        self.add_coupling(radio.output_radio_pbch, iot_devices.input_radio_bc)
        self.add_coupling(radio.output_radio_pdcch, iot_devices.input_radio_control_dl)
        self.add_coupling(radio.output_radio_pdsch, iot_devices.input_radio_transport_dl)
        self.add_coupling(iot_devices.output_new_location, radio.input_new_location)
        self.add_coupling(iot_devices.output_radio_control_ul, radio.input_radio_pxcch)
        self.add_coupling(iot_devices.output_radio_transport_ul, radio.input_radio_pxsch)

    def internal_access_points_iot_devices(self, access_points, iot_devices):
        """
        :param AccessPoints access_points:
        :param IoTDevices iot_devices:
        """
        self.add_coupling(iot_devices.output_new_location, access_points.input_new_ue_location)

    def internal_transducers(self, iot_devices, delay_transducer, edge_fed, edge_fed_transducer, access_points,
                             radio_transducer):
        """
        :param IoTDevices iot_devices:
        :param PerceivedDelayTransducer delay_transducer:
        :param EdgeFederation edge_fed:
        :param EdgeFederationTransducer edge_fed_transducer:
        :param AccessPoints access_points:
        :param RadioTransducer radio_transducer:
        """
        if delay_transducer is not None:
            self.add_component(delay_transducer)
            self.add_coupling(iot_devices.output_service_delay_report, delay_transducer.input_service_delay_report)
        if edge_fed_transducer is not None:
            self.add_component(edge_fed_transducer)
            self.add_coupling(edge_fed.output_edc_report, edge_fed_transducer.input_edc_report)
        if radio_transducer is not None:
            self.add_component(radio_transducer)
            self.add_coupling(access_points.output_ul_mcs, radio_transducer.input_new_ul_mcs)
            self.add_coupling(iot_devices.output_dl_mcs, radio_transducer.input_new_dl_mcs)
