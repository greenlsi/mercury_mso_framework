from collections import deque
from copy import deepcopy
from typing import Tuple, Dict, Union
from xdevs.models import INFINITY, Port

from .link import LinkConfiguration, Link, NetworkLinkReport, EnableChannels, ChannelShare
from .node import NodeConfiguration
from .channel_division import ChannelDivisionFactory

from ..common import Stateless
from ..common.packet.packet import PhysicalPacket
from .mobility import NodeLocation


class Receiver(Stateless):  # TODO hacerlo multinodo
    def __init__(self, name: str, node_id: str, max_hops: int = 0):
        super().__init__(name=name)
        self.node_id = node_id
        self.max_hops = max_hops

        self.input = Port(PhysicalPacket, "input")
        self.output_node = Port(PhysicalPacket, "output_node")
        self.output_transmitter = Port(PhysicalPacket, "output_transmitter")
        self.add_in_port(self.input)
        self.add_out_port(self.output_node)
        self.add_out_port(self.output_transmitter)

    def check_in_ports(self):
        for msg in self.input.values:
            if msg.node_to == self.node_id:  # Message to this node -> accept it
                self.add_msg_to_queue(self.output_node, msg)
            elif msg.node_to is None:  # Broadcast message -> accept copy and re-send message
                # forward broadcasted message
                self.forward_message(msg)
                msg_copy = deepcopy(msg)
                msg_copy.node_to = self.node_id
                msg_copy.data.node_to = self.node_id
                self.add_msg_to_queue(self.output_node, msg)
            else:  # Message to other node -> forward it
                self.forward_message(msg)

    def forward_message(self, msg: PhysicalPacket):
        if msg.n_hops < self.max_hops:
            msg.bandwidth = 0
            msg.frequency = 0
            msg.mcs = None
            msg.power = None
            msg.noise = None
            msg.n_hops += 1
            self.add_msg_to_queue(self.output_transmitter, msg)

    def process_internal_messages(self):
        pass


class Network(Stateless):
    def __init__(self, name: str, nodes: Dict[str, NodeConfiguration], default_link: LinkConfiguration,
                 topology: Dict[str, Dict[str, Dict[str, Union[LinkConfiguration, None]]]]):
        """
        Network model for Mercury. It is defined as a directed graph
        :param name: name of the xDEVS atomic model
        :param nodes: dictionary containing the ID of every node in the network and their configuration.
        :param default_link: Default link configuration in case a given link in the topology is None
        :param topology: directed graph representing the network {node_from: {node_to: link_configuration}}
        """
        super().__init__(name=name)

        self.input_node_location = Port(NodeLocation, 'input_new_location')
        self.input_data = Port(PhysicalPacket, 'input_data')
        self.output_link_report = Port(NetworkLinkReport, 'output_link_report')
        self.add_in_port(self.input_node_location)
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_link_report)

        self.links = dict()  # It contains the links of the network
        self.tx_overheads = dict()  # It contains the transmission overhead of each link
        self.buffers = dict()  # it contains the buffers of each transmitter
        self.outputs_node_to = dict()  # it contains all the output ports
        for node_from, links in topology.items():
            self.links[node_from] = dict()
            self.tx_overheads[node_from] = dict()
            self.buffers[node_from] = dict()
            for node_to, link_config in links.items():
                if node_to not in self.outputs_node_to:
                    self.outputs_node_to[node_to] = Port(PhysicalPacket, 'output_' + node_to)
                    self.add_out_port(self.outputs_node_to[node_to])
                conf = link_config if link_config is not None else default_link
                self.links[node_from][node_to] = Link(nodes[node_from], nodes[node_to], conf)
                self.tx_overheads[node_from][node_to] = 0
                self.buffers[node_from][node_to] = deque()

    def clear_state(self):
        for buffers in self.buffers.values():
            for buffer in buffers.values():
                while buffer and buffer[0][0] <= self._clock:
                    buffer.popleft()

    def check_in_ports(self):
        for msg in self.input_node_location.values:
            self.process_new_location(msg.node_id, msg.location)
        self.check_extra_ports()
        for msg in self.input_data.values:
            self.process_incoming_message(msg)

    def process_new_location(self, node_id: str, new_location: Tuple[float, ...]):
        # Modify links from node
        links = self.links.get(node_id, None)
        if links is not None:
            for link in links.values():
                link.set_new_location(node_id, new_location)
        # Modify links to node
        for links in self.links.values():
            link = links.get(node_id, None)
            if link is not None:
                link.set_new_location(node_id, new_location)

    def check_extra_ports(self):
        pass

    def process_incoming_message(self, msg: PhysicalPacket):
        node_from = msg.node_from
        node_to = msg.node_to
        if node_to is None:
            self.broadcast_message(node_from, msg)
        else:
            self.send_msg(node_from, node_to, msg)

    def broadcast_message(self, node_from: str, msg: PhysicalPacket):
        for node_to in self.links[node_from]:
            msg_copy = deepcopy(msg)
            self.send_msg(node_from, node_to, msg_copy)

    def send_msg(self, node_from: str, node_to: str, msg: PhysicalPacket):
        if node_to not in self.links[node_from]:
            raise NotImplementedError("Network re-routing is not implemented yet")
        self.send_message_through_link(node_from, node_to, msg)

    def send_message_through_link(self, node_from: str, node_to: str, msg: PhysicalPacket):
        link = self.links[node_from][node_to]
        new = not link.hit

        msg.header = link.header
        msg.frequency = link.frequency
        msg.bandwidth = link.bandwidth
        msg.power = link.power
        msg.noise = link.noise
        msg.mcs = link.mcs

        tx_overhead = max(self._clock, self.tx_overheads[node_from][node_to])
        tx_sigma = 0 if link.tx_speed == 0 else msg.size / link.tx_speed
        prop_sigma = link.prop_delay

        self.buffers[node_from][node_to].append((tx_overhead + tx_sigma + prop_sigma, msg))
        self.tx_overheads[node_from][node_to] = tx_overhead + tx_sigma

        if new:
            link_report = NetworkLinkReport(node_from, node_to, link.bandwidth, link.frequency,
                                            link.power, link.noise, link.mcs)
            self.add_msg_to_queue(self.output_link_report, link_report)

    def process_internal_messages(self):
        clock = self._clock
        # clock = self._clock + self.sigma  TODO cambiar esto
        for buffers in self.buffers.values():
            for node_to, buffer in buffers.items():
                for time, msg in buffer:
                    if time > clock:
                        continue
                    self.outputs_node_to[node_to].add(msg)  # Inject messages which sending time matches with the clock

    def get_next_timeout(self):
        if not self.msg_queue_empty():
            return 0
        ta = INFINITY
        for buffers in self.buffers.values():
            ta = min(ta, min([buffer[0][0] - self._clock for buffer in buffers.values() if buffer], default=INFINITY))
        return ta


class SharedNetwork(Network):
    def __init__(self, name: str, master_nodes: Dict[str, NodeConfiguration], slave_nodes: Dict[str, NodeConfiguration],
                 default_link: LinkConfiguration, topology: Dict[str, Dict[str, Dict[str, None]]]):

        super().__init__(name, {**master_nodes, **slave_nodes}, default_link, topology)

        self.shares = dict()
        for master_node in master_nodes:
            self.shares[master_node] = dict()
            for slave_node in slave_nodes:
                if slave_node in self.links and master_node in self.links[slave_node]:
                    self.links[slave_node][master_node].set_link_share(0)


class MasterNetwork(SharedNetwork):

    channel_div_factory = ChannelDivisionFactory()

    def __init__(self, name: str, master_nodes: Dict[str, NodeConfiguration], slave_nodes: Dict[str, NodeConfiguration],
                 default_link: LinkConfiguration, topology: Dict[str, Dict[str, Dict[str, None]]],
                 channel_div_name: str = None, channel_div_config: Dict = None):

        for node_from, links in topology.items():
            assert node_from in master_nodes
            for node_to in links:
                assert node_to in slave_nodes

        super().__init__(name, master_nodes, slave_nodes, default_link, topology)

        # the one in charge of divinding the spectrum (APs)
        self.channel_div = None
        if channel_div_name is None:
            channel_div_name = 'equal'
        if channel_div_config is None:
            channel_div_config = dict()
        self.channel_div = self.channel_div_factory.create_division(channel_div_name, **channel_div_config)

        self.input_enable_channels = Port(EnableChannels, 'input_enable_channels')
        self.output_channel_share = Port(ChannelShare, 'output_channel_share')
        self.add_in_port(self.input_enable_channels)
        self.add_out_port(self.output_channel_share)

    def check_extra_ports(self):
        for msg in self.input_enable_channels.values:
            node_from = msg.node_from
            enabled_nodes_to = msg.nodes_to

            mcs = {node_to: self.links[node_from][node_to].mcs for node_to in enabled_nodes_to}
            if self.channel_div is None:
                new_share = {node_to: 1 for node_to in mcs}
            else:
                new_share = self.channel_div.bandwidth_share(mcs)

            disconnected = [node_id for node_id in self.links[node_from] if node_id not in new_share]

            for node_to in disconnected:
                link = self.links[node_from][node_to]
                link.set_link_share(0)
                # self.add_msg_to_queue(self.output_channel_share, ChannelShare(node_from, node_to, 0))
                link_report = NetworkLinkReport(node_from, node_to, 0, 0, None, None, ("disconnected", 0))
                self.add_msg_to_queue(self.output_link_report, link_report)

            for node_to, share in new_share.items():
                link = self.links[node_from][node_to]
                hit = node_to in self.shares[node_from]
                link.set_link_share(share)
                if hit or not link.hit:
                    link_report = NetworkLinkReport(node_from, node_to, link.bandwidth, link.frequency, link.power,
                                                    link.noise, link.mcs)
                    self.add_msg_to_queue(self.output_link_report, link_report)

            self.shares[node_from] = new_share
            nodes = {node_to: share for node_to, share in self.shares[node_from].items()}
            self.add_msg_to_queue(self.output_channel_share, ChannelShare(node_from, nodes))

    def send_msg(self, node_from: str, node_to: str, msg: PhysicalPacket):
        if node_to not in self.links[node_from]:
            raise NotImplementedError("Network re-routing is not implemented yet")
        if node_to in self.shares[node_from]:
        # if self.shares[node_from][node_to] > 0:
            self.send_message_through_link(node_from, node_to, msg)
        else:
            raise ValueError  # TODO check this


class SlaveNetwork(SharedNetwork):
    def __init__(self, name: str, master_nodes: Dict[str, NodeConfiguration], slave_nodes: Dict[str, NodeConfiguration],
                 default_link: LinkConfiguration, topology: Dict[str, Dict[str, Dict[str, None]]]):

        for node_from, links in topology.items():
            assert node_from in slave_nodes
            for node_to in links:
                assert node_to in master_nodes

        super().__init__(name, master_nodes, slave_nodes, default_link, topology)

        self.input_channel_share = Port(ChannelShare, 'input_channel_share')
        self.add_in_port(self.input_channel_share)

    def check_extra_ports(self):
        for msg in self.input_channel_share.values:
            master_node = msg.master_node
            new_shares = msg.slave_nodes

            disconnected = [node for node in self.shares[master_node] if node not in new_shares]
            for slave_node in disconnected:
                self.links[slave_node][master_node].set_link_share(0)
                # self.add_msg_to_queue(self.output_channel_share, ChannelShare(node_from, node_to, 0))
                link_report = NetworkLinkReport(slave_node, master_node, 0, 0, None, None, ("disconnected", 0))
                self.add_msg_to_queue(self.output_link_report, link_report)

            for slave_node, share in new_shares.items():
                link = self.links[slave_node][master_node]
                hit = slave_node in self.shares[master_node]
                link.set_link_share(share)
                if hit or not link.hit:
                    link_report = NetworkLinkReport(slave_node, master_node, link.bandwidth, link.frequency, link.power,
                                                    link.noise, link.mcs)
                    self.add_msg_to_queue(self.output_link_report, link_report)

            self.shares[master_node] = {slave: share for slave, share in new_shares.items()}

    def send_msg(self, node_from: str, node_to: str, msg: PhysicalPacket):
        if node_to not in self.links[node_from]:
            raise NotImplementedError("Network re-routing is not implemented yet")
        if node_from in self.shares[node_to]:
        # if self.shares[node_from][node_to] > 0:
            self.send_message_through_link(node_from, node_to, msg)
        else:
            raise ValueError  # TODO check this
