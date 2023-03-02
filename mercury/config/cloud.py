from __future__ import annotations
from typing import Any
from .client import ServicesConfig
from .network import StaticNodeConfig, TransceiverConfig


class CloudServiceConfig:
    def __init__(self, service_id: str, profiling_window: float = None,
                 proc_t_id: str = 'constant', proc_t_config: dict[str, Any] = None):
        """
        Processing unit-specific process configuration.
        :param service_id: Service ID.
        :param profiling_window: size of the profiling window for assessing the service demand.
        :param proc_t_id: processing time model ID to use by the PU when executing tasks of this service.
        :param proc_t_config: processing time model configuration parameters.
        """
        from mercury.plugin import AbstractFactory, CloudProcTimeModel
        if not ServicesConfig.srv_defined(service_id):
            raise ValueError(f'Service {service_id} not defined')
        srv_config = ServicesConfig.SERVICES[service_id]
        if profiling_window is not None and profiling_window < 0:
            raise ValueError(f'profiling_window ({profiling_window}) must be greater than 0')
        self.profiling_window: float | None = profiling_window
        self.sess_required: bool = srv_config.sess_required
        self.t_deadline: float = srv_config.sess_config.t_deadline if self.sess_required else srv_config.t_deadline
        self.stream: bool = self.sess_required and ServicesConfig.SERVICES[service_id].sess_config.stream
        proc_t_config = dict() if proc_t_config is None else proc_t_config
        self.proc_t_model: CloudProcTimeModel = AbstractFactory.create_cloud_proc_t(proc_t_id, **proc_t_config)


class CloudConfig:
    def __init__(self, cloud_id: str = 'cloud', location: tuple[float, ...] = (0, 0), trx: TransceiverConfig = None,
                 delay_id: str = 'constant', delay_config: dict[str, Any] = None, srv_configs: dict[str, Any] = None):
        self.cloud_id: str = cloud_id
        self.location: tuple[float, ...] = location
        self.xh_node: StaticNodeConfig = StaticNodeConfig(self.cloud_id, location, trx)
        self.delay_id: str = delay_id
        self.delay_config: dict[str, Any] = dict() if delay_config is None else delay_config
        self.srv_config: dict[str, CloudServiceConfig] = dict()
        if srv_configs is not None:
            for service_id, service_config in srv_configs.items():
                self.add_srv_config(service_id, **service_config)

    def add_srv_config(self, service_id: str, profiling_window: float = None,
                       proc_t_id: str = 'constant', proc_t_config: dict[str, Any] = None):
        self.srv_config[service_id] = CloudServiceConfig(service_id, profiling_window, proc_t_id, proc_t_config)
