from __future__ import annotations
import json
from .client import ClientsConfig, ServicesConfig
from .cloud import CloudConfig
from .edcs import EdgeFederationConfig
from .gateway import GatewaysConfig
from .network import CrosshaulConfig, AccessNetworkConfig, LinkConfig, TransceiverConfig
from .packet import PacketConfig
from .smart_grid import SmartGridConfig, PowerGeneratorConfig, EnergyStorageConfig
from .transducers import TransducersConfig
from typing import Any, Type


class MercuryConfig:
    """ Edge Computing for Data Stream Analytics Model """
    def __init__(self):
        self.srv_configs: Type[ServicesConfig] = ServicesConfig
        self.edcs_config: EdgeFederationConfig | None = None
        self.clients_config: ClientsConfig | None = None
        self.cloud_config: CloudConfig | None = None
        self.gws_config: GatewaysConfig | None = None
        self.acc_net_config: AccessNetworkConfig | None = None
        self.xh_net_config: CrosshaulConfig | None = None
        self.sg_config: SmartGridConfig = SmartGridConfig()
        self.srv_priority: list[str] = list()

    @staticmethod
    def define_net_config(net_header: int = 160):
        """
        It modifies the header size of network packets. By default, it is set to the IP protocol real value (160 bits).
        :param net_header: size (in bits) of network packet headers. By default, it is set to 160 (i.e., IP header)
        """
        if net_header < 0:
            raise ValueError('net_header must be greater than or equal to 0 bits')
        PacketConfig.NETWORK_HEADER = net_header

    @staticmethod
    def define_sess_config(sess_header: int = None, sess_timeout: float = None):
        """
        It modifies the header size of
        :param sess_header:
        :param sess_timeout:
        :return:
        """
        if sess_header is not None:
            if sess_header < 0:
                raise ValueError('sess_header must be greater than or equal to 0 bits')
            PacketConfig.SESSION_HEADER = sess_header
        if sess_timeout is not None:
            if sess_timeout < 0:
                raise ValueError('sess_timeout must be greater than or equal to 0 seconds')
            PacketConfig.SESSION_TIMEOUT = sess_timeout

    @staticmethod
    def define_transducers_config(log_srv: bool = True, log_cloud: bool = True,
                                  log_edc_report: bool = True, log_edc_profile: bool = True,
                                  log_net: bool = True, log_sg: bool = True):
        TransducersConfig.LOG_SRV = log_srv
        TransducersConfig.LOG_CLOUD = log_cloud
        TransducersConfig.LOG_EDC_REPORT = log_edc_report
        TransducersConfig.LOG_EDC_PROFILE = log_edc_profile
        TransducersConfig.LOG_NET = log_net
        TransducersConfig.LOG_SG = log_sg

    def define_edge_fed_config(self, name: str = 'edge_fed', mapping_id: str = 'closest',
                               mapping_config: dict[str, Any] = None,
                               congestion: float = 1, srv_window_size: dict[str, float] = None,
                               header: int = 0, content: int = 0):
        if self.edcs_config is not None:
            raise ValueError('Edge federation configuration already defined')
        self.edcs_config = EdgeFederationConfig(name, mapping_id, mapping_config, congestion,
                                                srv_window_size, header, content)
        if self.cloud_config is not None:
            self.edcs_config.add_cloud(self.cloud_config.cloud_id)

    def add_cloud(self, cloud_id: str = 'cloud', location: tuple[float, ...] = (0, 0), trx: TransceiverConfig = None,
                  delay_id: str = 'constant', delay_config: dict[str, Any] = None, srv_configs: dict[str, Any] = None):
        if self.cloud_config is not None:
            raise ValueError('Cloud configuration already defined')
        self.cloud_config = CloudConfig(cloud_id, location, trx, delay_id, delay_config, srv_configs)
        if self.edcs_config is not None:
            self.edcs_config.add_cloud(cloud_id)

    def define_clients_config(self, srv_max_guard: float = 0, client_generators: list[dict[str, Any]] = None):
        if self.clients_config is not None:
            raise ValueError('Clients configuration already defined')
        self.clients_config = ClientsConfig(srv_max_guard)
        if client_generators is not None:
            for generator in client_generators:
                self.add_client_generator(**generator)

    def add_client_generator(self, generator_id: str, services: list[str], generator_config: dict[str, Any] = None):
        if self.clients_config is None:
            raise ValueError('Clients configuration has not been defined yet')
        services_len = len(services)
        services = set(services)
        if len(services) != services_len:
            raise ValueError('You repeated a service more than once')
        generator_config = dict() if generator_config is None else generator_config
        generator_config['services'] = services
        self.clients_config.add_client_generator(generator_id, generator_config)

    def define_gateways_config(self, pss_window: float = 1, cool_down: float = 0, app_ran_header: int = 0):
        if self.gws_config is not None:
            raise ValueError('Gateways configuration already defined')
        self.gws_config = GatewaysConfig(pss_window, cool_down, app_ran_header)

    def add_xh_network(self, header: int = 0, connect_all: bool = True,
                       default_trx: dict[str, Any] = None, default_link: dict[str, Any] = None):
        if self.xh_net_config is not None:
            raise ValueError('Crosshaul network configuration already defined')
        default_trx = None if default_trx is None else TransceiverConfig(**default_trx)
        default_link = None if default_link is None else LinkConfig(**default_link)
        self.xh_net_config = CrosshaulConfig(header, connect_all, default_trx, default_link)

    def add_acc_network(self, network_id: str = 'access',
                        phys_wired_header: int = None, phys_wireless_header: int = None,
                        wired_dl_trx: dict[str, Any] = None, wired_ul_trx: dict[str, Any] = None,
                        wired_dl_link: dict[str, Any] = None, wired_ul_link: dict[str, Any] = None,
                        wireless_dl_trx: dict[str, Any] = None, wireless_ul_trx: dict[str, Any] = None,
                        wireless_dl_link: dict[str, Any] = None, wireless_ul_link: dict[str, Any] = None,
                        wireless_div_id: str = None, wireless_div_config: dict[str, Any] = None):
        if self.acc_net_config is not None:
            raise ValueError('Access network configuration already defined')
        wired_dl_trx = None if wired_dl_trx is None else TransceiverConfig(**wired_dl_trx)
        wired_ul_trx = None if wired_ul_trx is None else TransceiverConfig(**wired_ul_trx)
        wireless_dl_trx = None if wireless_dl_trx is None else TransceiverConfig(**wireless_dl_trx)
        wireless_ul_trx = None if wireless_ul_trx is None else TransceiverConfig(**wireless_ul_trx)
        wired_dl_link = None if wired_dl_link is None else LinkConfig(**wired_dl_link)
        wired_ul_link = None if wired_ul_link is None else LinkConfig(**wired_ul_link)
        wireless_dl_link = None if wireless_dl_link is None else LinkConfig(**wireless_dl_link)
        wireless_ul_link = None if wireless_ul_link is None else LinkConfig(**wireless_ul_link)
        self.acc_net_config = AccessNetworkConfig(network_id, phys_wired_header, phys_wireless_header,
                                                  wired_dl_trx, wired_ul_trx, wired_dl_link, wired_ul_link,
                                                  wireless_dl_trx, wireless_ul_trx, wireless_dl_link,
                                                  wireless_ul_link, wireless_div_id, wireless_div_config)

    def define_service(self, service_id: str, t_deadline: float, activity_gen_id: str,
                       activity_gen_config: dict[str, Any], activity_window_id: str,
                       activity_window_config: dict[str, Any], req_gen_id: str, req_gen_config: dict[str, Any],
                       header_size: int = 0, srv_req_size: int = 0, srv_res_size: int = 0, cool_down: float = 0,
                       sess_config: dict[str, Any] | None = None):
        self.srv_configs.add_service(service_id, t_deadline, activity_gen_id, activity_gen_config, activity_window_id,
                                     activity_window_config, req_gen_id, req_gen_config, header_size,
                                     srv_req_size, srv_res_size, cool_down, sess_config)

    def define_srv_priority(self, srv_priority: list[str]):
        self.srv_priority = list()
        services = list(ServicesConfig.SERVICES)
        for srv_id in srv_priority:
            services.remove(srv_id)
            self.srv_priority.append(srv_id)
        self.srv_priority.extend(services)

    def add_sg_provider(self, provider_id: str, provider_type: str, provider_config: dict[str, Any] = None):
        """
        Adds a smart grid energy provider
        :param provider_id: ID of the energy provider
        :param provider_type: Type of energy provider
        :param provider_config: Any additional configuration parameter for the energy provider model
        """
        self.sg_config.add_provider(provider_id, provider_type, provider_config)

    def define_edc_pu_config(self, pu_id: str, t_on: float = 0, t_off: float = 0, scheduling_id: str = 'fcfs',
                             scheduling_config: dict[str, Any] = None, pwr_id: str = 'constant',
                             pwr_config: dict[str, Any] = None, temp_id: str = 'constant',
                             temp_config: dict[str, Any] = None, services: dict[str, dict[str, Any]] | None = None):
        if self.edcs_config is None:
            self.define_edge_fed_config()
        self.edcs_config.add_pu_config(pu_id, t_on, t_off, scheduling_id, scheduling_config,
                                       pwr_id, pwr_config, temp_id, temp_config, services)

    def define_edc_cooler_config(self, cooler_id: str, power_id: str = 'constant',
                                 power_config: dict[str, Any] | None = None):
        if self.edcs_config is None:
            self.define_edge_fed_config()
        self.edcs_config.add_cooler_config(cooler_id, power_id, power_config)

    def define_edc_r_manager_config(self, r_manager_id: str, mapping_id: str = 'ff',
                                    mapping_config: dict[str, Any] = None, standby: bool = False,
                                    edc_slicing: dict[str, int] = None, cool_down: float = 0):
        if self.edcs_config is None:
            self.define_edge_fed_config()
        self.edcs_config.add_r_manager_config(r_manager_id, mapping_id, mapping_config, standby, edc_slicing, cool_down)

    def add_edc(self, edc_id: str, location: tuple[float, ...], r_manager_id: str | None = None,
                cooler_id: str | None = None, edc_temp: float = 298, xh_trx: dict[str, Any] = None,
                pus: dict[str, str] = None, dyn_config: dict[str, Any] = None, sg_config: dict[str, Any] = None):
        if self.edcs_config is None:
            self.define_edge_fed_config()
        xh_trx = None if xh_trx is None else TransceiverConfig(**xh_trx)
        self.edcs_config.add_edc_config(edc_id, location, r_manager_id, cooler_id, edc_temp, xh_trx, pus, dyn_config)
        if sg_config is not None:
            self.add_sg_consumer(edc_id, **sg_config)

    def add_sg_consumer(self, consumer_id: str, provider_id: str, storage_config: dict[str, Any] = None,
                        manager_id: str = 'static', manager_config: dict[str, Any] = None,
                        sources: dict[str, dict[str, Any]] = None):
        if consumer_id not in self.edcs_config.edcs_config:
            raise ValueError(f'Smart Grid consumer {consumer_id} does not coincide with any EDC defined so far')
        storage_config = None if storage_config is None else EnergyStorageConfig(**storage_config)
        sources = None if sources is None else {source_id: PowerGeneratorConfig(**source_config)
                                                for source_id, source_config in sources.items()}
        self.sg_config.add_consumer(consumer_id, provider_id, storage_config, manager_id, manager_config, sources)
        self.edcs_config.edcs_config[consumer_id].add_sg_config(self.sg_config.consumers_config[consumer_id])

    def add_gateway(self, gateway_id: str, location: tuple[float, ...], wired: bool,
                    xh_trx: dict[str, Any] = None, acc_trx: dict[str, Any] = None):
        if self.gws_config is None:
            self.define_gateways_config()
        xh_trx = None if xh_trx is None else TransceiverConfig(**xh_trx)
        acc_trx = None if acc_trx is None else TransceiverConfig(**acc_trx)
        self.gws_config.add_gateway(gateway_id, location, wired, xh_trx, acc_trx)

    def add_nodes_to_xh(self):
        if self.xh_net_config is None:
            self.add_xh_network()
        self.xh_net_config.define_gateways(self.gws_config)
        self.xh_net_config.define_edcs(self.edcs_config)
        if self.cloud_config is not None:
            self.xh_net_config.define_cloud(self.cloud_config)

    def add_nodes_to_acc(self):
        if self.acc_net_config is None:
            self.add_acc_network('access')
        for gw_config in self.gws_config.gateways.values():
            self.acc_net_config.add_gateway(gw_config)

    @staticmethod
    def from_json(path: str) -> MercuryConfig:
        with open(path) as file:
            json_data = json.load(file)
        config: MercuryConfig = MercuryConfig()

        config.define_net_config(**json_data.get('net_config', dict()))
        config.define_sess_config(**json_data.get('sess_config', dict()))
        config.define_transducers_config(**json_data.get('transducers_config', dict()))
        # Define all the services in the scenario
        for service_id, service_config in json_data.get('services', dict()).items():
            config.define_service(service_id, **service_config)  # TODO additional code for setting callables? factory?
        config.define_srv_priority(json_data.get('srv_priority', list()))

        config.define_edge_fed_config(**json_data.get('edge_fed_config', dict()))
        config.define_gateways_config(**json_data.get('gateways_config', dict()))
        config.define_clients_config(**json_data.get('clients_config', dict()))

        if 'cloud_config' in json_data:
            config.add_cloud(**json_data['cloud_config'])

        for provider_id, provider_config in json_data.get('sg_providers', dict()).items():
            config.add_sg_provider(provider_id, **provider_config)

        # Define all the EDC-related properties in the scenario
        for pu_id, pu_config in json_data.get('edc_pus', dict()).items():
            config.define_edc_pu_config(pu_id, **pu_config)
        for cooler_id, cooler_config in json_data.get('edc_coolers', dict()).items():
            config.define_edc_cooler_config(cooler_id, **cooler_config)
        for r_manager_id, r_manager_config in json_data.get('edc_r_managers', dict()).items():
            config.define_edc_r_manager_config(r_manager_id, **r_manager_config)

        config.add_xh_network(**json_data.get('xh_config', dict()))
        config.add_acc_network(**json_data.get('acc_config', dict()))
        for gw_id, gw_config in json_data.get('gateways', dict()).items():
            config.add_gateway(gw_id, **gw_config)
        for edc_id, edc_config in json_data.get('edcs', dict()).items():
            config.add_edc(edc_id, **edc_config)
        # TODO no service estimation ("impossible" to load dataframes? (or non-sense); allocation manager integration)
        # TODO careful with callables and dataframes: we cannot automatically load them using JSON files
        # TODO integration with allocation manager
        return config
