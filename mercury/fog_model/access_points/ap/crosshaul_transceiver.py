from xdevs.models import Port
from ...common import Stateless
from ...common.packet.packet import PhysicalPacket,  NetworkPacketConfiguration, NetworkPacket
from ...common.packet.apps.ran.ran_access_control import CreatePathRequest, RemovePathRequest, SwitchPathRequest, \
    CreatePathResponse, RemovePathResponse, SwitchPathResponse
from ...common.packet.apps.ran.ran_handover import StartHandOverRequest, StartHandOverResponse
from ...common.packet.apps.federation_management import NewSDNPath


class CrosshaulTransceiver(Stateless):
    def __init__(self, name: str, ap_id: str, network_config: NetworkPacketConfiguration,
                 amf_id: str, bypass_amf: bool):
        """
        Access Point transceiver implementation for xDEVS
        :param name: Name of the stateless state machine xDEVS atomic module
        :param ap_id: ID of the corresponding Edge Data Center
        :param network_config: network packets configuration
        :param amf_id: ID of the Access and Mobility Management Function
        """
        super().__init__(name=name)

        self.ap_id = ap_id
        self.network_config = network_config
        self.amf_id = amf_id

        self.input_crosshaul = Port(PhysicalPacket, 'input_crosshaul')
        self.output_crosshaul = Port(PhysicalPacket, 'output_crosshaul')
        self.add_in_port(self.input_crosshaul)
        self.add_out_port(self.output_crosshaul)

        self.input_start_ho_request = Port(StartHandOverRequest, 'input_start_ho_request')
        self.input_start_ho_response = Port(StartHandOverResponse, 'input_start_ho_response')
        self.output_start_ho_request = Port(StartHandOverRequest, 'output_start_ho_request')
        self.output_start_ho_response = Port(StartHandOverResponse, 'output_start_ho_response')
        self.add_in_port(self.input_start_ho_request)
        self.add_in_port(self.input_start_ho_response)
        self.add_out_port(self.output_start_ho_request)
        self.add_out_port(self.output_start_ho_response)

        self.bypass_amf = bypass_amf
        if not self.bypass_amf:
            self.input_create_path_request = Port(CreatePathRequest, 'input_create_path_request')
            self.input_remove_path_request = Port(RemovePathRequest, 'input_remove_path_request')
            self.input_switch_path_request = Port(SwitchPathRequest, 'input_switch_path_request')
            self.output_create_path_response = Port(CreatePathResponse, 'output_create_path_response')
            self.output_remove_path_response = Port(RemovePathResponse, 'output_remove_path_response')
            self.output_switch_path_response = Port(SwitchPathResponse, 'output_switch_path_response')
            self.add_in_port(self.input_create_path_request)
            self.add_in_port(self.input_remove_path_request)
            self.add_in_port(self.input_switch_path_request)
            self.add_out_port(self.output_create_path_response)
            self.add_out_port(self.output_remove_path_response)
            self.add_out_port(self.output_switch_path_response)

        self.input_to_crosshaul = Port(NetworkPacket, 'input_to_crosshaul')
        self.output_from_crosshaul = Port(NetworkPacket, 'output_from_crosshaul')
        self.output_new_sdn_path = Port(NewSDNPath, 'output_new_sdn_path')
        self.add_in_port(self.input_to_crosshaul)
        self.add_out_port(self.output_from_crosshaul)
        self.add_out_port(self.output_new_sdn_path)

    def check_in_ports(self):
        self._check_crosshaul()
        self._check_access_control()
        self._check_transport()

    def _check_crosshaul(self):
        for msg in self.input_crosshaul.values:
            node_from_phys, net_msg = self.__expand_physical_message(msg)
            if net_msg.node_to != self.ap_id:
                self.add_msg_to_queue(self.output_from_crosshaul, net_msg)
            else:
                node_from_net, app_msg = self.__expand_network_message(net_msg)
                if isinstance(app_msg, StartHandOverRequest):
                    self.add_msg_to_queue(self.output_start_ho_request, app_msg)
                if isinstance(app_msg, StartHandOverResponse):
                    self.add_msg_to_queue(self.output_start_ho_response, app_msg)
                elif isinstance(app_msg, NewSDNPath):
                    self.add_msg_to_queue(self.output_new_sdn_path, app_msg)
                elif not self.bypass_amf:
                    if isinstance(app_msg, SwitchPathResponse):
                        self.add_msg_to_queue(self.output_switch_path_response, app_msg)
                    elif isinstance(app_msg, CreatePathResponse):
                        self.add_msg_to_queue(self.output_create_path_response, app_msg)
                    elif isinstance(app_msg, RemovePathResponse):
                        self.add_msg_to_queue(self.output_remove_path_response, app_msg)
                else:
                    raise Exception("AP could not identify message type")

    def _check_access_control(self):
        for msg in self.input_start_ho_request.values:
            self.__add_access_control_msg_to_crosshaul(msg, msg.ap_to, msg.ap_to)
        for msg in self.input_start_ho_response.values:
            self.__add_access_control_msg_to_crosshaul(msg, msg.ap_from, msg.ap_from)
        if not self.bypass_amf:
            for port in [self.input_create_path_request, self.input_remove_path_request, self.input_switch_path_request]:
                for msg in port.values:
                    self.__add_access_control_msg_to_crosshaul(msg, self.amf_id, self.amf_id)

    def _check_transport(self):
        for msg in self.input_to_crosshaul.values:
            dc_id = msg.node_to
            self.__add_transport_msg_to_crosshaul(msg, dc_id)

    def __encapsulate_network_packet(self, node_from, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(node_from, node_to, header, application_message)

    def __encapsulate_physical_packet(self, node_to: str, network_message: NetworkPacket):
        return PhysicalPacket(node_from=self.ap_id, node_to=node_to, data=network_message)

    def __expand_physical_message(self, physical_message):
        assert self.ap_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def __expand_network_message(self, network_message):
        assert self.ap_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __add_access_control_msg_to_crosshaul(self, msg, network_to, physical_to):
        network = self.__encapsulate_network_packet(self.ap_id, network_to, msg)
        msg = self.__encapsulate_physical_packet(physical_to, network)
        self.add_msg_to_queue(self.output_crosshaul, msg)

    def __add_transport_msg_to_crosshaul(self, msg, physical_to):
        msg = self.__encapsulate_physical_packet(physical_to, msg)
        self.add_msg_to_queue(self.output_crosshaul, msg)

    def process_internal_messages(self):
        pass
