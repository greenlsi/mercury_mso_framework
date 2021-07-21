from mercury.logger import logger as logging, logging_overhead
from abc import ABC
from collections import deque
from copy import deepcopy
from typing import Tuple, Dict, Optional
from xdevs.models import INFINITY, Port, PHASE_PASSIVE
from mercury.plugin import AbstractFactory
from mercury.config.network import NodeConfig, LinkConfig
from mercury.msg.network import PhysicalPacket, NetworkLinkReport, EnableChannels, ChannelShare, NodeLocation
from .link import Link
from ..common import ExtendedAtomic


class DynamicNodesMobility(ExtendedAtomic):

    LOGGING_OVERHEAD = ""

    def __init__(self, nodes_config: Optional[Dict[str, NodeConfig]] = None):
        """
        :param nodes_config: Initial Dynamic nodes configuration
        """
        if nodes_config is None:
            nodes_config = dict()
        self.nodes_mobility = {node_id: node_config.node_mobility for node_id, node_config in nodes_config.items()}

        self.nodes_next_change = dict()
        for node_id, mobility in self.nodes_mobility.items():
            self.nodes_next_change[node_id] = mobility.next_t

        super().__init__(name='dynamic_nodes_mobility')

        self.input_remove_node = Port(str, 'input_remove_node')
        self.input_create_node = Port(NodeConfig, 'input_create_node')
        self.output_node_location = Port(NodeLocation, 'output_node_location')

        self.add_in_port(self.input_create_node)
        self.add_in_port(self.input_remove_node)
        self.add_out_port(self.output_node_location)

    def deltint_extension(self):
        for node_id in self.nodes_next_change:
            if self.nodes_next_change[node_id] <= self._clock:
                self.nodes_mobility[node_id].advance()
                self.nodes_next_change[node_id] = self.nodes_mobility[node_id].next_t
        self.hold_in(PHASE_PASSIVE, self.get_next_timeout())

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        # Remove dynamic nodes
        for node_id in self.input_remove_node.values:
            logging.info(f"{overhead}Node {node_id} removed")
            self.nodes_next_change.pop(node_id, None)
            self.nodes_mobility.pop(node_id, None)
        # Create dynamic nodes
        for node_config in self.input_create_node.values:
            node_id = node_config.node_id
            node_mobility = node_config.node_mobility
            if node_mobility.next_t != self._clock:
                logging.error(f"{overhead}time coherence error detected with node {node_id} ({node_mobility.next_t})")
                raise AssertionError('time coherence error: new node was not created when required')
            logging.info(f"{overhead}Node {node_id} created (initial location: {node_mobility.location})")
            self.nodes_mobility[node_id] = node_mobility
            self.nodes_mobility[node_id].advance()
            self.nodes_next_change[node_id] = node_mobility.next_t

        self.hold_in(PHASE_PASSIVE, self.get_next_timeout())

    def lambdaf_extension(self):
        clock = self._clock + self.sigma
        overhead = logging_overhead(clock, self.LOGGING_OVERHEAD)
        for node_id in self.nodes_next_change:
            if self.nodes_next_change[node_id] <= clock:
                location = self.nodes_mobility[node_id].location
                logging.info(f"{overhead}{node_id} moved to location {location}")
                self.output_node_location.add(NodeLocation(node_id, location))

    def initialize(self):
        self.hold_in(PHASE_PASSIVE, self.get_next_timeout())

    def exit(self):
        pass

    def get_next_event(self, t):
        return min([next_change - t for next_change in self.nodes_next_change.values()], default=INFINITY)

    def get_next_timeout(self):
        return self.get_next_event(self._clock) if self.msg_queue_empty() else 0


class Network(ExtendedAtomic):
    def __init__(self, nodes: Dict[str, NodeConfig], default_link: LinkConfig,
                 fixed_topology: Optional[Dict[str, Dict[str, Dict[str, Optional[LinkConfig]]]]] = None,
                 dyn_node_type: str = NodeConfig.TRANSCEIVER, name: Optional[str] = None):
        """
        Network model for Mercury. It is defined as a directed graph with fixed nodes.
        In runtime, dynamic nodes may be created and removed. Dynamic nodes cannot communicated between each other.
        They can only use fixed nodes to transmit/receive messages.

        :param nodes: dictionary containing the ID of every fixed node in the network and their configuration.
               Fixed nodes are created at the beginning, and they are never removed. They do not move either.
        :param default_link: Dynamic link configuration.
               In case a given link in the fixed topology is None, this link configuration is used as default.
        :param fixed_topology: directed graph representing the fixed network {node_from: {node_to: link_configuration}}
               If the link configuration is None, the dynamic link configuration is used by default.
        :param dyn_node_type: If 'tx', dynamic nodes are transmitters. If 'trx', dynamic nodes are transceivers.
               If 'rx', dynamic nodes are receivers. By default, dynamic nodes are transceivers.
        :param name: name of the xDEVS atomic model.
        """
        assert dyn_node_type in [NodeConfig.TRANSMITTER, NodeConfig.TRANSCEIVER, NodeConfig.RECEIVER]
        if fixed_topology is None:
            fixed_topology = dict()

        self.default_link = default_link
        self.dyn_nodes_type = dyn_node_type
        self.nodes = nodes

        super().__init__(name=name)

        self.input_remove_node = Port(str, 'input_remove_node')
        self.input_new_location = Port(NodeLocation, 'input_new_location')
        self.input_create_node = Port(NodeConfig, 'input_create_node')
        self.input_data = Port(PhysicalPacket, 'input_data')
        self.output_data = Port(PhysicalPacket, 'output_data')
        self.output_link_report = Port(NetworkLinkReport, 'output_link_report')
        self.add_in_port(self.input_remove_node)
        self.add_in_port(self.input_new_location)
        self.add_in_port(self.input_create_node)
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_data)
        self.add_out_port(self.output_link_report)

        self.links = dict()         # It contains the links of the network
        self.tx_overheads = dict()  # It contains the transmission overhead of each link
        self.buffers = dict()       # it contains the buffers of each transmitter

        for node in self.nodes:
            self.links[node] = dict()
            self.tx_overheads[node] = dict()
            self.buffers[node] = dict()

        for node_from, links in fixed_topology.items():
            for node_to, link_config in links.items():
                conf = link_config if link_config is not None else default_link
                self.links[node_from][node_to] = Link(nodes[node_from], nodes[node_to], conf)
                self.tx_overheads[node_from][node_to] = 0
                self.buffers[node_from][node_to] = deque()

    def deltint_extension(self):
        for buffers in self.buffers.values():
            for buffer in buffers.values():
                while buffer and buffer[0][0] <= self._clock:
                    buffer.popleft()
        self.hold_in(PHASE_PASSIVE, self.get_next_timeout())

    def deltext_extension(self, e):
        for node_id in self.input_remove_node.values:
            self.remove_node(node_id)
        for node_config in self.input_create_node.values:
            self.create_node(node_config)
        for msg in self.input_new_location.values:
            self.process_new_location(msg.node_id, msg.location)
        self.check_extra_ports()
        for msg in self.input_data.values:
            self.process_incoming_message(msg)
        self.hold_in(PHASE_PASSIVE, self.get_next_timeout())

    def lambdaf_extension(self):
        clock = self._clock + self.sigma
        for buffers in self.buffers.values():
            for node_to, buffer in buffers.items():
                for time, msg in buffer:
                    if time > clock:
                        continue
                    self.output_data.add(msg)

    def remove_node(self, node_id: str):
        if self.dyn_nodes_type != NodeConfig.RECEIVER:      # If node is not a receiver, remove links from node
            if self.links.pop(node_id, None) is not None:
                self.tx_overheads.pop(node_id)
                self.buffers.pop(node_id)
        if self.dyn_nodes_type != NodeConfig.TRANSMITTER:   # If node is not a transmitter, remove links to node
            for node_from, links in self.links.items():
                if links.pop(node_id, None) is not None:
                    self.tx_overheads[node_from].pop(node_id)
                    self.buffers[node_from].pop(node_id)

    def create_node(self, node_config: NodeConfig):
        node_id = node_config.node_id

        if self.dyn_nodes_type != NodeConfig.RECEIVER:      # If node is not a receiver, create links from node
            self.links[node_id] = dict()
            self.tx_overheads[node_id] = dict()
            self.buffers[node_id] = dict()
            for node_to in self.nodes:
                self.links[node_id][node_to] = Link(node_config, self.nodes[node_to], self.default_link)
                self.set_initial_link_share(self.links[node_id][node_to])
                self.tx_overheads[node_id][node_to] = 0
                self.buffers[node_id][node_to] = deque()

        if self.dyn_nodes_type != NodeConfig.TRANSMITTER:   # If node is not a transmitter, create links to node
            for node_from in self.nodes:
                self.links[node_from][node_id] = Link(self.nodes[node_from], node_config, self.default_link)
                self.set_initial_link_share(self.links[node_from][node_id])
                self.tx_overheads[node_from][node_id] = 0
                self.buffers[node_from][node_id] = deque()

    def process_new_location(self, node_id: str, new_location: Tuple[float, ...]):
        for node_from, links in self.links.items():
            if node_id == node_from:
                for link in links.values():
                    link.set_new_location(node_id, new_location)
            elif node_id in links:
                links[node_id].set_new_location(node_id, new_location)

    def check_extra_ports(self):
        pass

    def process_incoming_message(self, msg: PhysicalPacket):
        node_from = msg.node_from
        node_to = msg.node_to
        if node_to is None:
            self.broadcast_message(node_from, msg)
        else:
            self.send_msg(node_from, node_to, msg)

    @staticmethod
    def set_initial_link_share(link: Link):  # This is only used in shared networks
        pass

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

    def get_next_timeout(self):
        if not self.msg_queue_empty():
            return 0
        ta = INFINITY
        for buffers in self.buffers.values():
            ta = min(ta, min([buffer[0][0] - self._clock for buffer in buffers.values() if buffer], default=INFINITY))
        return ta

    def initialize(self):
        self.passivate()

    def exit(self):
        pass


class SharedNetwork(Network, ABC):
    def __init__(self, nodes: Dict[str, NodeConfig], default_link: LinkConfig, dyn_node_type: str, name: str = None):
        """
        Medium-shared network model. In this networks, each link only gets a portion of the total available resources.
        Medium-shared networks are unidirectional: either from fixed to dynamic nodes or the other way around

        :param nodes: Configuration of fixed nodes.
        :param default_link: Default link configuration.
        :param dyn_node_type: Dynamic node type (either transmitter or receiver).
        :param name: xDEVS model name.
        """
        super().__init__(nodes, default_link, dyn_node_type=dyn_node_type, name=name)
        self.shares = {node: set() for node in self.nodes}

    @staticmethod
    def set_initial_link_share(link: Link):  # In shared networks, the initial share is set to 0 (i.e., no resources)
        link.set_link_share(0)


class MasterNetwork(SharedNetwork):
    def __init__(self, fixed_nodes: Dict[str, NodeConfig], default_link: LinkConfig, channel_div_name: str = 'equal',
                 channel_div_config: Optional[Dict] = None, name: Optional[str] = None):
        """
        Master Medium-Shared Network model. This network is in charge of sharing link resources.
        :param fixed_nodes: Configuration of fixed nodes.
        :param default_link: Default link configuration.
        :param channel_div_name: Channel division strategy name (by default, it is set to equal).
        :param channel_div_config: Any additional parameter for configuring the channel division strategy.
        :param name: xDEVS model name
        """
        super().__init__(fixed_nodes, default_link, NodeConfig.RECEIVER, name)  # Dynamic nodes are only receivers

        if channel_div_config is None:
            channel_div_config = dict()
        self.channel_div = AbstractFactory.create_network_channel_division(channel_div_name, **channel_div_config)

        self.input_enable_channels = Port(EnableChannels, 'input_enable_channels')
        self.output_channel_share = Port(ChannelShare, 'output_channel_share')
        self.add_in_port(self.input_enable_channels)
        self.add_out_port(self.output_channel_share)

    def check_extra_ports(self):
        super().check_extra_ports()
        for msg in self.input_enable_channels.values:
            node_from = msg.master_node
            enabled_nodes_to = msg.slave_nodes

            mcs = {node_to: self.links[node_from][node_to].mcs for node_to in enabled_nodes_to}
            if self.channel_div is None:
                new_share = {node_to: 1 for node_to in mcs}
            else:
                new_share = self.channel_div.bandwidth_share(mcs)

            disconnected = [node_id for node_id in self.links[node_from] if node_id not in new_share]

            for node_to in disconnected:
                link = self.links[node_from][node_to]
                link.set_link_share(0)
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
            self.send_message_through_link(node_from, node_to, msg)
        else:
            raise ValueError


class SlaveNetwork(SharedNetwork):

    def __init__(self, fixed_nodes: Dict[str, NodeConfig], default_link: LinkConfig, name: Optional[str] = None):
        """
        Slave Medium-Shared Network model. this network relies on a master network's channel division decision.
        :param fixed_nodes: Configuration of fixed nodes.
        :param default_link: Default link configuration.
        :param name: xDEVS model name
        """
        super().__init__(fixed_nodes, default_link, NodeConfig.TRANSMITTER, name)

        self.input_channel_share = Port(ChannelShare, 'input_channel_share')
        self.add_in_port(self.input_channel_share)

    def check_extra_ports(self):
        for msg in self.input_channel_share.values:
            master_node = msg.master_node
            new_shares = msg.slave_nodes

            disconnected = [node for node in self.shares[master_node] if node not in new_shares]
            for slave_node in disconnected:
                self.links[slave_node][master_node].set_link_share(0)
                link_report = NetworkLinkReport(slave_node, master_node, 0, 0, None, None, ("disconnected", 0))
                self.add_msg_to_queue(self.output_link_report, link_report)

            for slave_node, share in new_shares.items():
                link = self.links[slave_node][master_node]
                hit = slave_node in self.shares[master_node]
                link.set_link_share(share)
                if hit or not link.hit:
                    link_report = NetworkLinkReport(slave_node, master_node, link.bandwidth,
                                                    link.frequency, link.power, link.noise, link.mcs)
                    self.add_msg_to_queue(self.output_link_report, link_report)

            self.shares[master_node] = {slave: share for slave, share in new_shares.items()}

    def send_msg(self, node_from: str, node_to: str, msg: PhysicalPacket):
        if node_to not in self.links[node_from]:
            raise NotImplementedError("Network re-routing is not implemented yet")
        if node_from in self.shares[node_to]:
            self.send_message_through_link(node_from, node_to, msg)
        else:
            raise ValueError
