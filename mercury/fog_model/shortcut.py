from xdevs.models import Port
from mercury.msg.network import PhysicalPacket, NetworkPacket
from .common import Multiplexer


class NetworkMultiplexer(Multiplexer):
    def __init__(self, fixed_nodes: set):
        """
        Network communication layer multiplexer model
        :param fixed_nodes: set containing the IDs of all the fixed nodes in the scenario (i.e., APs, EDCs, and CNFs)
        """
        self.input = Port(NetworkPacket, 'input')
        self.outputs = {node_id: Port(NetworkPacket, 'output_' + node_id) for node_id in fixed_nodes}
        self.output_ues = Port(NetworkPacket, 'output_ues')  # Output port for messages to IoT devices
        super().__init__('network_mux', fixed_nodes)
        self.add_in_port(self.input)
        [self.add_out_port(port) for port in self.outputs.values()]
        self.add_out_port(self.output_ues)

    def build_routing_table(self):
        self.routing_table[self.input] = {node_id: self.outputs[node_id] for node_id in self.node_ids}

    def get_node_to(self, msg: NetworkPacket):
        return msg.node_to

    def catch_out_port_error(self, in_port: Port, node_to: str) -> Port:
        """If receiver node is not in the fixed nodes set, then the message is sent to the IoT devices layer"""
        return self.output_ues


class Shortcut(Multiplexer):
    def __init__(self, aps: set, edcs: set, cnfs: set, name: str = 'shortcut'):
        """
        Shortcut model for MErcury Lite
        :param aps:
        :param edcs:
        :param cnfs:
        :param name:
        """

        node_ids = {*aps, *edcs, *cnfs}

        self.ap_ids = aps
        self.edc_ids = edcs
        self.cnf_ids = cnfs

        self.input_xh_data = Port(PhysicalPacket, 'input_xh_data')
        self.input_radio_data = Port(PhysicalPacket, 'input_radio_data')
        self.input_radio_control = Port(PhysicalPacket, 'input_control')

        self.outputs_xh_data = {node_id: Port(PhysicalPacket, 'output_xh_data_' + node_id) for node_id in node_ids}
        self.outputs_radio_data = {ap_id: Port(PhysicalPacket, 'output_radio_data_' + ap_id) for ap_id in aps}
        self.outputs_radio_control = {ap_id: Port(PhysicalPacket, 'output_control_' + ap_id) for ap_id in aps}

        self.output_data_ues = Port(PhysicalPacket, 'output_data_ues')
        self.output_control_ues = Port(PhysicalPacket, 'output_control_ues')

        super().__init__(name, node_ids)

        [self.add_in_port(port) for port in [self.input_xh_data, self.input_radio_data, self.input_radio_control]]
        for ports in [self.outputs_xh_data, self.outputs_radio_control, self.outputs_radio_data]:
            [self.add_out_port(port) for port in ports.values()]
        self.add_out_port(self.output_control_ues)
        self.add_out_port(self.output_data_ues)

    def build_routing_table(self):
        self.routing_table[self.input_xh_data] = {node_id: self.outputs_xh_data[node_id] for node_id in self.node_ids}
        self.routing_table[self.input_radio_data] = dict()
        for cnf_id in self.cnf_ids:
            self.routing_table[self.input_radio_data][cnf_id] = self.outputs_xh_data[cnf_id]
        for edc_id in self.edc_ids:
            self.routing_table[self.input_radio_data][edc_id] = self.outputs_xh_data[edc_id]
        self.routing_table[self.input_radio_control] = {ap_id: self.outputs_radio_control[ap_id] for ap_id in self.ap_ids}

    def get_node_to(self, msg: PhysicalPacket):
        return msg.data.node_to

    def catch_out_port_error(self, in_port: Port, node_to: str) -> Port:
        """If receiver node is not in the fixed nodes set, then the message is sent to the IoT devices layer."""
        return self.output_control_ues if in_port == self.input_radio_control else self.output_data_ues
