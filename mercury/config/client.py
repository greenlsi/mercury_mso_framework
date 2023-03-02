from __future__ import annotations
from abc import ABC
from .packet import PacketConfig
from .network import TransceiverConfig, LinkConfig, DynamicNodeConfig, WirelessNodeConfig, WiredNodeConfig
from typing import Any, ClassVar


class SrvConfig:
    def __init__(self, service_id: str, t_deadline: float, activity_gen_id: str, activity_gen_config: dict[str, Any],
                 activity_window_id: str, activity_window_config: dict[str, Any], req_gen_id: str,
                 req_gen_config: dict[str, Any], header_size: int = 0,
                 srv_req_size: int = 0, srv_res_size: int = 0, cool_down: float = 0):
        """
        Service requests configuration parameters.
        :param service_id: ID of the service.
        :param t_deadline: deadline (in seconds) of service requests.
        :param activity_gen_id: ID of the service activity generator (i.e., how often a service is active).
        :param activity_gen_config: any additional configuration parameter for the service activity generator.
        :param activity_window_id: ID of the service activity window (i.e., how long a service remains active).
        :param activity_window_config: any additional configuration parameter for the service activity window.
        :param req_gen_id: ID of the service request generator (i.e., how often a new request is created).
        :param req_gen_config: any additional configuration parameter for the service request generator.
        :param header_size: header size (in bits) of service-related messages.
        :param srv_req_size: content size (in bits) of service request messages.
        :param srv_res_size: content size (in bits) of service response messages.
        :param cool_down: cooldown time to wait if a request fails.
        """
        if t_deadline < 0:
            raise ValueError(f'invalid t_deadline ({t_deadline})')
        if header_size < 0:
            raise ValueError(f'invalid header_size({header_size}')
        if srv_req_size < 0:
            raise ValueError(f'invalid srv_req_size ({srv_req_size})')
        if srv_res_size < 0:
            raise ValueError(f'invalid srv_res_size ({srv_res_size})')
        if cool_down < 0:
            raise ValueError(f'invalid cool_down ({cool_down}')
        self.service_id: str = service_id
        self.t_deadline: float = t_deadline
        self.activity_gen_id: str = activity_gen_id
        self.activity_gen_config: dict[str, Any] = activity_gen_config
        self.activity_window_id: str = activity_window_id
        self.activity_window_config: dict[str, Any] = activity_window_config
        self.req_gen_id: str = req_gen_id
        self.req_gen_config: dict[str, Any] = req_gen_config
        self.cool_down: float = cool_down
        self.sess_config: SrvSessionConfig | None = None
        PacketConfig.SRV_PACKET_HEADERS[self.service_id] = header_size
        PacketConfig.SRV_PACKET_SRV_REQ[self.service_id] = srv_req_size
        PacketConfig.SRV_PACKET_SRV_RES[self.service_id] = srv_res_size

    @property
    def sess_required(self) -> bool:
        return self.sess_config is not None

    def add_sess_config(self, t_deadline: float, stream: bool, open_req_size: int = 0,
                        open_res_size: int = 0, close_req_size: int = 0, close_res_size: int = 0):
        self.sess_config = SrvSessionConfig(self.service_id, t_deadline, stream, open_req_size,
                                            open_res_size, close_req_size, close_res_size)


class SrvSessionConfig:
    def __init__(self, service_id: str, t_deadline: float, stream: bool, open_req_size: int = 0,
                 open_res_size: int = 0, close_req_size: int = 0, close_res_size: int = 0):
        """
        Service sessions configuration parameters.
        :param service_id: Service ID.
        :param t_deadline: deadline (in seconds) of open service session requests.
        :param stream: If True, sessions are continuously executing until closed (even if no requests are pending).
        :param open_req_size: content size (in bits) of open session request messages.
        :param open_res_size: content size (in bits) of open session response messages.
        :param close_req_size: content size (in bits) of close session request messages.
        :param close_res_size: content size (in bits) of close session response messages.
        """
        if t_deadline < 0:
            raise ValueError(f'invalid t_deadline ({t_deadline})')
        if open_req_size < 0:
            raise ValueError(f'invalid open_req_size ({open_req_size})')
        if open_res_size < 0:
            raise ValueError(f'invalid open_res_size ({open_res_size})')
        if close_req_size < 0:
            raise ValueError(f'invalid close_req_size ({close_req_size})')
        if close_res_size < 0:
            raise ValueError(f'invalid close_res_size ({close_res_size})')
        self.service_id: str = service_id
        self.t_deadline: float = t_deadline
        self.stream: bool = stream

        PacketConfig.SRV_PACKET_OPEN_REQ[self.service_id] = open_req_size
        PacketConfig.SRV_PACKET_OPEN_RES[self.service_id] = open_res_size
        PacketConfig.SRV_PACKET_CLOSE_REQ[self.service_id] = close_req_size
        PacketConfig.SRV_PACKET_CLOSE_RES[self.service_id] = close_res_size


class ServicesConfig:
    SRV_MAX_GUARD: ClassVar[float] = 0
    SERVICES: ClassVar[dict[str, SrvConfig]] = dict()

    @staticmethod
    def srv_defined(service_id: str):
        return service_id in ServicesConfig.SERVICES

    @staticmethod
    def add_service(service_id: str, t_deadline: float, activity_gen_id: str, activity_gen_config: dict[str, Any],
                    activity_window_id: str, activity_window_config: dict[str, Any], req_gen_id: str,
                    req_gen_config: dict[str, Any], header_size: int = 0, srv_req_size: int = 0,
                    srv_res_size: int = 0, cool_down: float = 0, sess_config: dict[str, Any] = None):
        """
        Add service configuration.
        :param service_id: ID of the service.
        :param t_deadline: deadline (in seconds) of service requests.
        :param activity_gen_id: ID of the service activity generator (i.e., how often a service is active).
        :param activity_gen_config: any additional configuration parameter for the service activity generator.
        :param activity_window_id: ID of the service activity window (i.e., how long a service remains active).
        :param activity_window_config: any additional configuration parameter for the service activity window.
        :param req_gen_id: ID of the service request generator (i.e., how often a new request is created).
        :param req_gen_config: any additional configuration parameter for the service request generator.
        :param header_size: header size (in bits) of service-related messages.
        :param srv_req_size: content size (in bits) of service request messages.
        :param srv_res_size: content size (in bits) of service response messages.
        :param cool_down: cool down (in seconds) to wait if any service-relate request fails.
        :param sess_config: configuration for service sessions (see add_sess_config).
        """
        srv_config = SrvConfig(service_id, t_deadline, activity_gen_id, activity_gen_config,
                               activity_window_id, activity_window_config, req_gen_id, req_gen_config,
                               header_size, srv_req_size, srv_res_size, cool_down)
        ServicesConfig.SERVICES[service_id] = srv_config
        if sess_config is not None:
            ServicesConfig.add_sess_config(service_id, **sess_config)

    @staticmethod
    def add_sess_config(service_id: str, t_deadline: float, stream: bool, open_req_size: int = 0,
                        open_res_size: int = 0, close_req_size: int = 0, close_res_size: int = 0):
        """
        Adds sessions configuration parameters to a given service.
        :param service_id: Service ID.
        :param t_deadline: deadline (in seconds) of open service session requests.
        :param stream: If True, sessions are continuously executing until closed (even if no requests are pending).
        :param open_req_size: content size (in bits) of open session request messages.
        :param open_res_size: content size (in bits) of open session response messages.
        :param close_req_size: content size (in bits) of close session request messages.
        :param close_res_size: content size (in bits) of close session response messages.
        """
        if not ServicesConfig.srv_defined(service_id):
            raise ValueError(f'service with ID {service_id} is not defined')
        ServicesConfig.SERVICES[service_id].add_sess_config(t_deadline, stream, open_req_size,
                                                            open_res_size, close_req_size, close_res_size)

    @staticmethod
    def reset():
        ServicesConfig.SERVICES = dict()
        PacketConfig.reset_srv()


class ClientConfig(ABC):
    def __init__(self, client_id: str, services: set[str], t_start: float, t_end: float, node: DynamicNodeConfig):
        for service in services:
            if not ServicesConfig.srv_defined(service):
                raise ValueError(f'client {client_id} contains undefined service ({service})')
        self.client_id: str = client_id
        self.services: dict[str, SrvConfig] = {srv_id: ServicesConfig.SERVICES[srv_id] for srv_id in services}
        self.t_start: float = t_start
        self.t_end: float = t_end
        self.node_config: DynamicNodeConfig = node

    @property
    def location(self) -> tuple[float, ...]:
        return self.node_config.location

    @property
    def wireless(self) -> bool:
        return self.node_config.wireless


class WirelessClientConfig(ClientConfig):
    node: WirelessNodeConfig

    def __init__(self, client_id: str, services: set[str], t_start: float, t_end: float,
                 mob_id: str, mob_config: dict[str, Any], trx_config: TransceiverConfig = None):
        mob_config = {**mob_config, 't_start': t_start, 't_end': t_end}
        node = WirelessNodeConfig(client_id, t_start, t_end, mob_id, mob_config, trx_config)
        super().__init__(client_id, services, t_start, t_end, node)


class WiredClientConfig(ClientConfig):
    node: WiredNodeConfig

    def __init__(self, client_id: str, gateway_id: str, services: set[str], t_start: float, t_end: float,
                 location: tuple[float, ...], trx_config: TransceiverConfig = None,
                 dlink_config: LinkConfig = None, ulink_config: LinkConfig = None):
        node = WiredNodeConfig(client_id, gateway_id, t_start, t_end, location, trx_config, dlink_config, ulink_config)
        super().__init__(client_id, services, t_start, t_end, node)

    @property
    def gateway_id(self) -> str:
        return self.node.gateway_id


class ClientsConfig:
    def __init__(self, srv_max_guard: float = 0):
        ServicesConfig.SRV_MAX_GUARD = srv_max_guard
        self.clients: dict[str, ClientConfig] = dict()
        self.generators: list[tuple[str, dict[str, Any]]] = list()

    def add_client_generator(self, generator_id: str, generator_config: dict[str, Any]):
        """

        :param generator_id: ID of the client generator to be created.
        :param generator_config: Any additional configuration parameter for the generator.
        :return:
        """
        self.generators.append((generator_id, generator_config))
