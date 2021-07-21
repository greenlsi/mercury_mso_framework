from math import inf
from typing import Dict, Optional, Any
from .network import PacketConfig, NodeConfig, TransceiverConfig


class ServiceConfig:  # TODO adapt to session-related stuff
    def __init__(self, service_id: str, header: int, content: int,
                 req_profile_name: str, req_profile_config: Dict[str, Any], req_timeout: float, max_batches: int,
                 session_profile_name: str, session_profile_config: Dict[str, Any], session_timeout: float,
                 session_duration_name: str, session_duration_config: Dict[str, Any],
                 demand_estimator_name: Optional[str] = None, demand_estimator_config: Optional[Dict[str, Any]] = None):
        """
        Configuration class for services.
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
        self.service_id: str = service_id
        PacketConfig.SRV_HEADERS[service_id] = header
        PacketConfig.SRV_CONTENTS[service_id] = content
        self.req_profile_name: str = req_profile_name
        self.req_profile_config: Dict[str, Any] = req_profile_config
        self.req_timeout: float = req_timeout
        self.max_batches: int = max_batches
        self.session_profile_name: str = session_profile_name
        self.session_profile_config: Dict[str, Any] = session_profile_config
        self.session_timeout: float = session_timeout
        self.session_duration_name: str = session_duration_name
        self.session_duration_config: Dict[str, Any] = session_duration_config
        self.estimator_name: Optional[str] = demand_estimator_name
        self.estimator_config: Dict[str, Any] = dict() if demand_estimator_config is None else demand_estimator_config


class UserEquipmentConfig:
    def __init__(self, ue_id: str, services_config: Dict[str, ServiceConfig],
                 radio_trx: Optional[TransceiverConfig] = None, t_start: float = 0, t_end: float = inf,
                 mobility_name: str = 'still', mobility_config: Optional[Dict[str, Any]] = None):
        """
        User Equipment Configuration parameters.
        :param ue_id: Unique ID of the User Equipment
        :param services_config: Service configuration list
        :param radio_trx: Radio transceiver (i.e., antenna) configuration
        :param t_start: Time at which the UE appears. By default, it is t = 0
        :param t_end: Time at which the UE disappears. By default, it is infinity
        :param mobility_name: mobility module name
        :param mobility_config: mobility module configuration parameters
        """
        self.ue_id = ue_id
        self.t_start = t_start
        self.t_end = t_end
        self.services_config = services_config
        mobility_config = dict() if mobility_config is None else mobility_config
        mobility_config['t_start'] = t_start
        self.radio_node = NodeConfig(ue_id, radio_trx, mobility_name, mobility_config)
        self.ue_location = self.radio_node.initial_location


class IoTDevicesConfig:
    def __init__(self, ues_config: Dict[str, UserEquipmentConfig], max_guard_time: float = 0):
        """
        IoT Devices Layer Configuration.
        :param ues_config: dictionary of UE configurations {UE ID: UE Configuration}
        :param max_guard_time: Maximum guard time to be awaited by UEs at the beginning of the simulation
        """
        self.ues_config = ues_config
        self.max_guard_time = max_guard_time
