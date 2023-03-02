from __future__ import annotations
from abc import ABC
from mercury.config.client import ClientConfig
from mercury.msg.network import NewNodeLocation
from mercury.msg.packet import PhysicalPacket, NetworkPacket, AppPacket, PacketInterface
from mercury.msg.client import SendPSS, ServiceReport
from typing import Generic, Type
from xdevs.models import Coupled, Port
from .acc_manager import AccessManager
from .acc_trx import ClientAccessTransceiver
from .shortcut import Shortcut
from .srv import SrvManager, SrvManagers, create_srv_manager
from ...common import NetworkManager


class ClientABC(Coupled, ABC):
    def __init__(self, client_config: ClientConfig, gw_id: str | None):
        """
        Model of edge computing client.
        :param client_config: Client configuration.
        :param gw_id: ID of the default gateway (only for lite clients)
        """
        self.client_id: str = client_config.client_id
        self.wireless: bool = client_config.wireless
        super().__init__(f'client_{self.client_id}')

        self.srv_manager: SrvManager | SrvManagers = create_srv_manager(self.client_id, client_config.services, gw_id,
                                                                        client_config.t_start, client_config.t_end)
        self.add_component(self.srv_manager)
        self.acc_manager: AccessManager | None = None
        if gw_id is None:
            self.acc_manager = AccessManager(client_config.node_config)
            self.add_component(self.acc_manager)

        self.output_srv_report: Port[ServiceReport] = Port(ServiceReport, 'output_srv_report')
        self.add_out_port(self.output_srv_report)
        if self.acc_manager is not None:
            self.input_new_location: Port[NewNodeLocation] = Port(NewNodeLocation, 'input_new_location')
            self.output_send_pss: Port[SendPSS] = Port(SendPSS, 'output_send_pss')
            self.add_in_port(self.input_new_location)
            self.add_out_port(self.output_send_pss)

        self.add_coupling(self.srv_manager.output_report, self.output_srv_report)
        if self.acc_manager is not None:
            self.add_coupling(self.input_new_location, self.acc_manager.input_new_location)
            self.add_coupling(self.srv_manager.output_active, self.acc_manager.input_srv_active)
            self.add_coupling(self.acc_manager.output_gateway, self.srv_manager.input_gateway)
            self.add_coupling(self.acc_manager.output_send_pss, self.output_send_pss)

    @property
    def ready_to_dump(self) -> bool:
        return self.srv_manager.ready_to_dump and (self.acc_manager is None or self.acc_manager.ready_to_dump)


class Client(ClientABC):
    def __init__(self, client_config: ClientConfig):
        """
        Model of edge computing client.
        :param client_config: Client configuration.
        """
        super().__init__(client_config, None)
        self.client_trx: ClientAccessTransceiver = ClientAccessTransceiver(self.client_id, not client_config.wireless,
                                                                           client_config.t_start)
        self.net_acc_manager: NetworkManager = NetworkManager(self.client_id, 'net_acc_manager')
        self.net_srv_manager: NetworkManager = NetworkManager(self.client_id, 'net_srv_manager', False)
        for component in self.client_trx, self.net_acc_manager, self.net_srv_manager:
            self.add_component(component)

        self.input_phys: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_phys_acc')
        self.output_phys_acc: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_acc')
        self.output_phys_srv: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_srv')
        self.add_in_port(self.input_phys)
        self.add_out_port(self.output_phys_acc)
        self.add_out_port(self.output_phys_srv)

        self.add_coupling(self.input_phys, self.client_trx.input_phys)
        self.add_coupling(self.client_trx.output_phys_acc, self.output_phys_acc)
        self.add_coupling(self.client_trx.output_phys_srv, self.output_phys_srv)

        self.add_coupling(self.acc_manager.output_gateway, self.client_trx.input_gateway)
        self.add_coupling(self.acc_manager.output_connected, self.net_srv_manager.input_ctrl)

        self.add_coupling(self.client_trx.output_net_acc, self.net_acc_manager.input_net)
        self.add_coupling(self.client_trx.output_net_srv, self.net_srv_manager.input_net)
        self.add_coupling(self.net_acc_manager.output_app, self.acc_manager.input_acc)
        self.add_coupling(self.net_srv_manager.output_app, self.srv_manager.input_srv)
        self.add_coupling(self.acc_manager.output_acc, self.net_acc_manager.input_app)
        self.add_coupling(self.srv_manager.output_srv, self.net_srv_manager.input_app)
        self.add_coupling(self.net_acc_manager.output_net, self.client_trx.input_net)
        self.add_coupling(self.net_srv_manager.output_net, self.client_trx.input_net)


class ClientShortcut(ClientABC, Generic[PacketInterface]):
    def __init__(self, p_type: Type[PacketInterface], client_config: ClientConfig):
        """
        Model of edge computing client.
        :param p_type: input/output data ports type.
        :param client_config: Client configuration.
        """
        super().__init__(client_config, None)
        self.shortcut: Shortcut[PacketInterface] = Shortcut(p_type, client_config.client_id)
        self.add_component(self.shortcut)

        self.input_data: Port[PacketInterface] = Port(p_type, 'input_data')
        self.input_phys_pss: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_phys_pss')
        self.output_data: Port[PacketInterface] = Port(p_type, 'output_data')
        self.add_in_port(self.input_data)
        self.add_in_port(self.input_phys_pss)
        self.add_out_port(self.output_data)

        self.add_coupling(self.input_data, self.shortcut.input_data)
        self.add_coupling(self.input_phys_pss, self.shortcut.input_phys_pss)
        self.add_coupling(self.shortcut.output_app_pss, self.acc_manager.input_acc)

        if p_type == AppPacket:
            self.add_coupling(self.shortcut.output_data_acc, self.acc_manager.input_acc)
            self.add_coupling(self.shortcut.output_data_srv, self.srv_manager.input_srv)
            self.add_coupling(self.acc_manager.output_acc, self.output_data)
            self.add_coupling(self.srv_manager.output_srv, self.output_data)
        elif p_type == NetworkPacket:
            self.net_acc_manager: NetworkManager = NetworkManager(self.client_id, 'net_acc_manager')
            self.net_srv_manager: NetworkManager = NetworkManager(self.client_id, 'net_srv_manager', False)
            self.add_component(self.net_acc_manager)
            self.add_component(self.net_srv_manager)

            self.add_coupling(self.shortcut.output_data_acc, self.net_acc_manager.input_net)
            self.add_coupling(self.shortcut.output_data_srv, self.net_srv_manager.input_net)
            self.add_coupling(self.acc_manager.output_acc, self.net_acc_manager.input_app)
            self.add_coupling(self.acc_manager.output_connected, self.net_srv_manager.input_ctrl)
            self.add_coupling(self.srv_manager.output_srv, self.net_srv_manager.input_app)
            self.add_coupling(self.net_acc_manager.output_app, self.acc_manager.input_acc)
            self.add_coupling(self.net_srv_manager.output_app, self.srv_manager.input_srv)
            self.add_coupling(self.net_acc_manager.output_net, self.output_data)
            self.add_coupling(self.net_srv_manager.output_net, self.output_data)
        else:
            raise ValueError(f'Invalid value for p_type ({p_type})')


class ClientLite(ClientABC):
    def __init__(self, client_config: ClientConfig, gw_id: str):
        """
        Model of edge computing client.
        :param client_config: Client configuration.
        :param gw_id: ID of the default gateway (only for lite clients)
        """
        super().__init__(client_config, gw_id)
        self.input_data: Port[AppPacket] = Port(AppPacket, 'input_data')
        self.output_data: Port[AppPacket] = Port(AppPacket, 'output_data')
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_data)
        self.add_coupling(self.input_data, self.srv_manager.input_srv)
        self.add_coupling(self.srv_manager.output_srv, self.output_data)
