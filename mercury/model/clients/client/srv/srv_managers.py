from __future__ import annotations
from math import inf
from mercury.config.client import SrvConfig
from mercury.config.transducers import TransducersConfig
from mercury.msg.packet import AppPacket
from mercury.msg.packet.app_packet.srv_packet import SrvRelatedResponse
from mercury.msg.client import GatewayConnection, ServiceActive, ServiceReport
from typing import Iterable
from xdevs.models import Coupled, Port
from .srv_manager import SrvManager
from ....common import Multiplexer


class ServiceMux(Multiplexer):
    def __init__(self, client_id: str, services: Iterable[str]):
        self.input_srv: Port[AppPacket] = Port(AppPacket, 'input_srv')
        self.outputs_srv: dict[str, Port[AppPacket]] = {srv: Port(AppPacket, f'output_srv_{srv}') for srv in services}
        super().__init__(f'{client_id}_srv_mux')
        self.add_in_port(self.input_srv)
        [self.add_out_port(port) for port in self.outputs_srv.values()]

    def build_routing_table(self):
        """Fills the routing table with the correspondent links"""
        self.routing_table[self.input_srv] = self.outputs_srv

    def get_node_to(self, msg: SrvRelatedResponse) -> str:
        """Routes any service response message to the correspondent service"""
        return msg.service_id


class SrvManagers(Coupled):
    def __init__(self, client_id: str, services: dict[str, SrvConfig],
                 gateway: str | None, t_start: float = 0, t_end: float = inf):
        super().__init__(f'{client_id}_srv_suite')
        self.input_srv: Port[AppPacket] = Port(AppPacket, 'input_srv')
        self.input_gateway: Port[GatewayConnection] = Port(GatewayConnection, 'input_gateway')
        self.output_srv: Port[AppPacket] = Port(AppPacket, 'output_srv')
        self.output_active: Port[ServiceActive] = Port(ServiceActive, 'output_active')
        self.output_report: Port[ServiceReport] = Port(ServiceReport, 'output_report')
        self.add_in_port(self.input_srv)
        self.add_in_port(self.input_gateway)
        self.add_out_port(self.output_srv)
        self.add_out_port(self.output_active)
        self.add_out_port(self.output_report)

        self.srv_mux: ServiceMux = ServiceMux(client_id, services)
        self.add_component(self.srv_mux)
        self.add_coupling(self.input_srv, self.srv_mux.input_srv)

        self.srv_managers: list[SrvManager] = list()
        for service_id, srv_config in services.items():
            srv_manager = SrvManager(client_id, srv_config, gateway, t_start, t_end)
            self.srv_managers.append(srv_manager)
            self.add_component(srv_manager)
            self.add_coupling(self.srv_mux.outputs_srv[service_id], srv_manager.input_srv)
            self.add_coupling(self.input_gateway, srv_manager.input_gateway)
            self.add_coupling(srv_manager.output_srv, self.output_srv)
            self.add_coupling(srv_manager.output_active, self.output_active)
            if TransducersConfig.LOG_SRV:
                self.add_coupling(srv_manager.output_report, self.output_report)

    @property
    def ready_to_dump(self) -> bool:
        return all(srv_manager.ready_to_dump for srv_manager in self.srv_managers)


def create_srv_manager(client_id: str, services: dict[str, SrvConfig], gateway: str | None,
                       t_start: float = 0, t_end: float = inf) -> SrvManager | SrvManagers:
    if len(services) == 1:
        return SrvManager(client_id, list(services.values())[0], gateway, t_start, t_end)
    return SrvManagers(client_id, services, gateway, t_start, t_end)
