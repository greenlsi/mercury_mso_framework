from math import sqrt, log10
from abc import ABC, abstractmethod
from xdevs.models import INFINITY, Port
from .fsm import FiniteStateMachine
from .packet.physical import PhysicalPacket
from .packet.network import NetworkPacket
from .mobility import NewLocation

PHASE_IDLE = 'idle'

PROP_DELAY = 'propagation_delay'
ATTENUATION = 'attenuation'


class Attenuator(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def attenuate(self, frequency, distance):
        """
        Returns attenuation (in dB) depending on a given distance
        :param float frequency: carrier frequency of the signal to be attenuated
        :param float distance: distance"""
        pass


class FreeSpaceLossAttenuator(Attenuator):
    def attenuate(self, frequency, distance):
        if distance == 0 or frequency == 0:
            return 0
        attenuation = 20 * (log10(distance) + log10(frequency)) - 147.55
        return attenuation


class DummyAttenuator(Attenuator):
    def attenuate(self, frequency, distance):
        return 0


class Point2PointNetwork(FiniteStateMachine, ABC):

    def __init__(self, name, nodes_location, frequency, attenuator=None, prop_speed=0, penalty_delay=0):
        states = [PHASE_IDLE]
        int_table = {PHASE_IDLE: self.internal_idle}
        ext_table = {PHASE_IDLE: self.check_in_ports}
        lambda_table = {PHASE_IDLE: self.process_internal_messages}
        super().__init__(states, int_table, ext_table, lambda_table, PHASE_IDLE, INFINITY, name)
        self.frequency = frequency
        self.attenuator = attenuator
        if prop_speed < 0:
            raise ValueError('Propagation speed must be greater than or equal to zero')
        self.prop_speed = prop_speed
        if penalty_delay < 0:
            raise ValueError('Penalty delay must be greater than or equal to zero')
        self.penalty_delay = penalty_delay

        self.input_new_location = Port(NewLocation, "input_new_location")
        self.add_in_port(self.input_new_location)

        self.msg_buffer = dict()
        self.nodes_location = {node_id: node_location for node_id, node_location in nodes_location.items()}

        self.routing_table = dict()
        self.lookup_table = dict()
        self.build_routing_table()

    def internal_idle(self):
        return PHASE_IDLE, self._next_message_in_queue()

    def check_in_ports(self):
        for msg in self.input_new_location.values:
            node_id = msg.node_id
            assert node_id in self.nodes_location
            location = msg.location
            self.nodes_location[node_id] = location
            if node_id in self.lookup_table:
                self.lookup_table.pop(node_id)
            else:
                for _, secondaries in self.lookup_table.items():
                    if node_id in secondaries:
                        secondaries.pop(node_id)
        for input_port in self.in_ports:
            self._check_physical_port(input_port)
        return PHASE_IDLE, self._next_message_in_queue()

    def process_internal_messages(self):
        messages = self.msg_buffer.pop(self._clock, list())
        for msg in messages:
            self.add_msg_to_queue(msg[0], msg[1])

    def _next_message_in_queue(self):
        schedule = list(self.msg_buffer.keys())
        schedule.sort()
        return (schedule[0] - self._clock) if schedule else INFINITY

    def compute_internals(self, phys_msg):
        primary, secondary = self.get_lookup_keys(phys_msg)
        if primary not in self.lookup_table:
            self.lookup_table[primary] = dict()
        if secondary not in self.lookup_table[primary]:
            self._add_secondary(primary, secondary)
        prop_delay = self.lookup_table[primary][secondary][PROP_DELAY]
        attenuation = self.lookup_table[primary][secondary][ATTENUATION]
        return prop_delay, attenuation

    def _add_secondary(self, primary, secondary):
        distance = self._compute_distance(primary, secondary)
        prop_delay = self._compute_propagation_delay(distance)
        attenuation = self._compute_attenuation(distance)
        self.lookup_table[primary][secondary] = {PROP_DELAY: prop_delay, ATTENUATION: attenuation}

    def _compute_distance(self, node_a, node_b):
        location_a = self.nodes_location[node_a]
        location_b = self.nodes_location[node_b]
        return sqrt(sum([(location_a[i] - location_b[i]) ** 2 for i in range(len(location_a))]))

    def _compute_propagation_delay(self, distance):
        try:
            return distance / self.prop_speed
        except ZeroDivisionError:
            return 0

    def _compute_attenuation(self, distance):
        try:
            return self.attenuator.attenuate(self.frequency, distance)
        except AttributeError:
            return 0

    def add_message_to_buffer(self, phys_msg, delay):
        next_sigma = self._clock + delay
        if next_sigma not in self.msg_buffer:
            self.msg_buffer[next_sigma] = list()
        self.msg_buffer[next_sigma].append((self.routing_table[phys_msg.node_to], phys_msg))

    @abstractmethod
    def get_lookup_keys(self, phys_msg):
        """Method to determine the primary and secondary keys of the lookup table"""
        pass

    @abstractmethod
    def build_routing_table(self):
        """Build the routing table like this: {node_to: out_port}"""
        pass

    def _check_physical_port(self, phys_port):
        if phys_port.p_type == PhysicalPacket:
            for phys_msg in phys_port.values:
                delay = self.penalty_delay
                power = phys_msg.power
                prop_delay, attenuation = self.compute_internals(phys_msg)
                delay += prop_delay
                power -= attenuation
                msg = PhysicalPacket(phys_msg.node_from, phys_msg.node_to, power, phys_msg.bandwidth,
                                     phys_msg.spectral_efficiency, phys_msg.header, phys_msg.data)
                self.add_message_to_buffer(msg, delay)


class BroadcastNetwork(Point2PointNetwork, ABC):
    def __init__(self, name, nodes_location, target_nodes_location, frequency, attenuator=None, prop_speed=0,
                 penalty_delay=0):
        super().__init__(name, nodes_location, frequency, attenuator, prop_speed, penalty_delay)
        for node_id in target_nodes_location:
            assert node_id in nodes_location
        self.target_nodes_location = target_nodes_location

    def _check_physical_port(self, phys_port):
        if phys_port.p_type == PhysicalPacket and phys_port:
            for phys_msg in phys_port.values:
                for node_to in self.target_nodes_location:
                    delay = self.penalty_delay
                    distance = self._compute_distance(phys_msg.node_from, node_to)
                    delay += self._compute_propagation_delay(distance)
                    power = phys_msg.power
                    net = phys_msg.data
                    network_packet = NetworkPacket(phys_msg.node_from, node_to, net.header, net.data)
                    if self.attenuator:
                        power -= self.attenuator.attenuate(self.frequency, distance)
                    msg = PhysicalPacket(phys_msg.node_from, node_to, power, phys_msg.bandwidth,
                                         phys_msg.spectral_efficiency, phys_msg.header, network_packet)
                    self.add_message_to_buffer(msg, delay)
