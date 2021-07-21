from typing import Set
from abc import ABC, abstractmethod
from random import uniform
from collections import deque
from xdevs.models import PHASE_PASSIVE, Port, INFINITY
from xdevs.sim import Coordinator, SimulationClock
from mercury.config.iot_devices import UserEquipmentConfig, IoTDevicesConfig
from mercury.config.network import NodeConfig
from mercury.msg.network import PhysicalPacket, NetworkPacket
from mercury.msg.iot_devices import ServiceDelayReport
from .ue import UserEquipment, UserEquipmentLite
from ..common import ExtendedAtomic


class IoTDevicesAbstract(ExtendedAtomic, ABC):
    """
    IoT Devices Layer xDEVS model

    :param iot_layer_config: Fog Layer Configuration
    """
    def __init__(self, iot_layer_config: IoTDevicesConfig):
        super().__init__('iot_devices')
        # Unpack configuration parameters
        ue_config_list = iot_layer_config.ues_config
        self.max_guard_time = iot_layer_config.max_guard_time
        # Create UE creation timeline
        self.timeline = dict()
        for ue_id, ue_config in ue_config_list.items():
            t_start = ue_config.t_start
            t_end = ue_config.t_end
            if t_start < t_end:  # We only add UEs with valid lifetime
                if t_start not in self.timeline:
                    self.timeline[t_start] = set()
                self.timeline[t_start].add(ue_config)
        self.events = deque(sorted(self.timeline))  # Time when we have to trigger events
        self.ues = dict()
        # Root simulation clock to be shared among all the UEs
        self.root_clock = SimulationClock()

        # Define common input/output ports
        self.output_create_ue = Port(NodeConfig, 'output_create_ue')
        self.output_remove_ue = Port(str, 'output_remove_ue')
        self.output_service_delay_report = Port(ServiceDelayReport, 'output_service_delay_report')

        self.add_out_port(self.output_create_ue)
        self.add_out_port(self.output_remove_ue)
        self.add_out_port(self.output_service_delay_report)

    def deltint_extension(self):
        self.root_clock.time += self.sigma  # simulation clock advances according to sigma
        self.create_ues()                   # create new UEs
        self.ues_internal()                 # resolve any internal event of existing UEs
        next_sigma = self.next_sigma()
        self.hold_in(PHASE_PASSIVE, next_sigma)

    def deltext_extension(self, e):
        self.root_clock.time += e  # simulation clock advances according to elapsed time
        imminent_ues = self.forward_input()
        # Single delta to those UEs that have received a message
        for ue_id in imminent_ues:
            if self.ues[ue_id].time_next == self.root_clock.time:
                self.ues[ue_id].lambdaf()
                self.collect_output(self.ues[ue_id].model)
            self.ues[ue_id].deltfcn()
            self.ues[ue_id].clear()
        self.ues_internal()                 # resolve any internal event of existing UEs
        self.remove_ues()                   # remove outdated UEs
        self.hold_in(PHASE_PASSIVE, self.next_sigma())

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.hold_in(PHASE_PASSIVE, self.next_sigma())

    def exit(self):
        pass

    def create_ues(self):
        while self.events and self.events[0] <= self.root_clock.time:
            ues_config = self.timeline.pop(self.events.popleft())
            for ue_config in ues_config:
                ue_id = ue_config.ue_id
                ue = self.create_ue(ue_config)
                self.ues[ue_id] = Coordinator(ue, self.root_clock)
                self.ues[ue_id].initialize()
                self.add_msg_to_queue(self.output_create_ue, ue_config.radio_node)

    def ues_internal(self):
        for ue_id, ue in self.ues.items():
            # we execute as many internal transitions as needed to get a sigma greater than zero
            while ue.time_next <= self.root_clock.time:
                ue.lambdaf()                    # We trigger their lambdas...
                self.collect_output(ue.model)   # ... collect output messages to forward them...
                ue.deltfcn()                    # ... Compute the next UE state...
                ue.clear()                      # ... and clear the output

    def remove_ues(self):
        trash = {ue_id for ue_id, ue in self.ues.items() if self.ue_removable(ue)}
        for ue_id in trash:
            self.ues.pop(ue_id)
            self.add_msg_to_queue(self.output_remove_ue, ue_id)

    def min_next_time_ue(self):
        return min(ue.time_next - self.root_clock.time for ue in self.ues.values()) if self.ues else INFINITY

    def next_sigma(self):
        if self.msg_queue_empty():
            return min(self.min_next_time_ue(), self.events[0] - self.root_clock.time if self.events else INFINITY)
        return 0

    @abstractmethod
    def create_ue(self, ue_config: UserEquipmentConfig):
        pass

    @staticmethod
    @abstractmethod
    def ue_removable(ue: Coordinator) -> bool:
        return ue.time_next == INFINITY and ue.model.access_manager.ue_disconnected

    @abstractmethod
    def collect_output(self, ue: UserEquipment):
        pass

    @abstractmethod
    def forward_input(self) -> Set[str]:
        pass


class IoTDevices(IoTDevicesAbstract):
    def __init__(self, iot_layer_config: IoTDevicesConfig):
        super().__init__(iot_layer_config)

        self.input_radio_bc = Port(PhysicalPacket, 'input_radio_bc')
        self.input_radio_control_dl = Port(PhysicalPacket, 'input_radio_control_dl')
        self.input_radio_transport_dl = Port(PhysicalPacket, 'input_radio_transport_dl')
        self.output_repeat_pss = Port(str, 'output_repeat_pss')
        self.output_radio_control_ul = Port(PhysicalPacket, 'output_radio_control_ul')
        self.output_radio_transport_ul = Port(PhysicalPacket, 'output_radio_transport_ul')

        self.add_in_port(self.input_radio_bc)
        self.add_in_port(self.input_radio_control_dl)
        self.add_in_port(self.input_radio_transport_dl)
        self.add_out_port(self.output_repeat_pss)
        self.add_out_port(self.output_radio_control_ul)
        self.add_out_port(self.output_radio_transport_ul)

    def create_ue(self, ue_config: UserEquipmentConfig) -> UserEquipment:
        return UserEquipment(ue_config, uniform(0, self.max_guard_time))

    @staticmethod
    def ue_removable(ue: Coordinator) -> bool:
        return ue.time_next == INFINITY and ue.model.access_manager.ue_disconnected

    def collect_output(self, ue: UserEquipment):
        for port_from, port_to in [(ue.output_repeat_pss, self.output_repeat_pss),
                                   (ue.output_service_delay_report, self.output_service_delay_report),
                                   (ue.output_radio_control_ul, self.output_radio_control_ul),
                                   (ue.output_radio_transport_ul, self.output_radio_transport_ul)]:
            for msg in port_from.values:
                self.add_msg_to_queue(port_to, msg)

    def forward_input(self) -> Set[str]:
        imminent_ues = set()
        for msg in self.input_radio_bc.values:
            if msg.node_to in self.ues:
                imminent_ues.add(msg.node_to)
                self.ues[msg.node_to].model.input_radio_bc.add(msg)
        for msg in self.input_radio_control_dl.values:
            if msg.node_to in self.ues:
                imminent_ues.add(msg.node_to)
                self.ues[msg.node_to].model.input_radio_control_dl.add(msg)
        for msg in self.input_radio_transport_dl.values:
            if msg.node_to in self.ues:
                imminent_ues.add(msg.node_to)
                self.ues[msg.node_to].model.input_radio_transport_dl.add(msg)
            elif msg.data.node_to in self.ues:  # This is only for shortcut mode
                imminent_ues.add(msg.data.node_to)
                self.ues[msg.data.node_to].model.input_radio_transport_dl.add(msg)
        return imminent_ues


class IoTDevicesLite(IoTDevicesAbstract):
    def __init__(self, iot_layer_config: IoTDevicesConfig):
        super().__init__(iot_layer_config)

        # Define additional I/O ports
        self.input_network = Port(NetworkPacket, 'input_network')
        self.output_network = Port(NetworkPacket, 'output_network')
        self.add_in_port(self.input_network)
        self.add_out_port(self.output_network)

    def create_ue(self, ue_config: UserEquipmentConfig) -> UserEquipmentLite:
        return UserEquipmentLite(ue_config, uniform(0, self.max_guard_time))

    @staticmethod
    def ue_removable(ue: Coordinator) -> bool:
        return ue.time_next == INFINITY

    def collect_output(self, ue: UserEquipmentLite):
        for port_from, port_to in [(ue.output_service_delay_report, self.output_service_delay_report),
                                   (ue.output_network, self.output_network)]:
            for msg in port_from.values:
                self.add_msg_to_queue(port_to, msg)

    def forward_input(self) -> Set[str]:
        imminent_ues = set()
        for msg in self.input_network.values:
            if msg.node_to in self.ues:
                imminent_ues.add(msg.node_to)
                self.ues[msg.node_to].model.input_network.add(msg)
        return imminent_ues
