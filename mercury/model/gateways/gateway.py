from __future__ import annotations
from abc import ABC
from mercury.config.edcs import EdgeFederationConfig
from mercury.config.gateway import GatewayConfig, GatewaysConfig
from mercury.msg.network import ChannelShare
from mercury.msg.packet import AppPacket, NetworkPacket, PhysicalPacket, PacketInterface
from mercury.utils.amf import AccessManagementFunction
from mercury.utils.maths import euclidean_distance
from typing import Generic, Type
from xdevs.models import Coupled, Port
from .acc_manager import AccessManager
from .gw_trx import AccessTransceiver, CrosshaulTransceiver
from .shortcut import Shortcut
from ..common.net_manager import NetworkManager


class GatewayABC(Coupled, ABC):
    def __init__(self, gw_config: GatewayConfig, default_server: str, amf: AccessManagementFunction):
        """
        Abstract DEVS model of gateway.
        :param gw_config: gateway configuration parameters.
        :param default_server:
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        self.gateway_id: str = gw_config.gateway_id
        self.wired: bool = gw_config.wired
        super().__init__(f'gateway_{self.gateway_id}')
        self.manager: AccessManager = AccessManager(self.gateway_id, self.wired, default_server, amf)
        self.add_component(self.manager)
        if not self.wired:
            self.input_send_pss: Port[str] = Port(str, 'input_send_pss')
            self.output_channel_share: Port[ChannelShare] = Port(ChannelShare, 'output_channel_share')
            self.add_in_port(self.input_send_pss)
            self.add_out_port(self.output_channel_share)
            self.add_coupling(self.input_send_pss, self.manager.input_send_pss)
            self.add_coupling(self.manager.output_channel_share, self.output_channel_share)

    @staticmethod
    def new_gw(p_type: Type[PacketInterface], gw_config: GatewayConfig,
               default_server: str, amf: AccessManagementFunction) -> GatewayABC:
        return Gateway(gw_config, default_server, amf) if p_type == PhysicalPacket \
            else GatewayShortcut(p_type, gw_config, default_server, amf)


class Gateway(GatewayABC):
    def __init__(self, gw_config: GatewayConfig, default_server: str, amf: AccessManagementFunction):
        """
        DEVS model of gateway (complete model).
        :param gw_config: gateway configuration parameters.
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        super().__init__(gw_config, default_server, amf)
        self.acc_net_manager: NetworkManager = NetworkManager(self.gateway_id, manager_id='acc_net_manager')
        self.xh_net_manager: NetworkManager = NetworkManager(self.gateway_id, manager_id='xh_net_manager')
        self.acc_trx: AccessTransceiver = AccessTransceiver(self.gateway_id, gw_config.wired)
        self.xh_trx: CrosshaulTransceiver = CrosshaulTransceiver(self.gateway_id)
        for component in self.acc_net_manager, self.xh_net_manager, self.acc_trx, self.xh_trx:
            self.add_component(component)

        # INPUT/OUTPUT PORTS
        self.input_xh: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_xh')
        self.input_acc: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_acc')
        self.output_xh: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_xh')
        self.output_acc: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_acc')
        self.output_srv: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_srv')
        self.add_in_port(self.input_xh)
        self.add_in_port(self.input_acc)
        self.add_out_port(self.output_xh)
        self.add_out_port(self.output_acc)
        self.add_out_port(self.output_srv)

        # COUPLINGS
        self.add_coupling(self.input_xh, self.xh_trx.input_phys)
        self.add_coupling(self.input_acc, self.acc_trx.input_phys)

        self.add_coupling(self.xh_trx.output_phys, self.output_xh)
        self.add_coupling(self.acc_trx.output_phys_acc, self.output_acc)
        self.add_coupling(self.acc_trx.output_phys_srv, self.output_srv)

        self.add_coupling(self.xh_trx.output_net_to_acc, self.manager.input_net)
        self.add_coupling(self.manager.output_xh_net, self.xh_trx.input_net)
        self.add_coupling(self.acc_trx.output_net_to_xh, self.manager.input_net)
        self.add_coupling(self.manager.output_access_net, self.acc_trx.input_net)

        self.add_coupling(self.xh_trx.output_net, self.xh_net_manager.input_net)
        self.add_coupling(self.xh_net_manager.output_net, self.xh_trx.input_net)
        self.add_coupling(self.manager.output_xh_app, self.xh_net_manager.input_app)
        self.add_coupling(self.xh_net_manager.output_app, self.manager.input_app)

        self.add_coupling(self.acc_trx.output_net, self.acc_net_manager.input_net)
        self.add_coupling(self.acc_net_manager.output_net, self.acc_trx.input_net)
        self.add_coupling(self.manager.output_access_acc, self.acc_net_manager.input_app)
        self.add_coupling(self.acc_net_manager.output_app, self.manager.input_app)


class GatewayShortcut(GatewayABC, Generic[PacketInterface]):
    def __init__(self, p_type: Type[PacketInterface], gw_config: GatewayConfig,
                 default_server: str, amf: AccessManagementFunction):
        """
        DEVS model of gateway (shortcut model).
        :param p_type: input/output data ports type.
        :param gw_config: gateway configuration parameters.
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        super().__init__(gw_config, default_server, amf)
        # GENERIC COMPONENTS (regardless of p_type)
        if not self.wired:
            self.shortcut: Shortcut = Shortcut(self.gateway_id)
            self.add_component(self.shortcut)

        # INPUT/OUTPUT PORTS
        self.input_data: Port[PacketInterface] = Port(p_type, 'input_data')
        self.output_data: Port[PacketInterface] = Port(p_type, 'output_data')
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_data)
        if not self.wired:
            self.output_phys_pss: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_pss')
            self.add_out_port(self.output_phys_pss)
            # GENERIC COUPLINGS (regardless of p_type)
            self.add_coupling(self.manager.output_access_acc, self.shortcut.input_app)
            self.add_coupling(self.shortcut.output_phys, self.output_phys_pss)

        # MODEL SPECIFICATION (depending on p_type)
        acc_port = self.manager.output_access_acc if self.wired else self.shortcut.output_app
        if p_type == AppPacket:
            self.add_coupling(self.input_data, self.manager.input_app)
            self.add_coupling(self.manager.output_access_srv, self.output_data)
            self.add_coupling(self.manager.output_xh_app, self.output_data)
            self.add_coupling(acc_port, self.output_data)
        elif p_type == NetworkPacket:
            self.net_manager: NetworkManager = NetworkManager(self.gateway_id)
            self.add_component(self.net_manager)

            self.add_coupling(self.input_data, self.net_manager.input_net)
            self.add_coupling(self.net_manager.output_app, self.manager.input_app)
            self.add_coupling(self.manager.output_access_srv, self.net_manager.input_app)
            self.add_coupling(self.manager.output_xh_app, self.net_manager.input_app)
            self.add_coupling(acc_port, self.net_manager.input_app)
            self.add_coupling(self.net_manager.output_net, self.output_data)
        else:
            raise ValueError(f'Invalid value for p_type ({p_type})')


class GatewaysABC(Coupled, ABC):
    def __init__(self, p_type: Type[PacketInterface], gws_config: GatewaysConfig,
                 edge_fed_config: EdgeFederationConfig, amf: AccessManagementFunction):
        """
        Model containing all the gateways of the scenario.
        :param p_type: input/output data ports type.
        :param gws_config: Configuration for all the gateways.
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        super().__init__('gateways')
        default_servers: dict[str, str] = dict()
        for gw_id, gw_config in gws_config.gateways.items():
            best_server_id, best_distance = None, None
            for edc_id, edc_config in edge_fed_config.edcs_config.items():
                distance = euclidean_distance(gw_config.location, edc_config.location)
                if best_server_id is None or distance < best_distance:
                    best_server_id, best_distance = edc_id, distance
            if best_server_id is None:
                best_server_id = edge_fed_config.cloud_id
            assert best_server_id is not None
            default_servers[gw_id] = best_server_id
        self.gateways: dict[str, GatewayABC] = {gw_id: Gateway.new_gw(p_type, gw_config, default_servers[gw_id], amf)
                                                for gw_id, gw_config in gws_config.gateways.items()}
        self.output_channel_share = Port(ChannelShare, 'output_channel_share')
        self.add_out_port(self.output_channel_share)
        self.inputs_send_pss: dict[str, Port[str]] = dict()
        for gateway_id, gateway in self.gateways.items():
            self.add_component(gateway)
            if not gateway.wired:
                self.inputs_send_pss[gateway_id] = Port(str, f'input_{gateway_id}_repeat_pss')
                self.add_in_port(self.inputs_send_pss[gateway_id])
                self.add_coupling(self.inputs_send_pss[gateway_id], gateway.input_send_pss)
                self.add_coupling(gateway.output_channel_share, self.output_channel_share)

    @staticmethod
    def new_gws(p_type: Type[PacketInterface], gws_config: GatewaysConfig,
                edge_fed_config: EdgeFederationConfig, amf: AccessManagementFunction) -> GatewaysABC:
        return Gateways(gws_config, edge_fed_config, amf) if p_type == PhysicalPacket \
            else GatewaysShortcut(p_type, gws_config, edge_fed_config, amf)


class Gateways(GatewaysABC):
    gateways: dict[str, Gateway]

    def __init__(self, gws_config: GatewaysConfig,
                 edge_fed_config: EdgeFederationConfig, amf: AccessManagementFunction):
        """
        Model containing all the gateways of the scenario.
        :param gws_config: Configuration for all the gateways.
        :param edge_fed_config:
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        super().__init__(PhysicalPacket, gws_config, edge_fed_config, amf)
        # INPUT/OUTPUT PORTS
        self.output_xh: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_xh')
        self.output_wired: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_wired')
        self.output_wireless_acc: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_wireless_acc')
        self.output_wireless_srv: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_wireless_srv')

        self.add_out_port(self.output_xh)
        self.add_out_port(self.output_wired)
        self.add_out_port(self.output_wireless_acc)
        self.add_out_port(self.output_wireless_srv)

        self.inputs_xh: dict[str, Port[PhysicalPacket]] = dict()
        self.inputs_acc: dict[str, Port[PhysicalPacket]] = dict()
        for gateway_id, gateway in self.gateways.items():
            self.inputs_xh[gateway_id] = Port(PhysicalPacket, f'input_{gateway_id}_xh')
            self.inputs_acc[gateway_id] = Port(PhysicalPacket, f'input_{gateway_id}_acc')
            self.add_in_port(self.inputs_xh[gateway_id])
            self.add_in_port(self.inputs_acc[gateway_id])
            self.add_coupling(self.inputs_xh[gateway_id], gateway.input_xh)
            self.add_coupling(self.inputs_acc[gateway_id], gateway.input_acc)
            self.add_coupling(gateway.output_xh, self.output_xh)
            if gateway.wired:
                self.add_coupling(gateway.output_acc, self.output_wired)
                self.add_coupling(gateway.output_srv, self.output_wired)
            else:
                self.add_coupling(gateway.output_acc, self.output_wireless_acc)
                self.add_coupling(gateway.output_srv, self.output_wireless_srv)


class GatewaysShortcut(GatewaysABC, Generic[PacketInterface]):
    gateways: dict[str, GatewayShortcut]

    def __init__(self, p_type: Type[PacketInterface], gws_config: GatewaysConfig,
                 edge_fed_config: EdgeFederationConfig, amf: AccessManagementFunction):
        """
        Model containing all the gateways of the scenario.
        :param p_type: input/output data ports type.
        :param gws_config: Configuration for all the gateways.
        :param edge_fed_config:
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        super().__init__(p_type, gws_config, edge_fed_config, amf)
        self.output_data: Port[PacketInterface] = Port(p_type, 'output_data')
        self.output_phys_pss: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_pss')
        self.add_out_port(self.output_data)
        self.add_out_port(self.output_phys_pss)

        self.inputs_data: dict[str, Port[PacketInterface]] = dict()
        for gateway_id, gateway in self.gateways.items():
            self.inputs_data[gateway_id] = Port(p_type, f'input_{gateway_id}_data')
            self.add_in_port(self.inputs_data[gateway_id])

            self.add_coupling(self.inputs_data[gateway_id], gateway.input_data)
            self.add_coupling(gateway.output_data, self.output_data)
            if not gateway.wired:
                self.add_coupling(gateway.output_phys_pss, self.output_phys_pss)
