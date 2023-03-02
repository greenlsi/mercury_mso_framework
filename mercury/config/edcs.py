from __future__ import annotations
from typing import Any
from .client import ServicesConfig
from .cloud import CloudConfig
from .network import StaticNodeConfig, TransceiverConfig
from .packet import PacketConfig
from .smart_grid import ConsumerConfig


class ServiceTasksConfig:
    def __init__(self, service_id: str, max_parallel_tasks: int, proc_t_id: str = 'constant',
                 proc_t_config: dict[str, Any] = None, power_id: str = 'constant', power_config: dict[str, Any] = None):
        """
        Processing unit-specific process configuration.
        :param service_id: Service ID.
        :param max_parallel_tasks: maximum number of tasks that the processing unit can execute in parallel.
                                   It must be greater than 0 (i.e., at least one concurrent task execution).
        :param proc_t_id: processing time model ID to use by the PU when executing tasks of this service.
        :param proc_t_config: processing time model configuration parameters.
        :param power_id: power consumption model ID to use by the PU when executing tasks of this service.
        :param power_config: power consumption model configuration parameters.
        """
        from mercury.plugin import AbstractFactory, ProcessingUnitProcTimeModel
        if not ServicesConfig.srv_defined(service_id):
            raise ValueError(f'Service {service_id} not defined')
        if max_parallel_tasks < 1:
            raise ValueError('PU must be able to process at least 1 service task concurrently')
        self.max_parallel_tasks: int = max_parallel_tasks
        srv_config = ServicesConfig.SERVICES[service_id]
        self.sess_required: bool = srv_config.sess_required
        self.t_deadline: float = srv_config.sess_config.t_deadline if self.sess_required else srv_config.t_deadline
        self.stream: bool = self.sess_required and ServicesConfig.SERVICES[service_id].sess_config.stream
        proc_t_config = {'max_parallel_tasks': max_parallel_tasks} if proc_t_config is None \
            else {**proc_t_config, 'max_parallel_tasks': max_parallel_tasks}
        self.proc_t_model: ProcessingUnitProcTimeModel = AbstractFactory.create_edc_pu_proc_t(proc_t_id, **proc_t_config)
        self.power_id: str = power_id
        self.power_config: dict[str, Any] = dict() if power_config is None else power_config


class ProcessingUnitConfig:
    def __init__(self, pu_id: str, t_on: float = 0, t_off: float = 0,
                 scheduling_id: str = 'fcfs', scheduling_config: dict[str, Any] = None,
                 default_power_id: str = 'constant', default_power_config: dict[str, Any] = None,
                 temperature_id: str = 'constant', temperature_config: dict[str, Any] = None):
        """
        Processing Unit Configuration
        :param pu_id: Processing unit model type.
        :param t_on: time required by the processing unit for switching on.
        :param t_off: time required by the processing unit to switching off.
        :param scheduling_id: scheduler model ID. By default, it is set to 'first come-first served'.
        :param scheduling_config: Configuration parameters of the sheduling model.
        :param default_power_id: default power consumption model ID. By default, it is set to constant.
        :param default_power_config: configuration parameters for the default power consumption model.
        :param temperature_id: temperature model ID. By default, it is set to constant.
        :param temperature_config: Configuration parameters of the temperature model.
        """
        self.pu_id: str = pu_id
        self.srv_configs: dict[str, ServiceTasksConfig] = dict()
        self.t_on: float = t_on
        self.t_off: float = t_off
        self.scheduling_id: str = scheduling_id
        self.scheduling_config: dict[str, Any] = dict() if scheduling_config is None else scheduling_config
        self.default_power_id: str = default_power_id
        self.default_power_config: dict[str, Any] = dict() if default_power_config is None else default_power_config
        self.temperature_id: str = temperature_id
        self.temperature_config: dict[str, Any] = dict() if temperature_config is None else temperature_config

    def add_service(self, service_id: str, max_parallel_tasks: int,
                    proc_t_id: str = 'constant', proc_t_config: dict[str, Any] = None,
                    power_id: str = 'constant', power_config: dict[str, Any] = None):
        self.srv_configs[service_id] = ServiceTasksConfig(service_id, max_parallel_tasks, proc_t_id,
                                                          proc_t_config, power_id, power_config)


class CoolerConfig:
    def __init__(self, cooler_id: str, power_id: str = 'constant', power_config: dict[str, Any] = None):
        """
        Configuration for EDC cooler.
        :param cooler_id: type of the cooler.
        :param power_id:  name of the power model. By default, it is set to constant.
        :param power_config: configuration parameters for the power model.
        """
        self.cooler_id: str = cooler_id  # TODO quitar esto
        self.power_id: str = power_id
        self.power_config: dict[str, Any] = dict() if power_config is None else power_config


class RManagerConfig:
    def __init__(self, mapping_id: str = 'ff', mapping_config: dict[str, Any] = None,
                 standby: bool = False, edc_slicing: dict[str, int] = None, cool_down: float = 0):
        """
        Edge Data Center resource manager configuration.
        :param mapping_id: request mapping function ID. By default, it uses the "First Fit" algorithm.
        :param mapping_config: Configuration parameters for the mapping function.
        :param standby: Hot standby strategy function ID.
        :param edc_slicing: EDC resource slicing per service. By default, no slicing is enforced.
        :param cool_down: Hot standby cool-down period (i.e., minimum amount of time between hot standby explorations).
                          By default, it is set to 0 (i.e., no cool-down period).
        """
        self.mapping_id: str = mapping_id
        self.mapping_config: dict[str, Any] = dict() if mapping_config is None else mapping_config
        self.standby: bool = standby
        edc_slicing = dict() if edc_slicing is None else edc_slicing
        self.edc_slicing: dict[str, int] = edc_slicing
        self.cool_down: float = cool_down


class SrvEstimatorConfig:
    def __init__(self, service_id: str, estimator_id: str, estimator_config: dict[str, Any] = None):
        self.service_id: str = service_id
        self.estimator_id: str = estimator_id
        self.estimator_config: dict[str, Any] = dict() if estimator_config is None else estimator_config


class EDCDynOperationConfig:
    def __init__(self, mapping_id: str = None, mapping_config: dict[str, Any] = None,
                 slicing_id: str = None, slicing_config: dict[str, Any] = None,
                 srv_estimators_config: dict[str, dict[str, Any]] = None, cool_down: float = 0):
        """
        Edge Data Centers controller configuration parameters.
        :param mapping_id: ID of the dynamic mapping function assignation algorithm.
                           By default, dynamic mapping functions are disabled.
        :param mapping_config: any additional configuration parameter regarding dynamic mapping.
        :param slicing_id: ID of the dynamic EDC slicing function. By default, dynamic slicing is disabled.
        :param slicing_config: any additional configuration parameter regarding dynamic EDC slicing.
        :param srv_estimators_config: Configuration parameters for service estimators.
        :param cool_down: cool-down period (i.e., minimum amount of time between two EDC controller explorations).
                          By default, it is set to 0 (i.e., no cool-down period).
        """
        if cool_down < 0:
            raise ValueError(f'cool_down must be greater than or equal to0')
        self.mapping_id: str | None = mapping_id
        self.mapping_config = dict() if mapping_config is None else mapping_config
        self.slicing_id: str | None = slicing_id
        self.slicing_config = dict() if slicing_config is None else slicing_config
        self.cool_down: float = cool_down
        self.srv_estimators_config: dict[str, SrvEstimatorConfig] = dict()
        if srv_estimators_config is not None:
            for srv_id, estimator_data in srv_estimators_config.items():
                self.srv_estimators_config[srv_id] = SrvEstimatorConfig(srv_id, **estimator_data)

    @property
    def required(self) -> bool:
        return self.mapping_id is not None or self.slicing_id is not None


class EdgeDataCenterConfig:
    def __init__(self, edc_id: str, location: tuple[float, ...], r_mngr_config: RManagerConfig = None,
                 cooler_config: CoolerConfig | None = None, edc_temp: float = 298, edc_trx: TransceiverConfig = None):
        """
        Edge data center configuration.
        :param edc_id: ID of the Edge Data Center.
        :param location: Location of the EDC (coordinates in meters).
        :param r_mngr_config: Resource manager configuration.
        :param cooler_config: configuration of cooling infrastructure of EDC.
        :param edc_temp: temperature (in Kelvin) of the EDC.
        :param edc_trx: EDC transceiver configuration.
        """
        self.edc_id: str = edc_id
        self.location: tuple[float, ...] = location
        self.r_mngr_config: RManagerConfig = RManagerConfig() if r_mngr_config is None else r_mngr_config
        self.pu_configs: dict[str, ProcessingUnitConfig] = dict()
        self.edc_temp: float = edc_temp
        self.cooler_config: CoolerConfig = CoolerConfig("default") if cooler_config is None else cooler_config
        self.dyn_config: EDCDynOperationConfig | None = None
        self.sg_config: ConsumerConfig | None = None
        self.xh_node: StaticNodeConfig = StaticNodeConfig(self.edc_id, location, edc_trx)

    def add_pu(self, pu_id: str, pu_config: ProcessingUnitConfig):
        """
        Adds a new processing unit to the edge data center.
        :param pu_id: ID of the processing unit. Every PU in an EDC has a unique ID.
        :param pu_config: Processing unit configuration
        """
        if pu_id in self.pu_configs:
            raise ValueError(f'pu_id {pu_id} already defined in EDC {self.edc_id}')
        self.pu_configs[pu_id] = pu_config

    def add_dyn_config(self, dyn_manager_config: EDCDynOperationConfig):
        """
        Adds a dynamic configuration to the edge data center.
        :param dyn_manager_config: edge data center dynamic operation configuration.
        """
        if self.dyn_config is not None:
            raise ValueError(f'Dynamic operation for edge data center {self.edc_id} already defined')
        self.dyn_config = dyn_manager_config

    def add_sg_config(self, consumer_config: ConsumerConfig):
        """
        Adds smart grid consumer configuration to the edge data center.
        :param consumer_config: smart grid consumer configuration.
        """
        if consumer_config.consumer_id != self.edc_id:
            raise ValueError(f'Smart grid consumer ID {consumer_config.consumer_id} does not match EDC {self.edc_id}')
        self.sg_config = consumer_config


class EdgeFederationConfig:
    def __init__(self, edge_fed_id: str = 'edge_fed', mapping_id: str = 'closest',
                 mapping_config: dict[str, Any] = None, congestion: float = 1,
                 srv_window_size: dict[str, float] = None, header: int = 0, content: int = 0):
        """
        Edge Federation configuration.
        :param edge_fed_id: ID of the edge computing federation.
        :param congestion: percentage of resources at which an EDC is considered congested. By default, it is 1.
        :param header: size (in bits) of the header of app messages related to edge federation management.
        :param content: size (in bits) of the content of app messages related to edge federation management.
        """
        if 0 > congestion > 1:
            raise ValueError(f'congestion ({congestion}) must be between 0 and 1')
        if header < 0:
            raise ValueError(f'header ({header}) must be greater than or equal to 0')
        if content < 0:
            raise ValueError(f'fed_mgmt_content ({content}) must be greater than or equal to 0')
        self.edge_fed_id: str = edge_fed_id
        self.mapping_id: str = mapping_id
        self.mapping_config: dict[str, Any] = dict() if mapping_config is None else mapping_config
        self.cloud_id: str | None = None
        self.pus_config: dict[str, ProcessingUnitConfig] = dict()
        self.coolers_config: dict[str, CoolerConfig] = dict()
        self.r_managers_config: dict[str, RManagerConfig] = dict()
        self.edcs_config: dict[str, EdgeDataCenterConfig] = dict()
        self.congestion: float = congestion
        self.srv_profiling_windows: dict[str, float] = dict()
        if srv_window_size is not None:
            for srv_id, window_size in srv_window_size.items():
                self.add_srv_profiling_window(srv_id, window_size)

        PacketConfig.EDGE_FED_MGMT_HEADER = header
        PacketConfig.EDGE_FED_MGMT_CONTENT = content

    @property
    def valid_config(self) -> bool:
        return bool(self.edcs_config) or self.cloud_id is not None

    def add_cloud(self, cloud_id: str):
        self.cloud_id = cloud_id

    def add_srv_profiling_window(self, service_id: str, window_size: float):
        if not ServicesConfig.srv_defined(service_id):
            raise ValueError(f'service {service_id} not defined')
        if window_size < 0:
            raise ValueError(f'window_size ({window_size}) must be greater than 0')
        self.srv_profiling_windows[service_id] = window_size

    def add_pu_config(self, pu_id: str, t_on: float = 0, t_off: float = 0, scheduling_id: str = 'fcfs',
                      scheduling_config: dict[str, Any] = None, default_power_id: str = 'constant',
                      default_power_config: dict[str, Any] = None, temp_id: str = 'constant',
                      temp_config: dict[str, Any] = None, services: dict[str, dict[str, Any]] = None):
        if pu_id in self.pus_config:
            raise ValueError(f'Processing Unit {pu_id} already defined')
        self.pus_config[pu_id] = ProcessingUnitConfig(pu_id, t_on, t_off, scheduling_id, scheduling_config,
                                                      default_power_id, default_power_config, temp_id, temp_config)
        if services is not None:
            for srv_id, srv_config in services.items():
                self.add_pu_service(pu_id, srv_id, **srv_config)

    def add_pu_service(self, pu_id: str, service_id: str, max_parallel_tasks: int, proc_t_id: str = 'constant',
                       proc_t_config: dict[str, Any] = None, pwr_id: str = 'constant', pwr_config: dict[str, Any] = None):
        if pu_id not in self.pus_config:
            raise ValueError(f'Processing Unit {pu_id} not defined')
        self.pus_config[pu_id].add_service(service_id, max_parallel_tasks, proc_t_id, proc_t_config, pwr_id, pwr_config)

    def add_cooler_config(self, cooler_id: str, power_id: str = 'constant', power_config: dict[str, Any] = None):
        if cooler_id in self.coolers_config:
            raise ValueError(f'Cooler {cooler_id} already defined')
        self.coolers_config[cooler_id] = CoolerConfig(cooler_id, power_id, power_config)

    def add_r_manager_config(self, r_manager_id: str, mapping_id: str = 'ff', mapping_config: dict[str, Any] = None,
                             standby: bool = False, edc_slicing: dict[str, int] = None, cool_down: float = 0):
        if r_manager_id in self.r_managers_config:
            raise ValueError(f'Resource manager {r_manager_id} already defined')
        self.r_managers_config[r_manager_id] = RManagerConfig(mapping_id, mapping_config, standby, edc_slicing, cool_down)

    def add_edc_config(self, edc_id: str, location: tuple[float, ...], r_manager_id: str = None,
                       cooler_id: str = None, edc_temp: float = 298, edc_trx: TransceiverConfig = None,
                       pus: dict[str, str] | None = None, dyn_config: dict[str, Any] = None):
        if edc_id in self.edcs_config:
            raise ValueError(f'EDC {edc_id} already defined')
        r_manager_config = None if r_manager_id is None else self.r_managers_config[r_manager_id]
        cooler_config = None if cooler_id is None else self.coolers_config[cooler_id]
        self.edcs_config[edc_id] = EdgeDataCenterConfig(edc_id, location, r_manager_config,
                                                        cooler_config, edc_temp, edc_trx)
        if pus is not None:
            for pu_id, pu_type_id in pus.items():
                self.add_edc_pu(edc_id, pu_id, pu_type_id)
        if dyn_config is not None:
            self.add_edc_dyn_config(edc_id, **dyn_config)

    def add_edc_pu(self, edc_id: str, pu_id: str, pu_type_id: str):
        if edc_id not in self.edcs_config:
            raise ValueError(f'Edge data center {edc_id} not defined')
        if pu_type_id not in self.pus_config:
            raise ValueError(f'Processing unit {pu_type_id} not defined')
        self.edcs_config[edc_id].add_pu(pu_id, self.pus_config[pu_type_id])

    def add_edc_dyn_config(self, edc_id: str,  mapping_id: str = None, mapping_config: dict[str, Any] = None,
                           slicing_id: str = None, slicing_config: dict[str, Any] = None,
                           srv_estimators_config: dict[str, dict[str, Any]] = None, cool_down: float = 0):
        if edc_id not in self.edcs_config:
            raise ValueError(f'Edge data center {edc_id} not defined')
        self.edcs_config[edc_id].add_dyn_config(EDCDynOperationConfig(mapping_id, mapping_config, slicing_id,
                                                                      slicing_config, srv_estimators_config, cool_down))

    def add_edc_sg_config(self, edc_id: str, consumer_config: ConsumerConfig):
        if edc_id not in self.edcs_config:
            raise ValueError(f'Edge data center {edc_id} not defined')
        self.edcs_config[edc_id].add_sg_config(consumer_config)

    def add_cloud_config(self, cloud_config: CloudConfig):
        self.cloud_config = cloud_config

