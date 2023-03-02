from __future__ import annotations
from mercury.config.edcs import EdgeFederationConfig
from mercury.config.gateway import GatewaysConfig
from mercury.config.network import DynamicNodeConfig, WiredNodeConfig, WirelessNodeConfig
from mercury.logger import logger as logging, logging_overhead
from mercury.msg.network import NewNodeLocation
from mercury.msg.packet import AppPacket
from mercury.msg.packet.app_packet.srv_packet import SrvRelatedRequest
from mercury.utils.amf import AccessManagementFunction
from mercury.utils.maths import euclidean_distance
from xdevs.models import Port
from ..common import ExtendedAtomic


class GatewaysLite(ExtendedAtomic):

    LOGGING_OVERHEAD = '        '

    def __init__(self, gws_config: GatewaysConfig, edge_fed_config: EdgeFederationConfig, amf: AccessManagementFunction):
        """
        Simplified SDNC for interconnecting clients and Edge Data Centers.
        :param gws_config: Configuration of gateways in the scenario.
        :param edge_fed_config: Configuration of the edge computing federation in the scenario.
        :param amf:
        """
        super().__init__(GatewaysConfig.GATEWAYS_LITE)
        self.wired_gws: dict[str, tuple[float, ...]] = dict()
        self.wireless_gws: dict[str, tuple[float, ...]] = dict()
        self.default_servers: dict[str, str] = dict()
        for gw_id, gw_config in gws_config.gateways.items():
            if gw_config.wired:
                self.wired_gws[gw_id] = gw_config.location
            else:
                self.wireless_gws[gw_id] = gw_config.location
            best_server_id, best_distance = None, None
            for edc_id, edc_config in edge_fed_config.edcs_config.items():
                distance = euclidean_distance(gw_config.location, edc_config.location)
                if best_server_id is None or distance < best_distance:
                    best_server_id, best_distance = edc_id, distance
            if best_server_id is None:
                best_server_id = edge_fed_config.cloud_id
            assert best_server_id is not None
            self.default_servers[gw_id] = best_server_id
        self.amf: AccessManagementFunction = amf

        self.clients: dict[str, DynamicNodeConfig] = dict()
        # self.designated_gws: dict[str, str] = dict()
        self.input_create_client = Port(DynamicNodeConfig, 'input_create_client')
        self.input_new_location = Port(NewNodeLocation, 'input_new_location')
        self.input_remove_client = Port(str, 'input_remove_client')
        self.input_data = Port(AppPacket, 'input_data')
        self.output_data = Port(AppPacket, 'output_data')
        self.add_in_port(self.input_create_client)
        self.add_in_port(self.input_new_location)
        self.add_in_port(self.input_remove_client)
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_data)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        for client_id in self.input_remove_client.values:
            gateway_id = self.amf.get_client_gateway(client_id)
            self.amf.disconnect_client(client_id, gateway_id)
            self.clients.pop(client_id)
            logging.info(f'{overhead}GatewaysLite: client {client_id} disconnected from gateway {gateway_id} and removed')

        for node_config in self.input_create_client.values:
            self.clients[node_config.node_id] = node_config
            if isinstance(node_config, WiredNodeConfig):
                gateway_id = node_config.gateway_id
            elif isinstance(node_config, WirelessNodeConfig):
                gateway_id = self.best_gw(node_config.location)
            else:
                raise TypeError(f'unknown data type for node_config ({type(node_config)})')
            self.amf.connect_client(node_config.node_id, gateway_id)
            logging.info(f'{overhead}GatewaysLite: client {node_config.node_id} created and connected to gateway {gateway_id}')

        for msg in self.input_new_location.values:
            node_config = self.clients.get(msg.node_id)
            if isinstance(node_config, WirelessNodeConfig):
                node_config.location = msg.location
                prev_gw = self.amf.get_client_gateway(msg.node_id)
                new_gw = self.best_gw(msg.location)
                if prev_gw != new_gw:
                    self.amf.handover_client(msg.node_id, prev_gw, new_gw)
                    logging.info(f'{overhead}GatewaysLite: client {node_config.node_id} moved from gateway {prev_gw} to {new_gw}')
        super().deltext_extension(e)

        for msg in self.input_data.values:
            if isinstance(msg, SrvRelatedRequest):
                gateway_id = self.amf.get_client_gateway(msg.client_id)
                msg.set_node_to(self.default_servers[gateway_id])
                self.add_msg_to_queue(self.output_data, msg)

        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def best_gw(self, client_location: tuple[float, ...]) -> str:
        return min(self.wireless_gws, key=lambda x: euclidean_distance(self.wireless_gws[x], client_location))
