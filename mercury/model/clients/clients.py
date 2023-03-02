from __future__ import annotations
from abc import ABC, abstractmethod
from math import inf
from mercury.config.client import ClientConfig
from mercury.config.gateway import GatewaysConfig
from mercury.config.network import DynamicNodeConfig
from mercury.msg.client import SendPSS, ServiceReport
from mercury.msg.network import NewNodeLocation
from mercury.msg.packet import AppPacket, PhysicalPacket, PacketInterface
from typing import Generic, Type
from xdevs.models import Port
from xdevs.sim import Coordinator, SimulationClock
from .client import ClientABC, Client, ClientShortcut, ClientLite
from ...model.common import ExtendedAtomic


class ClientsABC(ExtendedAtomic, ABC):
    def __init__(self):
        super().__init__('clients')
        self.clients: dict[str, Coordinator] = dict()
        self.root_clock: SimulationClock = SimulationClock()  # Root simulation clock shared among all the clients

        # Define common input/output ports
        self.input_create_client: Port[ClientConfig] = Port(ClientConfig, 'input_create_client')
        self.output_create_client: Port[DynamicNodeConfig] = Port(DynamicNodeConfig, 'output_create_client')
        self.output_remove_client: Port[str] = Port(str, 'output_remove_client')
        self.output_srv_report: Port[ServiceReport] = Port(ServiceReport, 'output_srv_report')
        self.add_in_port(self.input_create_client)
        self.add_out_port(self.output_create_client)
        self.add_out_port(self.output_remove_client)
        self.add_out_port(self.output_srv_report)

    def deltint_extension(self):
        self.root_clock.time += self.sigma  # simulation clock advances according to sigma
        self.clients_internal()             # resolve any internal event of existing clients
        next_sigma = self.next_sigma()
        self.hold_in('passive', next_sigma)

    def deltext_extension(self, e):
        self.root_clock.time += e  # simulation clock advances according to elapsed time
        for client_config in self.input_create_client.values:
            self.create_client(client_config)
        for client_id in self.forward_input():  # Single delta to those clients that have received a message
            if self.clients[client_id].time_next == self.root_clock.time:
                self.clients[client_id].lambdaf()
                self.collect_output(self.clients[client_id].model)
            self.clients[client_id].deltfcn()
            self.clients[client_id].clear()
        self.clients_internal()                 # resolve any internal event of existing clientss
        self.remove_clients()                   # remove outdated clientss
        self.hold_in('passive', self.next_sigma())

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.hold_in('passive', self.next_sigma())

    def exit(self):
        pass

    def create_client(self, client_config: ClientConfig):
        client_id: str = client_config.client_id
        if client_id in self.clients:
            raise ValueError(f'client with id {client_id} already exists')
        client = Coordinator(self._create_client(client_config), self.root_clock)
        client.initialize()
        self.clients[client_id] = client
        self.add_msg_to_queue(self.output_create_client, client_config.node_config)

    def clients_internal(self):
        for client_id, client in self.clients.items():
            # we execute as many internal transitions as needed to get a sigma greater than zero
            while client.time_next <= self.root_clock.time:
                client.lambdaf()                    # We trigger their lambdas...
                self.collect_output(client.model)   # ... collect output messages to forward them...
                client.deltfcn()                    # ... Compute the next client state...
                client.clear()                      # ... and clear the output

    def remove_clients(self):
        trash = {client_id for client_id, client in self.clients.items() if client.model.ready_to_dump}
        for client_id in trash:
            self.clients.pop(client_id)
            self.add_msg_to_queue(self.output_remove_client, client_id)

    def next_sigma(self):
        if self.msg_queue_empty():
            min_next_t_client = min((client.time_next for client in self.clients.values()), default=inf)
            return min_next_t_client - self.root_clock.time
        return 0

    @abstractmethod
    def _create_client(self, client_config: ClientConfig) -> ClientABC:
        pass

    @abstractmethod
    def collect_output(self, client: ClientABC):
        pass

    @abstractmethod
    def forward_input(self) -> set[str]:
        pass

    @staticmethod
    def new_clients(lite: bool, p_type: Type[PacketInterface]) -> ClientsABC:
        if lite:
            return ClientsLite()
        elif p_type == PhysicalPacket:
            return Clients()
        else:
            return ClientsShortcut(p_type)


class Clients(ClientsABC):
    def __init__(self):
        super().__init__()
        self.input_phys: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_phys')
        self.input_new_location: Port[NewNodeLocation] = Port(NewNodeLocation, 'input_new_location')
        self.output_phys_wired: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_wired_acc')
        self.output_phys_wireless_acc: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_wireless_acc')
        self.output_phys_wireless_srv: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_wireless_srv')
        self.output_send_pss: Port[SendPSS] = Port(SendPSS, 'output_send_pss')
        self.add_in_port(self.input_phys)
        self.add_in_port(self.input_new_location)
        self.add_out_port(self.output_phys_wired)
        self.add_out_port(self.output_phys_wireless_acc)
        self.add_out_port(self.output_phys_wireless_srv)
        self.add_out_port(self.output_send_pss)

    def _create_client(self, client_config: ClientConfig) -> Client:
        return Client(client_config)

    def collect_output(self, client: Client):
        if client.wireless:
            output_phys_acc, output_phys_srv = self.output_phys_wireless_acc, self.output_phys_wireless_srv
        else:
            output_phys_acc, output_phys_srv = self.output_phys_wired, self.output_phys_wired
        for port_from, port_to in [(client.output_send_pss, self.output_send_pss),
                                   (client.output_srv_report, self.output_srv_report),
                                   (client.output_phys_acc, output_phys_acc),
                                   (client.output_phys_srv, output_phys_srv)]:
            for msg in port_from.values:
                self.add_msg_to_queue(port_to, msg)

    def forward_input(self) -> set[str]:
        imminent_clients = set()
        for msg in self.input_phys.values:
            if msg.node_to in self.clients:
                imminent_clients.add(msg.node_to)
                self.clients[msg.node_to].model.input_phys.add(msg)
        for msg in self.input_new_location.values:
            if msg.node_id in self.clients:
                imminent_clients.add(msg.node_id)
                self.clients[msg.node_id].model.input_new_location.add(msg)
        return imminent_clients


class ClientsShortcut(ClientsABC, Generic[PacketInterface]):
    def __init__(self, p_type: Type[PacketInterface]):
        self.p_type: Type[PacketInterface] = p_type
        super().__init__()
        self.input_data: Port[PacketInterface] = Port(self.p_type, 'input_data')
        self.input_phys_pss: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_phys_pss')
        self.input_new_location: Port[NewNodeLocation] = Port(NewNodeLocation, 'input_new_location')
        self.output_data: Port[PacketInterface] = Port(self.p_type, 'output_data')
        self.output_send_pss: Port[SendPSS] = Port(SendPSS, 'output_send_pss')
        self.add_in_port(self.input_data)
        self.add_in_port(self.input_phys_pss)
        self.add_in_port(self.input_new_location)
        self.add_out_port(self.output_data)
        self.add_out_port(self.output_send_pss)

    def _create_client(self, client_config: ClientConfig) -> ClientShortcut:
        return ClientShortcut(self.p_type, client_config)

    def collect_output(self, client: ClientShortcut):
        for port_from, port_to in [(client.output_send_pss, self.output_send_pss),
                                   (client.output_srv_report, self.output_srv_report),
                                   (client.output_data, self.output_data)]:
            for msg in port_from.values:
                self.add_msg_to_queue(port_to, msg)

    def forward_input(self) -> set[str]:
        imminent_clients = set()
        for msg in self.input_data.values:
            if msg.node_to in self.clients:
                imminent_clients.add(msg.node_to)
                self.clients[msg.node_to].model.input_data.add(msg)
        for msg in self.input_phys_pss.values:
            if msg.node_to in self.clients:
                imminent_clients.add(msg.node_to)
                self.clients[msg.node_to].model.input_phys_pss.add(msg)
        for msg in self.input_new_location.values:
            if msg.node_id in self.clients:
                imminent_clients.add(msg.node_id)
                self.clients[msg.node_id].model.input_new_location.add(msg)
        return imminent_clients


class ClientsLite(ClientsABC):
    def __init__(self):
        super().__init__()
        self.input_data: Port[AppPacket] = Port(AppPacket, 'input_data')
        self.output_data: Port[AppPacket] = Port(AppPacket, 'output_data')
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_data)

    def _create_client(self, client_config: ClientConfig) -> ClientLite:
        return ClientLite(client_config, GatewaysConfig.GATEWAYS_LITE)

    def collect_output(self, client: ClientLite):
        for port_from, port_to in [(client.output_srv_report, self.output_srv_report),
                                   (client.output_data, self.output_data)]:
            for msg in port_from.values:
                self.add_msg_to_queue(port_to, msg)

    def forward_input(self) -> set[str]:
        imminent_clients = set()
        for msg in self.input_data.values:
            if msg.node_to in self.clients:
                imminent_clients.add(msg.node_to)
                self.clients[msg.node_to].model.input_data.add(msg)
        return imminent_clients
