from __future__ import annotations
from abc import ABC, abstractmethod
from mercury.config.client import ServicesConfig
from mercury.config.config import MercuryConfig, GatewaysConfig
from mercury.config.transducers import TransducersConfig
from mercury.msg.packet import AppPacket, NetworkPacket, PhysicalPacket, PacketInterface
from mercury.utils.amf import AccessManagementFunction
from typing import Any, Generic, Type
from xdevs.models import Coupled
from xdevs.transducers import Transducer, Transducers
from .clients import ClientsABC, Clients, ClientsShortcut, ClientsLite, ClientGeneratorModel
from .cloud import Cloud
from .edcs import EdgeDataCenters
from .gateways import GatewaysABC, Gateways, GatewaysShortcut, GatewaysLite
from .network import AccessNetwork, AccessNetworkShortcut, CrosshaulNetwork, MobilityManager
from .smart_grid import SmartGrid
from .shortcut import PacketMultiplexer


class MercuryModelABC(Coupled, ABC, Generic[PacketInterface]):
    def __init__(self, config: MercuryConfig, lite: bool, p_type: Type[PacketInterface], name: str = 'mercury'):
        """
        Mercury edge computing model.
        :param config:
        :param lite:
        :param p_type:
        :param name: name of the model. By default, it is set to "mercury"
        """
        super().__init__(name)
        self._lite: bool = lite
        self._p_type: Type[PacketInterface] = AppPacket if lite else p_type
        self._built: bool = False
        self.config: MercuryConfig = config
        self.transducers_config: dict[str, tuple[str, dict[str, Any]]] = dict()

        self.shortcut: PacketMultiplexer[PacketInterface] | None = None
        self.edcs: EdgeDataCenters[PacketInterface] | None = None
        self.cloud: Cloud | None = None
        self.xh: CrosshaulNetwork | None = None
        self.gws: GatewaysABC | GatewaysLite | None = None
        self.access: AccessNetwork | AccessNetworkShortcut | None = None
        self.clients: ClientsABC | None = None
        self.client_generator: ClientGeneratorModel | None = None
        self.mobility: MobilityManager | None = None
        self.smart_grid: SmartGrid | None = None
        self.transducers: list[Transducer] = list()

    @property
    def built(self) -> bool:
        return self._built

    def add_transducers(self, transducer_id, transducer_type: str, transducer_config: dict[str, Any]):
        if transducer_id in self.transducers_config:
            raise ValueError("Transducer already defined")
        self.transducers_config[transducer_id] = (transducer_type, transducer_config)

    def build(self):
        if self._built:
            raise ValueError('Model already built')
        self._add_components()
        self._add_specific_couplings()
        self._add_common_couplings()
        self._add_transducers()
        self._built = True

    def _add_components(self):
        p_type = AppPacket if self._lite else self._p_type
        amf = AccessManagementFunction(self.config.gws_config.gateways)

        if not self.config.edcs_config.valid_config:
            raise ValueError('invalid configuration: no EDC nor cloud configuration provided')
        if self.config.cloud_config is not None:
            self.cloud = Cloud(p_type, self.config.cloud_config, amf)
            self.add_component(self.cloud)
        if self.config.edcs_config.edcs_config:
            self.edcs = EdgeDataCenters(p_type, self.config.edcs_config,
                                        self.config.gws_config, self.config.srv_priority, amf)
            self.add_component(self.edcs)
        self.clients = ClientsABC.new_clients(self._lite, p_type)
        self.add_component(self.clients)
        self.client_generator = ClientGeneratorModel(self.config.clients_config)
        self.add_component(self.client_generator)
        self.mobility = MobilityManager()
        self.add_component(self.mobility)
        if self.config.sg_config is not None and self.config.sg_config.consumers_config:
            self.smart_grid = SmartGrid(self.config.sg_config)
            self.add_component(self.smart_grid)

        if not self._lite and p_type == PhysicalPacket:
            self.config.add_nodes_to_xh()
            self.config.xh_net_config.build()
            self.xh = CrosshaulNetwork(self.config.xh_net_config.net_config)
            self.add_component(self.xh)
        else:
            if self._lite:
                nodes = [GatewaysConfig.GATEWAYS_LITE, *self.config.edcs_config.edcs_config]
            else:
                nodes = [*self.config.gws_config.gateways, *self.config.edcs_config.edcs_config]
            # If cloud is defined, we add it to the node list
            if self.config.cloud_config is not None:
                nodes.append(self.config.cloud_config.cloud_id)
            self.shortcut = PacketMultiplexer(p_type, nodes)
            self.add_component(self.shortcut)
        if self._lite:
            self.gws = GatewaysLite(self.config.gws_config, self.config.edcs_config, amf)
            self.add_component(self.gws)
        else:
            self.gws = GatewaysABC.new_gws(p_type, self.config.gws_config, self.config.edcs_config, amf)
            self.add_component(self.gws)
            self.config.add_nodes_to_acc()
            self.access = AccessNetwork.new_access(p_type, self.config.acc_net_config)
            self.add_component(self.access)

    @abstractmethod
    def _add_specific_couplings(self):
        pass

    def _add_common_couplings(self):
        xh = self.xh if self.xh is not None else self.shortcut
        # ICs between EDCs and xh
        if self.edcs is not None:
            self.add_coupling(self.edcs.output_data, xh.input_data)
            for edc_id, in_port in self.edcs.inputs_data.items():
                self.add_coupling(xh.outputs_data[edc_id], in_port)
        # ICs between client generator and clients
        self.add_coupling(self.client_generator.output_client_config, self.clients.input_create_client)
        # ICs between clients and mobility manager
        self.add_coupling(self.clients.output_create_client, self.mobility.input_create_node)
        self.add_coupling(self.clients.output_remove_client, self.mobility.input_remove_node)
        # ICs between smart grid layer and EDCs
        if self.smart_grid is not None:
            for edc_id in self.smart_grid.consumers:
                self.add_coupling(self.smart_grid.outputs_consumption[edc_id], self.edcs.inputs_sg_report[edc_id])
                self.add_coupling(self.edcs.outputs_sg_report[edc_id], self.smart_grid.inputs_demand[edc_id])

    def _add_transducers(self):
        for t_id, (t_type, t_config) in self.transducers_config.items():
            if TransducersConfig.LOG_SRV:
                transducer = Transducers.create_transducer(t_type, **t_config, transducer_id=f'{t_id}_srv_report',
                                                           sim_time_id='time', include_names=False)
                transducer.add_target_port(self.clients.output_srv_report)
                transducer.drop_event_field('value')
                transducer.add_event_field('client_id', str, lambda x: x.client_id)
                transducer.add_event_field('service_id', str, lambda x: x.service_id)
                transducer.add_event_field('req_type', str, lambda x: x.req_type)
                transducer.add_event_field('req_n', int, lambda x: x.req_n)
                transducer.add_event_field('t_req_gen', float, lambda x: x.t_req_gen)
                transducer.add_event_field('t_res_rcv', float, lambda x: x.t_res_rcv)
                transducer.add_event_field('t_delay', float, lambda x: x.t_delay)
                transducer.add_event_field('deadline_met', bool, lambda x: x.deadline_met)
                transducer.add_event_field('acc_met_deadlines', int, lambda x: x.acc_met_deadlines)
                transducer.add_event_field('acc_missed_deadlines', int, lambda x: x.acc_missed_deadlines)
                transducer.add_event_field('n_sess', int, lambda x: x.n_sess)
                transducer.add_event_field('t_sess', float, lambda x: x.t_sess)
                self.transducers.append(transducer)

            if self.cloud is not None and TransducersConfig.LOG_CLOUD:
                transducer = Transducers.create_transducer(t_type, **t_config, transducer_id=f'{t_id}_cloud',
                                                           sim_time_id='time', include_names=False)
                transducer.add_target_port(self.cloud.output_profile)
                transducer.drop_event_field('value')
                transducer.add_event_field('cloud_id', str, lambda x: x.cloud_id)
                transducer.add_event_field('service_id', str, lambda x: x.srv_id)
                transducer.add_event_field('n_clients', int, lambda x: x.n_clients)
                transducer.add_event_field('req_type', str, lambda x: x.req_type)
                transducer.add_event_field('result', str, lambda x: x.result)
                transducer.add_event_field('window_n', int, lambda x: x.window.window_n)
                transducer.add_event_field('window_acc_delay', float, lambda x: x.window.window_acc_delay)
                transducer.add_event_field('window_mean_delay', float, lambda x: x.window.window_mean_delay)
                self.transducers.append(transducer)

            if self.edcs is not None and TransducersConfig.LOG_EDC_REPORT:
                transducer = Transducers.create_transducer(t_type, **t_config, transducer_id=f'{t_id}_edc_report',
                                                           sim_time_id='time', include_names=False)
                transducer.add_target_port(self.edcs.output_edc_report)
                transducer.drop_event_field('value')
                transducer.add_event_field('edc_id', str, lambda x: x.edc_id)
                transducer.add_event_field('it_power', float, lambda x: x.it_power)
                transducer.add_event_field('cooling_power', float, lambda x: x.cooling_power)
                transducer.add_event_field('power_demand', float, lambda x: x.power_demand)
                transducer.add_event_field('pue', float, lambda x: x.pue)
                for service in ServicesConfig.SERVICES:
                    transducer.add_event_field(f'{service}_expected_size', int, lambda x: x.srv_expected_size(service))
                    transducer.add_event_field(f'{service}_slice_size', int, lambda x: x.srv_slice_size(service))
                    transducer.add_event_field(f'{service}_slice_u', float, lambda x: x.srv_slice_u(service))
                    transducer.add_event_field(f'{service}_free_size', int, lambda x: x.srv_free_size(service))
                    transducer.add_event_field(f'{service}_free_u', float, lambda x: x.srv_free_u(service))
                    transducer.add_event_field(f'{service}_total_u', float, lambda x: x.srv_total_u(service))
                self.transducers.append(transducer)

            if self.edcs is not None and TransducersConfig.LOG_EDC_PROFILE:
                transducer = Transducers.create_transducer(t_type, **t_config, transducer_id=f'{t_id}_edc_profile',
                                                           sim_time_id='time', include_names=False)
                transducer.add_target_port(self.edcs.output_profile_report)
                transducer.drop_event_field('value')
                transducer.add_event_field('edc_id', str, lambda x: x.edc_id)
                transducer.add_event_field('service_id', str, lambda x: x.srv_id)
                transducer.add_event_field('n_clients', int, lambda x: x.n_clients)
                transducer.add_event_field('req_type', str, lambda x: x.req_type)
                transducer.add_event_field('result', str, lambda x: x.result)
                transducer.add_event_field('window_n', int, lambda x: x.window.window_n)
                transducer.add_event_field('window_acc_delay', float, lambda x: x.window.window_acc_delay)
                transducer.add_event_field('window_mean_delay', float, lambda x: x.window.window_mean_delay)

                self.transducers.append(transducer)

            if TransducersConfig.LOG_NET and self.xh is not None:
                transducer = Transducers.create_transducer(t_type, **t_config, transducer_id=f'{t_id}_network',
                                                           sim_time_id='time', include_names=False)
                transducer.add_target_port(self.xh.output_link_report)
                transducer.add_target_port(self.access.output_link_report)
                transducer.drop_event_field('value')
                transducer.add_event_field('node_from', str, lambda x: x.node_from)
                transducer.add_event_field('node_to', str, lambda x: x.node_to)
                transducer.add_event_field('frequency', float, lambda x: x.frequency)
                transducer.add_event_field('power', float, lambda x: x.power)
                transducer.add_event_field('noise', float, lambda x: x.noise)
                transducer.add_event_field('snr', float, lambda x: x.snr)
                transducer.add_event_field('bandwidth', float, lambda x: x.bandwidth)
                transducer.add_event_field('eff', float, lambda x: x.eff)
                transducer.add_event_field('rate', float, lambda x: x.rate)
                self.transducers.append(transducer)

            if TransducersConfig.LOG_SG and self.smart_grid is not None:
                transducer = Transducers.create_transducer(t_type, **t_config, transducer_id=f'{t_id}_smart_grid',
                                                           sim_time_id='time', include_names=False)
                for port in self.smart_grid.outputs_consumption.values():
                    transducer.add_target_port(port)
                transducer.drop_event_field('value')
                transducer.add_event_field('consumer_id', str, lambda x: x.consumer_id)
                transducer.add_event_field('provider_id', str, lambda x: x.provider_id)
                transducer.add_event_field('energy_cost', float, lambda x: x.energy_cost)
                transducer.add_event_field('power_consumption', float, lambda x: x.power_consumption)
                transducer.add_event_field('power_demand', float, lambda x: x.power_demand)
                transducer.add_event_field('power_storage', float, lambda x: x.power_storage)
                transducer.add_event_field('power_generation', float, lambda x: x.power_generation)
                transducer.add_event_field('allow_charge', bool, lambda x: x.allow_charge)
                transducer.add_event_field('allow_discharge', bool, lambda x: x.allow_discharge)
                transducer.add_event_field('energy_stored', float, lambda x: x.energy_stored)
                transducer.add_event_field('energy_capacity', float, lambda x: x.energy_capacity)
                transducer.add_event_field('acc_energy_consumption', float, lambda x: x.acc_energy_consumption)
                transducer.add_event_field('acc_energy_returned', float, lambda x: x.acc_energy_returned)
                transducer.add_event_field('acc_cost', float, lambda x: x.acc_cost)
                self.transducers.append(transducer)

    @staticmethod
    def new_mercury(config: MercuryConfig, lite: bool, p_type: Type[PacketInterface],
                    name: str = 'mercury') -> MercuryModelABC:
        if lite:
            return MercuryModelLite(config, name)
        elif p_type != PhysicalPacket:
            return MercuryModelShortcut(config, p_type, name)
        return MercuryModel(config, name)


class MercuryModel(MercuryModelABC[PhysicalPacket]):
    edcs: EdgeDataCenters[PhysicalPacket]
    xh: CrosshaulNetwork
    gws: Gateways
    access: AccessNetwork
    clients: Clients

    def __init__(self, config: MercuryConfig, name: str = 'mercury'):
        super().__init__(config, False, PhysicalPacket, name)

    def _add_specific_couplings(self):
        # couplings between XH network and cloud
        if self.cloud is not None:
            self.add_coupling(self.cloud.output_data, self.xh.input_data)
            self.add_coupling(self.xh.outputs_data[self.cloud.cloud_id], self.cloud.input_data)
        # couplings between XH network and gateways
        self.add_coupling(self.gws.output_xh, self.xh.input_data)
        for gw_id, in_port in self.gws.inputs_xh.items():
            self.add_coupling(self.xh.outputs_data[gw_id], in_port)
        # Couplings between gateways and access network
        self.add_coupling(self.gws.output_wired, self.access.input_wired)
        self.add_coupling(self.gws.output_wireless_acc, self.access.input_wireless_acc)
        self.add_coupling(self.gws.output_wireless_srv, self.access.input_wireless_srv)
        self.add_coupling(self.gws.output_channel_share, self.access.input_share)
        for gw_id, in_port in self.gws.inputs_acc.items():
            self.add_coupling(self.access.outputs_ul[gw_id], in_port)
        for gw_id, in_port in self.gws.inputs_send_pss.items():
            self.add_coupling(self.access.outputs_send_pss[gw_id], in_port)
        # Couplings between clients and access network
        self.add_coupling(self.clients.output_create_client, self.access.input_create_client)
        self.add_coupling(self.clients.output_remove_client, self.access.input_remove_client)
        self.add_coupling(self.clients.output_send_pss, self.access.input_send_pss)
        self.add_coupling(self.clients.output_phys_wired, self.access.input_wired)
        self.add_coupling(self.clients.output_phys_wireless_acc, self.access.input_wireless_acc)
        self.add_coupling(self.clients.output_phys_wireless_srv, self.access.input_wireless_srv)
        self.add_coupling(self.access.output_dl, self.clients.input_phys)
        # Couplings between mobility manager and access network
        self.add_coupling(self.mobility.output_new_location, self.access.input_new_location)
        # Couplings between mobility manager and clients
        self.add_coupling(self.mobility.output_new_location, self.clients.input_new_location)


class MercuryModelShortcut(MercuryModelABC, Generic[PacketInterface]):
    edcs: EdgeDataCenters[PacketInterface]
    gws: GatewaysShortcut
    access: AccessNetworkShortcut
    clients: ClientsShortcut
    shortcut: PacketMultiplexer[PacketInterface]

    def __init__(self, config: MercuryConfig, p_type: Type[PacketInterface], name: str = 'mercury'):
        if p_type not in [AppPacket, NetworkPacket]:
            raise ValueError('invalid value of p_type')
        super().__init__(config, False, p_type, name)

    def _add_specific_couplings(self):
        # couplings between XH network and cloud
        if self.cloud is not None:
            self.add_coupling(self.cloud.output_data, self.shortcut.input_data)
            self.add_coupling(self.shortcut.outputs_data[self.cloud.cloud_id], self.cloud.input_data)
        # Couplings between shortcut and gateways
        self.add_coupling(self.gws.output_data, self.shortcut.input_data)
        for gw_id, in_port in self.gws.inputs_data.items():
            self.add_coupling(self.shortcut.outputs_data[gw_id], in_port)
        # Couplings between gateways and access network
        self.add_coupling(self.gws.output_phys_pss, self.access.input_data)
        for gw_id, in_port in self.gws.inputs_send_pss.items():
            self.add_coupling(self.access.outputs_send_pss[gw_id], in_port)
        # Couplings between clients and shortcut
        self.add_coupling(self.clients.output_data, self.shortcut.input_data)
        self.add_coupling(self.shortcut.output_clients, self.clients.input_data)
        # Couplings between clients and access network
        self.add_coupling(self.clients.output_create_client, self.access.input_create_client)
        self.add_coupling(self.clients.output_remove_client, self.access.input_remove_client)
        self.add_coupling(self.clients.output_send_pss, self.access.input_send_pss)
        self.add_coupling(self.access.output_clients, self.clients.input_phys_pss)
        # Couplings between mobility manager and access network
        self.add_coupling(self.mobility.output_new_location, self.clients.input_new_location)
        self.add_coupling(self.mobility.output_new_location, self.access.input_new_location)
        # Couplings between mobility manager and clients
        self.add_coupling(self.mobility.output_new_location, self.clients.input_new_location)


class MercuryModelLite(MercuryModelABC[AppPacket]):
    edcs: EdgeDataCenters[AppPacket]
    gws: GatewaysLite
    clients: ClientsLite
    shortcut: PacketMultiplexer[AppPacket]

    def __init__(self, config: MercuryConfig, name: str = 'mercury'):
        super().__init__(config, True, AppPacket, name)

    def _add_specific_couplings(self):
        # couplings between XH network and cloud
        if self.cloud is not None:
            self.add_coupling(self.cloud.output_data, self.shortcut.input_data)
            self.add_coupling(self.shortcut.outputs_data[self.cloud.cloud_id], self.cloud.input_data)
        # Couplings between shortcut and gateways
        self.add_coupling(self.gws.output_data, self.shortcut.input_data)
        self.add_coupling(self.shortcut.outputs_data[GatewaysConfig.GATEWAYS_LITE], self.gws.input_data)
        # Couplings between shortcut and clients
        self.add_coupling(self.clients.output_data, self.shortcut.input_data)
        self.add_coupling(self.shortcut.output_clients, self.clients.input_data)
        # Couplings between clients and gateways
        self.add_coupling(self.clients.output_create_client, self.gws.input_create_client)
        self.add_coupling(self.clients.output_remove_client, self.gws.input_remove_client)
        # Couplings between mobility manager and gateways
        self.add_coupling(self.mobility.output_new_location, self.gws.input_new_location)
