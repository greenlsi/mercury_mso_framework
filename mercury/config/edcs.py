from typing import Optional, Dict, Tuple, Any
from .network import NodeConfig, TransceiverConfig


class ResourceManagerConfig:
    def __init__(self, mapping_name: str = 'first_fit', mapping_config: Optional[Dict[str, Any]] = None,
                 hot_standby_name: Optional[str] = None, hot_standby_config: Optional[Dict[str, Any]] = None,
                 cool_down: float = 0):
        """
        Resource Manager Configuration.
        :param mapping_name: Session dispatching cost function name. By default, it uses the First Fit algorithm
        :param mapping_config: Configuration parameters for the dispatching cost function.
        :param hot_standby_name: Hot standby strategy function name.
        :param hot_standby_config: Configuration parameters for the Hot standby strategy function.
        :param cool_down: Hot standby cool-down period (i.e., minimum amount of time between hot standby explorations).
                          By default, it is set to 0 (i.e., no cool-down period).
        """
        self.mapping_name: str = mapping_name
        self.mapping_config: Dict[str, Any] = dict() if mapping_config is None else mapping_config
        self.hot_standby_name: Optional[str] = hot_standby_name
        self.hot_standby_config: Dict[str, Any] = dict() if hot_standby_config is None else hot_standby_config
        self.cool_down: float = cool_down


class ProcessingUnitProcessConfig:
    def __init__(self, t_start: float = 0, t_stop: float = 0, t_process: float = 0,
                 u_idle: float = 0, u_busy: float = 0):
        """
        Processing Unit-specific process configuration.
        :param t_start: time (in seconds) required to start a service context. By default, it is 0.
        :param t_stop: time (in seconds) required to stop a service context. By default, it is 0.
        :param t_process: time (in seconds) required to process a service request. By default, it is 0.
        :param u_idle: resource utilization (in %) consumed by process when session is idling. By default, it is 0%.
        :param u_busy: resource utilization (in %) consumed by process when session is busy. By default, it is 0%.
        """
        if t_start < 0 or t_stop < 0 or t_process < 0 or u_idle < 0 or u_busy < 0:
            raise ValueError('PU process configuration values cannot be less than 0')
        if not u_busy > 0:
            raise ValueError('PU process utilization when busy must be greater than 0%')
        self.t_start: float = t_start
        self.t_stop: float = t_stop
        self.t_process: float = t_process
        self.u_idle: float = u_idle
        self.u_busy: float = u_busy

    @property
    def max_u(self) -> float:
        """Maximum resource utilization (in %) consumed by process"""
        return max(self.u_idle, self.u_busy)

    @property
    def min_u(self) -> float:
        """Minimum resource utilization (in %) consumed by process"""
        return min(self.u_idle, self.u_busy)

    @property
    def t_total(self) -> float:
        """Total time required for a session-less request"""
        return self.t_start + self.t_process + self.t_stop


class ProcessingUnitConfig:
    def __init__(self, pu_type: str, services: Dict[str, Dict[str, float]],
                 dvfs_table: Optional[Dict[float, Any]] = None, t_on: float = 0, t_off: float = 0,
                 scheduling_name: str = 'fcfs', scheduling_config: Optional[Dict[str, Any]] = None,
                 power_name: Optional[str] = None, power_config: Optional[Dict[str, Any]] = None,
                 temp_name: Optional[str] = None, temp_config: Optional[Dict[str, Any]] = None):
        """
        Processing Unit Configuration
        :param pu_type: Processing unit model type.
        :param services: dictionary {service_id: {SERVICE_CONFIG}}.  TODO hacer service config con un objeto
        :param dvfs_table: dictionary containing DVFS table {max_u_1: {dvfs_conf_1}, ..., 100: {dvfs_conf_N}}.
        :param t_on: time required by the processing unit for switching on.
        :param t_off: time required by the processing unit to switching off.
        :param scheduling_name: Scheduling function name. By default, it is a first come first served scheduler.
        :param scheduling_config: Configuration parameters of PU's scheduling function.
        :param power_name: Power consumption model name. By default, no power consumption model is implemented.
        :param power_config: Configuration parameters of power consumption model.
        :param temp_name: Temperature model name. By default, no temperature model is implemented.
        :param temp_config: Configuration parameters of temperature model.
        """
        self.pu_type: str = pu_type
        self.services: Dict[str, ProcessingUnitProcessConfig] = {service: ProcessingUnitProcessConfig(**process)
                                                                 for service, process in services.items()}
        self.dvfs_table: Dict[float, Any] = {100: dict()} if dvfs_table is None else dvfs_table
        self.t_on: float = t_on
        self.t_off: float = t_off
        self.scheduling_name: str = scheduling_name
        self.scheduling_config: Dict[str, Any] = scheduling_config if scheduling_config is not None else dict()
        self.power_name: Optional[str] = power_name
        self.power_config: Dict[str, Any] = power_config if power_config is not None else dict()
        self.temp_name: Optional[str] = temp_name
        self.temp_config: Dict[str, Any] = temp_config if temp_config is not None else dict()


class CoolerConfig:
    def __init__(self, cooler_type: str,
                 power_name: Optional[str] = None, power_config: Optional[Dict[str, Any]] = None,
                 temp_name: Optional[str] = None, temp_config: Optional[Dict[str, Any]] = None):
        """
        Configuration for EDC cooler.
        :param cooler_type: type of the cooler.
        :param power_name:  name of the power model.
        :param power_config: configuration parameters for the power model.
        :param temp_name: name of the temperature model.
        :param temp_config: configuration parameters for the temperature model.
        """
        self.cooler_type: str = cooler_type
        self.power_name: Optional[str] = power_name
        self.power_config: Dict[str, Any] = dict() if power_config is None else power_config
        self.temp_name: Optional[str] = temp_name
        self.temp_config: Dict[str, Any] = dict() if temp_config is None else temp_config


class EdgeDataCenterConfig:
    def __init__(self, edc_id: str, edc_location: Tuple[float, ...], r_manager_config: ResourceManagerConfig,
                 pus_config: Dict[str, ProcessingUnitConfig], cooler_config: Optional[CoolerConfig] = None,
                 edc_trx: Optional[TransceiverConfig] = None, env_temp: float = 298):
        """
        Edge Data Center Configuration.
        :param edc_id: ID of the Edge Data Center.
        :param edc_location: Location of the EDC (coordinates in meters).
        :param r_manager_config: Default resource manager configuration.
        :param pus_config: configuration of PUs that compose the EDC.
        :param cooler_config: configuration of cooling infrastructure of EDC.
        :param edc_trx: Crosshaul transceiver configuration.
        :param env_temp: Environment temperature of the EDC.
        """
        self.edc_id: str = edc_id
        self.edc_location: Tuple[float, ...] = edc_location
        self.r_manager_config: ResourceManagerConfig = r_manager_config
        self.pus_config: Dict[str, ProcessingUnitConfig] = pus_config
        self.cooler_config: Optional[CoolerConfig] = cooler_config
        self.crosshaul_node = NodeConfig(self.edc_id, edc_trx, node_mobility_config={'initial_val': edc_location})
        self.env_temp = env_temp


class EdgeFederationControllerConfig:
    def __init__(self, demand_share_name: str = 'equal', demand_share_config: Optional[Dict[str, Any]] = None,
                 dyn_dispatching_name: Optional[str] = None, dyn_dispatching_config: Optional[Dict[str, Any]] = None,
                 dyn_hot_standby_name: Optional[str] = None, dyn_hot_standby_config: Optional[Dict[str, Any]] = None,
                 dyn_slicing_name: Optional[str] = None, dyn_slicing_config: Optional[Dict[str, Any]] = None,
                 cool_down: float = 0):
        """
        Edge Data Centers controller configuration parameters.
        :param demand_share_name: name of the demand share algorithm (i.e., how demand is distributed among EDCs).
                                  By default, the EDC controller estimates that all the EDCs will face the same demand.
        :param demand_share_config: any additional configuration parameter regarding EDC demand share estimation.
        :param dyn_dispatching_name: name of the dynamic dispatching function assignation algorithm.
                                     By default, dynamic dispatching functions are disabled.
        :param dyn_dispatching_config: any additional configuration parameter regarding dynamic dispatching.
        :param dyn_hot_standby_name: name of the dynamic hot standby algorithm.
                                     By default, dynamic hot standby is disabled.
        :param dyn_hot_standby_config: any additional configuration parameter regarding dynamic hot standby functions.
        :param dyn_slicing_name: name of the dynamic EDC slicing function. By default, dynamic slicing is disabled.
        :param dyn_slicing_config: any additional configuration parameter regarding dynamic EDC slicing.
        :param cool_down: cool-down period (i.e., minimum amount of time between two EDC controller explorations).
                          By default, it is set to 0 (i.e., no cool-down period).
        """
        self.demand_share_name = demand_share_name
        self.demand_share_config = dict() if demand_share_config is None else demand_share_config
        self.dyn_dispatching_name = dyn_dispatching_name
        self.dyn_dispatching_config = dict() if dyn_dispatching_config is None else dyn_dispatching_config
        self.dyn_hot_standby_name = dyn_hot_standby_name
        self.dyn_hot_standby_config = dict() if dyn_hot_standby_config is None else dyn_hot_standby_config
        self.dyn_slicing_name = dyn_slicing_name
        self.dyn_slicing_config = dict() if dyn_slicing_config is None else dyn_slicing_config
        self.cool_down = cool_down


class EdgeFederationConfig:
    def __init__(self, edcs: Dict[str, EdgeDataCenterConfig], congestion: float = 100,
                 edc_slicing: Optional[Dict[str, Dict[str, float]]] = None,
                 efc: Optional[EdgeFederationControllerConfig] = None):
        """
        Edge Federation configuration.
        :param edcs: dictionary containing the configuration of each EDC that comprises the federation.
        :param congestion: percentage of resources at which an EDC is considered congested. By default, it is 100%.
        :param edc_slicing: EDC resources slicing per service. By default, no slicing is enforced.
        :param efc: Configuration parameters of the EDCs controller.
                                By default, the EDCs controller is disabled (i.e., no dynamic configuration of EDCs)
        """
        self.edcs: Dict[str, EdgeDataCenterConfig] = edcs
        self.congestion: float = congestion
        self.edc_slicing: Dict[str, Dict[str, float]] = dict() if edc_slicing is None else edc_slicing
        self.efc: Optional[EdgeFederationControllerConfig] = efc
