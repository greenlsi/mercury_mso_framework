from xdevs.models import Port
from .common.multiplexer import Multiplexer
from .common.packet.packet import PhysicalPacket, NetworkPacket


class Shortcut(Multiplexer):

    def __init__(self, ue_ids_list, ap_ids_list, edc_ids_list, core_ids_list, name='shortcut'):

        node_id_list = [*ue_ids_list, *ap_ids_list, *edc_ids_list, *core_ids_list]
        assert len(node_id_list) == len(set(node_id_list))

        self.ue_ids_list = ue_ids_list
        self.ap_ids_list = ap_ids_list
        self.edc_ids_list = edc_ids_list
        self.core_ids_list = core_ids_list

        self.input_xh = Port(PhysicalPacket, 'input_xh')
        self.input_radio_control = Port(PhysicalPacket, 'input_radio_control')
        self.input_radio_transport = Port(PhysicalPacket, 'input_radio_transport')

        self.outputs_xh = dict()
        self.outputs_radio_control = dict()
        self.outputs_radio_transport = dict()
        for node_id in [*ap_ids_list, *edc_ids_list, *core_ids_list]:
            self.outputs_xh[node_id] = Port(PhysicalPacket, 'output_xh_' + node_id)
        for out_ports in [(self.outputs_radio_control, 'control'), (self.outputs_radio_transport, 'transport')]:
            for node_id in [*ue_ids_list, *ap_ids_list]:
                out_ports[0][node_id] = Port(PhysicalPacket, 'output_{}_{}'.format(out_ports[1], node_id))

        super().__init__(name, node_id_list)

        self.add_in_port(self.input_xh)
        self.add_in_port(self.input_radio_control)
        self.add_in_port(self.input_radio_transport)
        for node_id in [*ap_ids_list, *edc_ids_list, *core_ids_list]:
            self.add_out_port(self.outputs_xh[node_id])
        for out_ports in [(self.outputs_radio_control, 'control'), (self.outputs_radio_transport, 'transport')]:
            for node_id in [*ue_ids_list, *ap_ids_list]:
                self.add_out_port(out_ports[0][node_id])

    def build_routing_table(self):
        self.routing_table[self.input_xh] = dict()
        for ue_id in self.ue_ids_list:
            self.routing_table[self.input_xh][ue_id] = self.outputs_radio_transport[ue_id]
        for node_id in [*self.ap_ids_list, *self.edc_ids_list, *self.core_ids_list]:
            self.routing_table[self.input_xh][node_id] = self.outputs_xh[node_id]

        self.routing_table[self.input_radio_control] = dict()
        for node_id in [*self.ap_ids_list, *self.ue_ids_list]:
            self.routing_table[self.input_radio_control][node_id] = self.outputs_radio_control[node_id]

        self.routing_table[self.input_radio_transport] = dict()
        for edc_id in self.edc_ids_list:
            self.routing_table[self.input_radio_transport][edc_id] = self.outputs_xh[edc_id]
        for node_id in [*self.ue_ids_list, *self.ap_ids_list]:
            self.routing_table[self.input_radio_transport][node_id] = self.outputs_radio_transport[node_id]

    def get_node_to(self, msg: PhysicalPacket):
        return msg.data.node_to


class NetworkMultiplexer(Multiplexer):
    def __init__(self, node_id_list, name="network_mux"):
        self.input = Port(NetworkPacket, 'input')
        self.outputs = {node_id: Port(NetworkPacket, 'output_' + node_id) for node_id in node_id_list}
        super().__init__(name, node_id_list)
        self.add_in_port(self.input)
        [self.add_out_port(port) for port in self.outputs.values()]

    def build_routing_table(self):
        self.routing_table[self.input] = dict()
        for node_id in self.node_id_list:
            self.routing_table[self.input][node_id] = self.outputs[node_id]

    def get_node_to(self, msg: NetworkPacket):
        return msg.node_to
