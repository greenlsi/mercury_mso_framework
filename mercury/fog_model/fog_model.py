import datetime
from mercury.logger import logger as logging
from typing import Any, Dict, Optional, Set, Tuple, Type
from xdevs.sim import Coordinator, INFINITY

from .engines import MercuryFogModel, MercuryFogModelShortcut, MercuryLite

from mercury.config.edcs import ProcessingUnitConfig, CoolerConfig, ResourceManagerConfig, EdgeDataCenterConfig, \
    EdgeFederationControllerConfig, EdgeFederationConfig
from .edcs import EdgeDataCenters

from mercury.config.smart_grid import SmartGridConfig, EnergyProviderConfig,\
    ConsumerConfig, PowerSourceConfig, EnergyStorageConfig
from .smart_grid import SmartGrid

from mercury.config.iot_devices import UserEquipmentConfig, IoTDevicesConfig, ServiceConfig
from .iot_devices import IoTDevices, IoTDevicesLite

from mercury.config.core import CoreConfig
from .core import Core

from mercury.config.crosshaul import CrosshaulConfig
from .crosshaul import Crosshaul
from mercury.config.aps import AccessPointConfig
from .aps import AccessPoints
from mercury.config.radio import RadioConfig, RadioAccessNetworkConfig
from .radio import Radio, RadioShortcut

from ..visualization import *
from mercury.plugin import *
from mercury.config.network import PacketConfig, NodeConfig, LinkConfig, TransceiverConfig
from .network.network import DynamicNodesMobility


class FogModel:
    """
    Edge Computing for Data Stream Analytics Model

    :param str name: Mercury Edge model instance name
    """
    def __init__(self, name='fog_model'):
        self.name = name
        self.model = None
        self.coordinator = None

        self.cooler_configs: Dict[str, CoolerConfig] = dict()
        self.pu_configs: Dict[str, ProcessingUnitConfig] = dict()
        self.srv_configs: Dict[str, ServiceConfig] = dict()

        self.edc_configs: Dict[str, EdgeDataCenterConfig] = dict()
        self.ap_configs: Dict[str, AccessPointConfig] = dict()
        self.ue_configs: Dict[str, UserEquipmentConfig] = dict()

        self.edcs_congestion: float = 100
        self.edcs_slicing: Optional[Dict[str, Dict[str, float]]] = None
        self.edcs_controller_config = None
        self.core_config: Optional[CoreConfig] = None
        self.xh_config = None
        self.radio_config = None
        self.max_guard_time = 0

        self.energy_provider_configs: Dict[str, EnergyProviderConfig] = dict()
        self.energy_consumer_configs: Dict[str, ConsumerConfig] = dict()

        # Transducers to be added
        self.transducers_config: Dict[str, Tuple[str, Dict[str, Any]]] = dict()

    def define_rac_config(self, header: int = 0, pss_period: float = 0, rrc_period: float = 0,
                          timeout: float = 0.5, bypass_amf: bool = False):
        """
        Define configuration for all the services related with radio access operations.

        :param header: size (in bits) of the header of radio access application messages
        :param pss_period: period (in seconds) of Primary Synchronization Signals
        :param rrc_period: period (in seconds) of Radio Resource Control Signals
        :param timeout: time (in seconds) to wait before an unacknowledged message is considered timed out
        :param bypass_amf: if True, APs are in charge of access control decisions
        """
        PacketConfig.RAN_MGMT_HEADER = header
        RadioAccessNetworkConfig.pss_period = pss_period
        RadioAccessNetworkConfig.rrc_period = rrc_period
        RadioAccessNetworkConfig.timeout = timeout
        RadioAccessNetworkConfig.bypass_amf = bypass_amf

    @staticmethod
    def define_fed_mgmt_config(header: int = 0, content: int = 0):
        """
        Define configuration for all federation management-related messages.

        :param header: size (in bits) of the header of radio access application messages
        :param content: size (in bits) of the body of EDC report messages
        """
        PacketConfig.EDGE_FED_MGMT_HEADER = header
        PacketConfig.EDGE_FED_MGMT_CONTENT = content

    @staticmethod
    def define_network_config(header: int = 0):
        """
        Define configuration for all the network packets.

        :param header: size (in bits) of the header of network packets.
        """
        PacketConfig.NET_HEADER = header

    @staticmethod
    def add_custom_service_demand_estimator(key: str, model: Type[DemandEstimationGenerator]):
        """
        Adds a custom service demand estimator model to the corresponding factory
        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_demand_estimator(key, model)

    @staticmethod
    def add_custom_srv_session_profile(key: str, model: Type[ServiceSessionProfile]):
        """
        Adds a custom service profile model to the corresponding factory
        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_srv_session_profile(key, model)

    @staticmethod
    def add_custom_srv_duration_profile(key: str, model: Type[ServiceSessionDuration]):
        """
        Adds a custom service profile model to the corresponding factory
        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_srv_session_duration(key, model)

    @staticmethod
    def add_custom_srv_request_profile(key: str, model: Type[ServiceRequestProfile]):
        """
        Adds a custom service profile model to the corresponding factory
        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_srv_request_profile(key, model)

    # TODO improve service-related stuff
    def define_srv_config(self, service_id: str, header: int, content: int,  req_profile_name: str,
                          req_profile_config: Dict[str, Any], req_timeout: float, max_batches: int,
                          session_profile_name: str, session_profile_config: Dict[str, Any], session_timeout: float,
                          session_duration_name: str, session_duration_config: Dict[str, Any],
                          demand_estimator_name: Optional[str] = None,
                          demand_estimator_config: Optional[Dict[str, Any]] = None):
        """
        Define configuration  for services.
        :param service_id: ID of the service.
        :param header: size (in bits) of headers of a given service.
        :param content: size (in bits) of content of data messages of a given service.
        :param req_profile_name: name of the service request profile model.
        :param req_profile_config: any additional configuration parameter for the service request profile model.
        :param req_timeout: time (in seconds) to wait before considering a request without response timed out.
        :param max_batches: maximum number of requests that can be sent simultaneously.
        :param session_profile_name: name of the service session profile model.
        :param session_profile_config: any additional configuration parameter for the service session profile model.
        :param session_timeout: time (in seconds) to wait before considering an open session without response timed out.
        :param session_duration_name: name of the service session duration model.
        :param session_duration_config: any additional configuration parameter for the service session duration model.
        :param demand_estimator_name: name of the service demand estimator model.
        :param demand_estimator_config: any additional configuration parameter for the service demand estimator model.
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if service_id in self.srv_configs:
            raise AssertionError("Service ID already defined")
        self.srv_configs[service_id] = ServiceConfig(service_id, header, content,  req_profile_name, req_profile_config,
                                                     req_timeout, max_batches, session_profile_name,
                                                     session_profile_config, session_timeout, session_duration_name,
                                                     session_duration_config, demand_estimator_name,
                                                     demand_estimator_config)

    @staticmethod
    def add_custom_rack_cooler_power_model(key: str, model: Type[EdgeDataCenterCoolerPowerModel]):
        """
        Adds a custom rack cooler power model to the corresponding factory

        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_edc_cooler_pwr(key, model)

    @staticmethod
    def add_custom_rack_cooler_temp_model(key: str, model: Type[EdgeDataCenterCoolerTemperatureModel]):
        """
        Adds a custom rack cooler temperature model to the corresponding factory

        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_edc_cooler_temp(key, model)

    def define_edc_rack_cooler_type(self, cooler_id: str, pwr_model_name: str = None,
                                    pwr_model_config: Dict[str, Any] = None, temp_model_name: str = None,
                                    temp_model_config: Dict[str, Any] = None):
        """
        Define a rack cooler type.
        :param cooler_id: ID for the rack type
        :param pwr_model_name: Heat dissipation power model name for the rack type
        :param pwr_model_config: Power model configuration parameters
        :param temp_model_name: Temperature model name for the rack type
        :param temp_model_config: Temperature model configuration parameters
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if cooler_id in self.cooler_configs:
            raise AssertionError("EDC Rack ID matches with other already defined")
        self.cooler_configs[cooler_id] = CoolerConfig(cooler_id, pwr_model_name, pwr_model_config,
                                                      temp_model_name, temp_model_config)

    @staticmethod
    def add_custom_pu_power_model(key: str, model: Type[ProcessingUnitPowerModel]):
        """
        Adds a custom processing unit power model to the corresponding factory.
        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_edc_pu_pwr(key, model)

    @staticmethod
    def add_custom_pu_temp_model(key: str, model: Type[ProcessingUnitTemperatureModel]):
        """
        Adds a custom processing unit temperature model to the corresponding factory.
        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_edc_pu_temp(key, model)

    def define_pu_type_config(self, pu_type: str, services: Dict[str, Dict[str, float]],
                              dvfs_table: Optional[Dict[float, Any]] = None, t_on: float = 0,
                              t_off: float = 0, sched_name: str = 'fcfs', sched_config: Optional[Dict[str, Any]] = None,
                              pwr_model_name: str = None, pwr_model_config: Optional[Dict[str, Any]] = None,
                              temp_model_name: str = None, temp_model_config: Optional[Dict[str, Any]] = None):
        """
        Define a new Processing Unit type.

        :param pu_type: Processing Unit type ID. It must be unique.
        :param dvfs_table: DVFS table. Keys are maximum specific std_u factor for using this DVFS configuration.
                           Values are hardware configuration for the given DVFS configuration
        :param services: resource utilization depending on the service to host
        :param t_on: time required for the processing unit to switch on [s]
        :param t_off: time required for the processing unit to switch off [s]
        :param sched_name: Processing scheduling model name
        :param sched_config: Processing scheduling model configuration
        :param pwr_model_name: Processing unit power model name
        :param pwr_model_config: Processing unit power model configuration
        :param temp_model_name: Processing unit temperature model name
        :param temp_model_config: Processing unit temperature model configuration
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if pu_type in self.pu_configs:
            raise AssertionError("Processing Unit ID matches with other already defined")
        p_unit_config = ProcessingUnitConfig(pu_type, services, dvfs_table, t_on, t_off,
                                             sched_name, sched_config, pwr_model_name,
                                             pwr_model_config, temp_model_name, temp_model_config)
        self.pu_configs[pu_type] = p_unit_config

    @staticmethod
    def add_custom_edc_mapping_strategy(key: str, model: Type[MappingStrategy]):
        """
        Adds a custom EDC dispatching strategy to the corresponding factory.
        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_edc_mapping(key, model)

    @staticmethod
    def add_custom_edc_hot_standby(key: str, model: Type[HotStandbyStrategy]):
        """
        Adds a custom EDC hot standby strategy to the corresponding factory.
        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_edc_hot_standby(key, model)

    def add_edc_config(self, edc_id: str, edc_location: Tuple[float, ...], r_manager_config: ResourceManagerConfig,
                       edc_pus: Dict[str, str], cooler_id: Optional[str] = None,
                       edc_trx: Optional[TransceiverConfig] = None, env_temp: float = 298):
        """
        Adds an EDC to the scenario.
        :param edc_id: ID of the EDC
        :param edc_location: Location of the EDC
        :param edc_trx: Crosshaul transceiver used by the EDC to communicate with the rest of the scenario
        :param r_manager_config: EDC's Resource Manager configuration
        :param env_temp: Base temperature of the EDC
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if self.edcs_slicing is not None:
            raise AssertionError('Model has already defined an EDC slicing strategy. No new EDCs are allowed after.')
        if edc_id in self.edc_configs:
            raise AssertionError("Edge Data Center already defined")

        pus_config = {pu_id: self.pu_configs[pu_config] for pu_id, pu_config in edc_pus.items()}
        cooler: Optional[CoolerConfig] = self.cooler_configs[cooler_id] if cooler_id is not None else None
        new_edc = EdgeDataCenterConfig(edc_id, edc_location, r_manager_config, pus_config, cooler, edc_trx, env_temp)
        self.edc_configs[edc_id] = new_edc

    def add_edge_fed_config(self, congestion: float = 100, slicing: Optional[Dict[str, Dict[str, float]]] = None):
        self.edcs_congestion = congestion
        self.edcs_slicing = dict() if slicing is None else slicing  # TODO check that this is well-defined

    @staticmethod
    def add_custom_edc_demand_share(key: str, model: Type[DemandShare]):
        """
        Adds a custom Edge Data Center demand share model to the corresponding factory.
        :param key: ID of the custom model.
        :param model: Pointer to the custom model class.
        """
        AbstractFactory.register_edc_demand_share(key, model)

    @staticmethod
    def add_custom_edc_dyn_dispatching(key: str, model: Type[DynamicMapping]):
        """
        Adds a custom Edge Data Center dynamic dispatching function model to the corresponding factory.
        :param key: ID of the custom model.
        :param model: Pointer to the custom model class.
        """
        AbstractFactory.register_edc_dyn_dispatching(key, model)

    @staticmethod
    def add_custom_edc_dyn_hot_standby(key: str, model: Type[DynamicHotStandby]):
        """
        Adds a custom Edge Data Center dynamic hot standby function model to the corresponding factory.
        :param key: ID of the custom model.
        :param model: Pointer to the custom model class.
        """
        AbstractFactory.register_edc_dyn_hot_standby(key, model)

    @staticmethod
    def add_custom_edc_dyn_slicing(key: str, model: Type[DynamicSlicing]):
        """
        Adds a custom Edge Data Center dynamic EDC slicing policy model to the corresponding factory.
        :param key: ID of the custom model.
        :param model: Pointer to the custom model class.
        """
        AbstractFactory.register_edc_dyn_slicing(key, model)

    def add_efc_config(self, demand_share_name: str = 'equal',
                       demand_share_config: Optional[Dict[str, Any]] = None,
                       dyn_dispatching_name: Optional[str] = None,
                       dyn_dispatching_config: Optional[Dict[str, Any]] = None,
                       dyn_hot_standby_name: Optional[str] = None,
                       dyn_hot_standby_config: Optional[Dict[str, Any]] = None,
                       dyn_slicing_name: Optional[str] = None,
                       dyn_slicing_config: Optional[Dict[str, Any]] = None, cool_down: float = 0):
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if self.edcs_controller_config is not None:
            raise AssertionError("EDCs controller already defined")
        self.edcs_controller_config = EdgeFederationControllerConfig(demand_share_name, demand_share_config,
                                                                     dyn_dispatching_name, dyn_dispatching_config,
                                                                     dyn_hot_standby_name, dyn_hot_standby_config,
                                                                     dyn_slicing_name, dyn_slicing_config, cool_down)

    @staticmethod
    def add_custom_smart_grid_power_source(key: str, model: Type[PowerSource]):
        """
        Adds a custom Smart Grid power source model to the corresponding factory.
        :param key: ID of the custom model.
        :param model: Pointer to the custom model class.
        """
        AbstractFactory.register_smart_grid_source(key, model)

    @staticmethod
    def add_custom_smart_grid_provider(key: str, model: Type[EnergyProvider]):
        """
        Adds a custom Smart Grid energy provider model to the corresponding factory

        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_smart_grid_provider(key, model)

    @staticmethod
    def add_custom_smart_grid_consumption_manager(key: str, model: Type[ConsumptionManager]):
        """
        Adds a custom Smart Grid consumption manager model to the corresponding factory
        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_smart_grid_consumption_manager(key, model)

    def add_smart_grid_energy_provider(self, provider_id: str, provider_type: str,
                                       provider_config: Optional[Dict[str, Any]] = None):
        """
        Adds a smart grid energy provider
        :param provider_id: ID of the energy provider
        :param provider_type: Type of energy provider
        :param provider_config: Any additional configuration parameter for the energy provider model
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if provider_id in self.energy_provider_configs:
            raise AssertionError("Smart Grid energy provider already defined")
        self.energy_provider_configs[provider_id] = EnergyProviderConfig(provider_id, provider_type, provider_config)

    def add_smart_grid_consumer(self, consumer_id: str, provider_id: str,
                                storage_config: Optional[EnergyStorageConfig] = None,
                                consumption_manager_name: str = 'static',
                                consumption_manager_config: Optional[Dict[str, Any]] = None,
                                sources_config: Optional[Dict[str, PowerSourceConfig]] = None):
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if consumer_id in self.energy_consumer_configs:
            raise AssertionError("Smart Grid consumer already defined")
        if consumer_id not in self.edc_configs:
            raise AssertionError("Smart Grid consumer does not coincide with any EDC defined so far")
        self.energy_consumer_configs[consumer_id] = ConsumerConfig(consumer_id, provider_id, storage_config,
                                                                   consumption_manager_name,
                                                                   consumption_manager_config, sources_config)

    @staticmethod
    def add_custom_sdn_strategy(key: str, model: Type[SDNStrategy]):
        """
        Adds a custom SDN strategy model to the corresponding factory
        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_sdn_strategy(key, model)

    def add_core_config(self, core_location: Tuple[float, ...], core_trx: Optional[TransceiverConfig] = None,
                        sdn_strategy_name: str = 'closest', sdn_strategy_config: Optional[Dict[str, Any]] = None):
        """
        Add core_config layer to Mercury model.
        :param core_location: Core network elements (SDN controller, AMF) ue_location (x, y) [m].
        :param core_trx: Crosshaul transceiver configuration.
        :param sdn_strategy_name: SDN Controller name.
        :param sdn_strategy_config: Any additional SDN Controller configuration parameter.
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.core_config = CoreConfig(core_location, core_trx, sdn_strategy_name, sdn_strategy_config)

    @staticmethod
    def add_custom_link_attenuation(key: str, model: Type[Attenuation]):
        """
        Adds a custom link attenuation model to the corresponding factory

        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_network_attenuation(key, model)

    @staticmethod
    def add_custom_link_noise(key: str, model: Type[Noise]):
        """
        Adds a custom link noise model to the corresponding factory

        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_network_noise(key, model)

    def add_xh_config(self, base_link_config: Optional[LinkConfig] = None,
                      base_trx_config: Optional[TransceiverConfig] = None, header: int = 0):
        """
        Adds configuration for Crosshaul communications

        :param base_link_config: Base configuration for crosshaul links
        :param base_trx_config: Base configuration for crosshaul transceivers
        :param header: size (in bits) of message headers
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.xh_config = CrosshaulConfig(base_link_config, base_trx_config, header)

    def add_ap_config(self, ap_id: str, ap_location: Tuple[float, ...],
                      xh_trx: Optional[TransceiverConfig] = None, rad_antenna: Optional[TransceiverConfig] = None):
        """
        Adds Access Point Configuration

        :param ap_id: ID of the Access Point (it must be unique)
        :param ap_location: location of the AP expressed as a tuple (in meters)
        :param xh_trx:  AP's crosshaul transceiver configuration
        :param rad_antenna: AP's radio antenna configuration
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if ap_id in self.ap_configs:
            raise AssertionError("Access Point already defined")
        new_ap = AccessPointConfig(ap_id, ap_location, xh_trx, rad_antenna)
        self.ap_configs[ap_id] = new_ap

    @staticmethod
    def add_custom_channel_division_strategy(key: str, model: Type[ChannelDivision]):
        """
        Adds a custom channel frequency division model to the corresponding factory

        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_network_channel_division(key, model)

    @staticmethod
    def add_custom_node_mobility(key: str, model: Type[NodeMobility]):
        """
        Adds a custom node mobility model to the corresponding factory

        :param key: ID of the custom model
        :param model: Pointer to the custom model class
        """
        AbstractFactory.register_mobility(key, model)

    def add_radio_config(self, base_dl_config: Optional[LinkConfig] = None, base_ul_config: Optional[LinkConfig] = None,
                         base_ap_antenna: Optional[TransceiverConfig] = None,
                         base_ue_antenna: Optional[TransceiverConfig] = None, channel_div_name: str = 'equal',
                         channel_div_config: Optional[Dict[str, Any]] = None, header: int = 0):
        """
        Adds configuration for Radio communications.

        :param base_dl_config: Base configuration for downlink radio links
        :param base_ul_config: Base configuration for uplink radio links
        :param base_ap_antenna: Base configuration for APs' radio antennas
        :param base_ue_antenna: Base configuration for UEs' radio antennas
        :param channel_div_name: ID of the channel frequency division algorithm
        :param channel_div_config: Any additional configuration parameter of the channel frequency division algorithm
        :param header: size (in bits) of radio message headers
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.radio_config = RadioConfig(base_dl_config, base_ul_config, base_ap_antenna, base_ue_antenna,
                                        channel_div_name, channel_div_config, header)

    def add_ue_config(self, ue_id: str, services_id: Set[str], radio_antenna: TransceiverConfig = None,
                      t_start: float = 0, t_end: float = INFINITY, mobility_name: str = None,
                      mobility_config: Optional[dict] = None):
        """
        Adds User Equipment Configuration

        :param ue_id: ID of the User Equipment (it must be unique)
        :param services_id: Set of the IDs of all the services on board of the UE
        :param radio_antenna: Configuration for UE's radio antenna
        :param t_start:
        :param t_end:
        :param mobility_name: Name of the mobility module implemented by the UE
        :param mobility_config: Any additional parameter regarding node mobility
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        if ue_id in self.ue_configs:
            raise AssertionError('User Equipment ID already defined')
        for service_id in services_id:
            if service_id not in self.srv_configs:
                raise AssertionError("Service that conforms the UE is not defined")
        services_config = {service_id: self.srv_configs[service_id] for service_id in services_id}

        self.ue_configs[ue_id] = UserEquipmentConfig(ue_id, services_config, radio_antenna, t_start,
                                                     t_end, mobility_name, mobility_config)

    def set_max_guard_time(self, max_guard_time: float):
        """
        Add a guard time generator in order to prevent from similar, simultaneous UE behaviour

        :param max_guard_time: upper limit of the uniform distribution
        """
        if self.model is not None:
            raise AssertionError("Model already built. No changes are allowed after building the model")
        self.max_guard_time = max_guard_time

    def add_transducers(self, transducer_id, transducer_type: str, **kwargs):  # TODO check that transducer exists
        if transducer_id in self.transducers_config:
            raise ValueError("Transducer already defined")
        self.transducers_config[transducer_id] = (transducer_type, kwargs)

    def build(self, lite=False, shortcut=False):
        """ Build Mercury model """
        logging.debug("Mercury: Building Layers...")

        services_id = {service_id for service_id in self.srv_configs}

        logging.debug("    Building Edge Federation Layer...")
        smart_grid_active = {edc_id: edc_id in self.energy_consumer_configs for edc_id in self.edc_configs}
        edge_fed_config = EdgeFederationConfig(self.edc_configs, self.edcs_congestion,
                                               self.edcs_slicing, self.edcs_controller_config)
        federation = EdgeDataCenters(self.edc_configs, services_id, smart_grid_active, lite=lite)
        logging.debug("    Edge Federation Layer Built")

        logging.debug("    Building Core Layer...")
        aps_location = {ap_id: ap_config.ap_location for ap_id, ap_config in self.ap_configs.items()}
        core = Core(self.core_config, edge_fed_config, aps_location,
                    self.srv_configs, self.energy_consumer_configs, lite)
        logging.debug("    Core Layer Built")

        edc_nodes = dict()
        for edc_id, edc_config in self.edc_configs.items():
            assert isinstance(edc_config.crosshaul_node, NodeConfig)
            if edc_config.crosshaul_node.node_trx is None:
                assert isinstance(self.xh_config, CrosshaulConfig)
                edc_config.crosshaul_node.node_trx = self.xh_config.base_trx_config
            edc_nodes[edc_id] = edc_config.crosshaul_node

        ap_crosshaul_nodes = {ap_id: ap_config.xh_node for ap_id, ap_config in self.ap_configs.items()}
        edc_nodes = {edc_id: edc_config.crosshaul_node for edc_id, edc_config in self.edc_configs.items()}
        for node_group in [ap_crosshaul_nodes, edc_nodes]:
            for node_config in node_group.values():
                if node_config.node_trx is None:
                    node_config.node_trx = self.xh_config.base_trx_config

        ap_radio_nodes = {ap_id: ap_config.radio_node for ap_id, ap_config in self.ap_configs.items()}
        for node_config in ap_radio_nodes.values():
            if node_config.node_trx is None:
                node_config.node_trx = self.radio_config.base_ap_antenna_config

        crosshaul = None
        access = None
        radio = None

        if not lite:
            if not shortcut:
                logging.debug("    Building Crosshaul Layer...")
                crosshaul = Crosshaul(self.xh_config, ap_crosshaul_nodes, edc_nodes, self.core_config)
                logging.debug("    Crosshaul Layer built")

            logging.debug("    Building Access Points Layer...")
            access = AccessPoints(self.ap_configs)
            logging.debug("    Access Points Layer built")

            logging.debug("    Building Radio Layer...")
            if shortcut:
                radio = RadioShortcut(self.radio_config, ap_radio_nodes)
            else:
                radio = Radio(self.radio_config, ap_radio_nodes)
            logging.debug("    Radio Layer built")

        logging.debug("    Building IoT Devices Layer...")
        for ue_config in self.ue_configs.values():
            if ue_config.radio_node.node_trx is None:
                ue_config.radio_node.node_trx = self.radio_config.base_ue_antenna_config
        iot_config = IoTDevicesConfig(self.ue_configs, self.max_guard_time)
        iot_devices = IoTDevicesLite(iot_config) if lite else IoTDevices(iot_config)
        logging.debug("    IoT Devices Layer built")

        logging.debug("    Building Nodes Mobility...")
        mobility = DynamicNodesMobility()
        logging.debug("    Nodes Mobility Built")

        logging.debug("    Building Smart Grid Layer...")
        smart_grid = SmartGrid(SmartGridConfig(self.energy_provider_configs, self.energy_consumer_configs))
        logging.debug("    Smart Grid Layer Built")

        """
        logging.debug("    Building Transducers...")
        scenario_config = dict()
        scenario_config['edcs'] = list(self.edc_configs.values())
        scenario_config['aps'] = list(self.ap_configs.values())
        scenario_config['services'] = list(self.srv_configs.values())
        scenario_config['ues'] = list(self.ue_configs.values())
        scenario_config['smart_grid_consumers'] = list(self.energy_consumer_configs.values())
        scenario_config['smart_grid_providers'] = list(self.energy_provider_configs.values())

        for key, config in self.transducer_keys.items():
            builder = AbstractFactory.create_transducer_builder(key, scenario_config=scenario_config, **config)
            self.edc_transducers.append(builder.create_edc_transducer())
            self.radio_transducers.append(builder.create_radio_transducer())
            self.ue_delay_transducers.append(builder.create_ue_delay_transducer())
            if smart_grid is not None:
                self.smart_grid_transducers.append(builder.create_smart_grid_transducer())
        logging.debug("    Transducers built")
        """

        logging.debug("Mercury: Layers built successfully")

        logging.debug("Mercury: Building model...")
        if lite:
            self.model = MercuryLite(self.name, services_id, federation, core, iot_devices,
                                     smart_grid, mobility, self.transducers_config)
        elif shortcut:
            self.model = MercuryFogModelShortcut(self.name, services_id, federation, core, access, radio,
                                                 iot_devices, smart_grid, mobility, self.transducers_config)
        else:
            self.model = MercuryFogModel(self.name, services_id, federation, core, crosshaul, access, radio,
                                         iot_devices, smart_grid, mobility, self.transducers_config)
        logging.debug("Mercury: model built successfully")

    def start_simulation(self, time_interv: float = 10000, log_time: bool = False):
        """ Initialize Mercury xDEVS coordinator """
        start_date = datetime.datetime.now()
        if self.model is None:
            raise AssertionError('Mercury model has not been built yet.')
        logging.debug("Mercury: Starting Coordinator initialization...")
        self.coordinator = Coordinator(self.model)
        for transducer in self.model.transducers:
            self.coordinator.add_transducer(transducer)
        self.coordinator.initialize()
        logging.debug("Mercury: Coordinator initialization finished successfully")
        finish_date = datetime.datetime.now()
        engine_time = finish_date - start_date
        if log_time:
            print("*********************")
            print('It took {} seconds to create the engine'.format(engine_time))
            print("*********************")

        start_date = datetime.datetime.now()
        self.coordinator.simulate_time(time_interv=time_interv)
        finish_date = datetime.datetime.now()
        sim_time = finish_date - start_date
        if log_time:
            print("*********************")
            print('It took {} seconds to simulate'.format(sim_time))
            print("*********************")
        for transducer in self.model.transducers:
            transducer.exit()
        return engine_time, sim_time

    @staticmethod
    def plot_delay(path: str, sep: str = ',', ue_id: Optional[str] = None,
                   service_id: Optional[str] = None, action: Optional[str] = None, alpha: float = 1):
        df = pd.read_csv(path, sep=sep)
        if ue_id is not None:
            df = df[df['ue_id'] == ue_id]
        if service_id is not None:
            df = df[df['service_id'] == service_id]
        if action is not None:
            df = df[df['action'] == action]
        plot_ue_service_delay(df['time'], df['delay'], ue_id, service_id, action, alpha)

    @staticmethod
    def plot_edc_utilization(path: str, sep: str = ',', stacked=False, alpha=1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_utilization(df['time'], df['edc_id'], df['utilization'], stacked=stacked, alpha=alpha)

    @staticmethod
    def plot_edc_power_demand(path: str, sep: str = ',', stacked=False, alpha=1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['edc_id'], df['power_demand'], stacked=stacked, alpha=alpha)

    @staticmethod
    def plot_edc_it_power(path: str, sep: str = ',', stacked=False, alpha=1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['edc_id'], df['it_power'],
                       stacked=stacked, alpha=alpha, nature='Demand (only IT)')

    @staticmethod
    def plot_edc_cooling_power(path: str, sep: str = ',', stacked=False, alpha=1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['edc_id'], df['cooling_power'],
                       stacked=stacked, alpha=alpha, nature='Demand (only Cooling)')

    @staticmethod
    def plot_edc_power_consumption(path: str, sep: str = ',', stacked=False, alpha=1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['consumer_id'], df['power_consumption'],
                       stacked=stacked, alpha=alpha, nature='Consumption')

    @staticmethod
    def plot_edc_power_storage(path: str, sep: str = ',', stacked=False, alpha=1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['consumer_id'], df['power_storage'],
                       stacked=stacked, alpha=alpha, nature='Storage')

    @staticmethod
    def plot_edc_power_generation(path: str, sep: str = ',', stacked=False, alpha=1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_power(df['time'], df['consumer_id'], df['power_generation'],
                       stacked=stacked, alpha=alpha, nature='Generation')

    @staticmethod
    def plot_edc_energy_stored(path: str, sep: str = ',', alpha=1):
        df = pd.read_csv(path, sep=sep)
        plot_edc_energy(df['time'], df['consumer_id'], df['energy_stored'], alpha=alpha)

    @staticmethod
    def plot_ul_bw(path: str, sep: str = ',', alpha=1):
        df = pd.read_csv(path, sep=sep)
        plot_bw(df['sim_time'], df['ue_id'], df['ap_id'], df['bandwidth'], df['rate'], df['efficiency'], alpha=alpha)

    @staticmethod
    def plot_dl_bw(path: str, sep: str = ',', alpha=1):
        df = pd.read_csv(path, sep=sep)
        plot_bw(df['time'], df['ue_id'], df['ap_id'], df['bandwidth'], df['rate'], df['efficiency'],
                link='Downlink', alpha=alpha)
