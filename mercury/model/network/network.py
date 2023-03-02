from __future__ import annotations
from abc import ABC
from collections import deque
from copy import deepcopy
from math import inf
from mercury.config.network import LinkConfig, TransceiverConfig, NetworkNodeConfig, StaticNodeConfig, \
    DynamicNodeConfig, WiredNodeConfig, WirelessNodeConfig, NetworkConfig, AccessNetworkConfig
from mercury.config.transducers import TransducersConfig
from mercury.msg.client import SendPSS
from mercury.msg.packet import PhysicalPacket
from mercury.msg.network import NetworkLinkReport, NewNodeLocation, ChannelShare
from mercury.utils.link import Link
from xdevs.models import Port, PHASE_PASSIVE
from ..common import ExtendedAtomic


class LinkStructure:
    def __init__(self, node_from: NetworkNodeConfig, node_to: NetworkNodeConfig,
                 link_config: LinkConfig, share: float = 1, t_init: float = 0):
        self.link: Link = Link(node_from, node_to, link_config)
        self.link.set_link_share(share)
        self.tx_overhead: float = t_init
        self.buffer: deque[tuple[float, PhysicalPacket]] = deque()


class AbstractNetwork(ExtendedAtomic, ABC):
    def __init__(self, net_config: NetworkConfig):
        super().__init__(name=f'network_{net_config.network_id}')
        self.net_config = net_config
        nodes = self.net_config.nodes

        self.input_data: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_data')
        self.output_link_report = Port(NetworkLinkReport, 'output_link_report')
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_link_report)
        self.outputs_data: dict[str, Port[PhysicalPacket]] = dict()
        for node_id in nodes:
            self.outputs_data[node_id] = Port(PhysicalPacket, f'output_{node_id}')
            self.add_out_port(self.outputs_data[node_id])

        self.links: dict[str, dict[str, LinkStructure]] = dict()
        for node in nodes:
            self.links[node] = dict()
        for node_from, links in self.net_config.links.items():
            for node_to, link_config in links.items():
                link_struct = LinkStructure(nodes[node_from], nodes[node_to], link_config)
                self.links[node_from][node_to] = link_struct

    def deltint_extension(self):
        for links in self.links.values():
            for link in links.values():
                while link.buffer and link.buffer[0][0] <= self._clock:
                    _, msg = link.buffer.popleft()
                    self.add_msg_to_queue(self.get_msg_port(msg), msg)
        self.hold_in(PHASE_PASSIVE, self.next_timeout())

    def deltext_extension(self, e: float):
        for msg in self.input_data.values:
            self.process_incoming_message(msg)
        self.hold_in(PHASE_PASSIVE, self.next_timeout())

    def lambdaf_extension(self):
        pass

    def initialize(self):
        if TransducersConfig.LOG_NET:
            for links in self.links.values():
                for link in links.values():
                    self.add_msg_to_queue(self.output_link_report, link.link.generate_report())
        self.hold_in(PHASE_PASSIVE, self.next_timeout())

    def exit(self):
        pass

    def get_msg_port(self, data: PhysicalPacket) -> Port[PhysicalPacket]:
        return self.outputs_data[data.node_to]

    def process_incoming_message(self, msg: PhysicalPacket):
        node_from = msg.node_from
        node_to = msg.node_to
        self.broadcast_message(node_from, msg) if node_to is None else self.send_msg(node_from, node_to, msg)

    def broadcast_message(self, node_from: str, msg: PhysicalPacket):
        for node_to in self.links[node_from]:
            msg_copy = deepcopy(msg)
            msg_copy.node_to = node_to
            self.send_msg(node_from, node_to, msg_copy)

    def send_msg(self, node_from: str, node_to: str, msg: PhysicalPacket):
        if node_to not in self.links[node_from]:
            raise NotImplementedError("Network re-routing is not implemented yet")
        self.send_message_through_link(self.links[node_from][node_to], msg)

    def send_message_through_link(self, link_struct: LinkStructure, msg: PhysicalPacket):
        new = not link_struct.link.hit
        link_struct.link.prepare_msg(msg)
        tx_overhead = max(self._clock, link_struct.tx_overhead)
        tx_sigma = 0 if link_struct.link.tx_speed == 0 else msg.size / link_struct.link.tx_speed
        prop_sigma = link_struct.link.prop_delay
        link_struct.buffer.append((tx_overhead + tx_sigma + prop_sigma, msg))
        link_struct.tx_overhead = tx_overhead + tx_sigma
        if TransducersConfig.LOG_NET and new:  # TODO quitarlo de aqui
            self.add_msg_to_queue(self.output_link_report, link_struct.link.generate_report())

    def next_timeout(self):
        if not self.msg_queue_empty():
            return 0
        ta = inf
        for links in self.links.values():
            ta = min(ta, min((link.buffer[0][0] - self._clock for link in links.values() if link.buffer), default=inf))
        return ta


class AbstractAccessNetwork(AbstractNetwork, ABC):
    def __init__(self, log_links: bool, net_config: NetworkConfig, default_dl_trx: TransceiverConfig,
                 default_ul_trx: TransceiverConfig, default_dl_link: LinkConfig, default_ul_link: LinkConfig):
        self.log_links = log_links
        super().__init__(net_config)
        self.default_dl_trx: TransceiverConfig = default_dl_trx
        self.default_ul_trx: TransceiverConfig = default_ul_trx
        self.default_dl_link: LinkConfig = default_dl_link
        self.default_ul_link: LinkConfig = default_ul_link
        self.dynamic_nodes: dict[str, DynamicNodeConfig] = dict()

        self.input_create_client: Port[DynamicNodeConfig] = Port(DynamicNodeConfig, 'input_create_client')
        self.input_remove_client: Port[str] = Port(str, 'input_remove_client')
        self.output_clients: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_clients')
        self.add_in_port(self.input_create_client)
        self.add_in_port(self.input_remove_client)
        self.add_out_port(self.output_clients)

    def deltext_extension(self, e: float):
        for node_config in self.input_create_client.values:
            self.create_node(node_config)
        self.check_additional_ports()
        super().deltext_extension(e)
        for node_id in self.input_remove_client.values:
            self.remove_node(node_id)
        self.hold_in(PHASE_PASSIVE, self.next_timeout())

    def get_msg_port(self, data: PhysicalPacket) -> Port[PhysicalPacket]:
        return self.outputs_data.get(data.node_to, self.output_clients)

    def remove_node(self, node_id: str):
        self.dynamic_nodes.pop(node_id, None)
        links = self.links.pop(node_id, None)
        if links is not None:
            for node_from in links:
                self.links[node_from].pop(node_id)
                self.remove_links(node_id, node_from)

    def create_node(self, node_config: DynamicNodeConfig):
        self.dynamic_nodes[node_config.node_id] = node_config
        self.links[node_config.node_id] = dict()

    def check_additional_ports(self):
        pass

    def create_links(self, gateway: StaticNodeConfig, node: DynamicNodeConfig,
                     dl_link_config: LinkConfig, ul_link_config: LinkConfig, share: float):
        link_dl = LinkStructure(gateway, node, dl_link_config, share, self._clock)
        link_ul = LinkStructure(node, gateway, ul_link_config, share, self._clock)
        self.links[gateway.node_id][node.node_id] = link_dl
        self.links[node.node_id][gateway.node_id] = link_ul
        if self.log_links and TransducersConfig.LOG_NET:
            self.add_msg_to_queue(self.output_link_report, link_dl.link.generate_report())
            self.add_msg_to_queue(self.output_link_report, link_ul.link.generate_report())

    def remove_links(self, client: str, gateway: str, log: bool = False):
        if (self.log_links or log) and TransducersConfig.LOG_NET:
            self.add_msg_to_queue(self.output_link_report, NetworkLinkReport(client, gateway, 0, 0, None, None, None))
            self.add_msg_to_queue(self.output_link_report, NetworkLinkReport(gateway, client, 0, 0, None, None, None))


class WiredAccessNetwork(AbstractAccessNetwork):
    def __init__(self, net_config: AccessNetworkConfig):
        super().__init__(True, net_config.wired_config, net_config.wired_dl_trx,
                         net_config.wired_ul_trx, net_config.wired_dl_link, net_config.wired_ul_link)

    def create_node(self, node_config: DynamicNodeConfig):
        if isinstance(node_config, WiredNodeConfig):
            if node_config.trx is None:
                node_config.trx = self.default_ul_trx
            if node_config.dl_link_config is None:
                node_config.dl_link_config = self.default_dl_link
            if node_config.ul_link_config is None:
                node_config.ul_link_config = self.default_ul_link
            super().create_node(node_config)
            gateway = self.net_config.nodes[node_config.gateway_id]
            self.create_links(gateway, node_config, node_config.dl_link_config, node_config.ul_link_config, 1)


class WirelessAccessNetwork(AbstractAccessNetwork):
    def __init__(self, net_config: AccessNetworkConfig, control: bool):
        super().__init__(False, net_config.wireless_config, net_config.wireless_dl_trx,
                         net_config.wireless_ul_trx, net_config.wireless_dl_link, net_config.wireless_ul_link)
        self.control = control
        self.input_new_location: Port[NewNodeLocation] = Port(NewNodeLocation, 'input_new_location')
        self.add_in_port(self.input_new_location)
        if self.control:
            self.input_send_pss: Port[SendPSS] = Port(SendPSS, 'input_send_pss')
            self.add_in_port(self.input_send_pss)
            self.outputs_send_pss: dict[str, Port[str]] = dict()
            for gateway_id in self.net_config.nodes:
                self.outputs_send_pss[gateway_id] = Port(str, f'output_{gateway_id}_repeat_pss')
                self.add_out_port(self.outputs_send_pss[gateway_id])
        else:
            self.channel_div = net_config.wireless_div
            self.channel_share: dict[str, list[str]] = {gateway_id: list() for gateway_id in self.net_config.nodes}
            self.input_share: Port[ChannelShare] = Port(ChannelShare, 'input_share')
            self.add_in_port(self.input_share)

    def create_node(self, node_config: DynamicNodeConfig):
        if isinstance(node_config, WirelessNodeConfig):
            super().create_node(node_config)
            if self.control:
                if node_config.trx is None:
                    node_config.trx = self.default_ul_trx
                for gateway in self.net_config.nodes.values():
                    self.create_links(gateway, node_config, self.default_dl_link, self.default_ul_link, 1)

    def check_additional_ports(self):
        new_share: set[str] = set()
        for msg in self.input_new_location.values:
            self.process_new_location(msg.node_id, msg.location, new_share)
        if self.control:
            for pss in self.input_send_pss.values:
                self.filter_pss(pss.client_id, pss.best_gw)
        else:
            for msg in self.input_share.values:
                new_share.add(msg.master_node)
                self.channel_share[msg.master_node] = msg.slave_nodes
            for gateway_id in new_share:
                self.process_new_share(gateway_id, self.channel_share[gateway_id])

    def process_new_location(self, node_id: str, new_location: tuple[float, ...], share: set[str]):
        node_config = self.dynamic_nodes.get(node_id)
        if node_config is not None:
            node_config.location = new_location
            for gateway, link_struct in self.links[node_id].items():
                ul_link = link_struct.link
                dl_link = self.links[gateway][node_id].link
                ul_link.set_new_location(node_id, new_location)
                dl_link.set_new_location(node_id, new_location)
                if not self.control and TransducersConfig.LOG_NET:
                    if not ul_link.hit or not dl_link.hit:
                        share.add(gateway)
                        self.add_msg_to_queue(self.output_link_report, ul_link.generate_report())
                        self.add_msg_to_queue(self.output_link_report, dl_link.generate_report())

    def filter_pss(self, node_id: str, current_gw: str | None):
        if node_id in self.dynamic_nodes:
            best_gateway = max(self.net_config.nodes, key=lambda gw: self.links[gw][node_id].link.natural_snr)
            if current_gw is None:
                self.add_msg_to_queue(self.outputs_send_pss[best_gateway], node_id)
            elif best_gateway != current_gw:
                self.add_msg_to_queue(self.outputs_send_pss[current_gw], node_id)
                self.add_msg_to_queue(self.outputs_send_pss[best_gateway], node_id)

    def process_new_share(self, gateway: str, clients: list[str]):
        for client in [client for client in self.links[gateway] if client not in clients]:  # Remove links
            self.links[gateway].pop(client)
            self.links[client].pop(gateway)
            self.remove_links(client, gateway, True)
        for client in [client for client in clients if client not in self.links[gateway]]:  # Create new links
            gateway_config = self.net_config.nodes[gateway]
            client_config = self.dynamic_nodes[client]
            if client_config.trx is None:
                client_config.trx = self.default_ul_trx
            self.create_links(gateway_config, client_config, self.default_dl_link, self.default_ul_link, 0)
        # third we check if share changed
        eff = {client: self.links[gateway][client].link.efficiency for client in clients}
        if self.channel_div is None:
            new_share = {node_to: 1 for node_to in eff}
        else:
            new_share = self.channel_div.bandwidth_share(eff)
        for client, share in new_share.items():
            dl_link = self.links[gateway][client].link
            ul_link = self.links[client][gateway].link
            dl_link.set_link_share(share)
            ul_link.set_link_share(share)
            if TransducersConfig.LOG_NET:
                if not dl_link.hit:
                    self.add_msg_to_queue(self.output_link_report, dl_link.generate_report())
                if not ul_link.hit:
                    self.add_msg_to_queue(self.output_link_report, ul_link.generate_report())
