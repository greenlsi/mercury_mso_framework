from xdevs.models import Port
from ...common import TransmissionDelayer
from ...common.crosshaul import CrosshaulConfiguration, CrosshaulTransceiverConfiguration
from ...common.packet.physical import PhysicalPacket
from ...common.packet.network import NetworkPacketConfiguration, NetworkPacket
from ...common.packet.application.ran.ran_access_control import CreatePathRequest, RemovePathRequest, SwitchPathRequest
from ...common.packet.application.ran.ran_access_control import CreatePathResponse, RemovePathResponse, SwitchPathResponse
from ...common.packet.application.ran.ran_handover import StartHandOverRequest, StartHandOverResponse
from ...common.packet.application.federation_management import NewSDNPath


class CrosshaulTransceiver(TransmissionDelayer):
    """
    Access Point transceiver implementation for xDEVS
    :param str name: Name of the stateless state machine xDEVS atomic module
    :param str ap_id: ID of the corresponding Edge Data Center
    :param CrosshaulTransceiverConfiguration crosshaul_transceiver: crosshaul_config transceiver configuration
    :param NetworkPacketConfiguration network_config: network packets configuration
    :param CrosshaulConfiguration crosshaul_config: Crosshaul layer configuration parameters
    :param str amf_id: ID of the Access and Mobility Management Function
    """
    def __init__(self, name, ap_id, crosshaul_transceiver, network_config, crosshaul_config, amf_id):
        super().__init__(name=name)

        self.ap_id = ap_id
        self.crosshaul_transceiver = crosshaul_transceiver
        self.network_config = network_config
        self.crosshaul_config = crosshaul_config
        self.amf_id = amf_id

        self.input_crosshaul_dl = Port(PhysicalPacket, name + '_input_crosshaul_dl')
        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.output_crosshaul_dl = Port(PhysicalPacket, name + '_output_crosshaul_dl')
        self.output_crosshaul_ul = Port(PhysicalPacket, name + '_output_crosshaul_ul')
        self.add_in_port(self.input_crosshaul_dl)
        self.add_in_port(self.input_crosshaul_ul)
        self.add_out_port(self.output_crosshaul_dl)
        self.add_out_port(self.output_crosshaul_ul)

        self.input_start_ho_request = Port(StartHandOverRequest, name + '_input_start_ho_request')
        self.input_start_ho_response = Port(StartHandOverResponse, name + '_input_start_ho_response')
        self.output_start_ho_request = Port(StartHandOverRequest, name + '_output_start_ho_request')
        self.output_start_ho_response = Port(StartHandOverResponse, name + '_output_start_ho_response')
        self.add_in_port(self.input_start_ho_request)
        self.add_in_port(self.input_start_ho_response)
        self.add_out_port(self.output_start_ho_request)
        self.add_out_port(self.output_start_ho_response)

        self.input_create_path_request = Port(CreatePathRequest, name + '_input_create_path_request')
        self.input_remove_path_request = Port(RemovePathRequest, name + '_input_remove_path_request')
        self.input_switch_path_request = Port(SwitchPathRequest, name + '_input_switch_path_request')
        self.output_create_path_response = Port(CreatePathResponse, name + '_output_create_path_response')
        self.output_remove_path_response = Port(RemovePathResponse, name + '_output_remove_path_response')
        self.output_switch_path_response = Port(SwitchPathResponse, name + '_output_switch_path_response')
        self.add_in_port(self.input_create_path_request)
        self.add_in_port(self.input_remove_path_request)
        self.add_in_port(self.input_switch_path_request)
        self.add_out_port(self.output_create_path_response)
        self.add_out_port(self.output_remove_path_response)
        self.add_out_port(self.output_switch_path_response)

        self.input_to_crosshaul = Port(NetworkPacket, name + '_input_to_crosshaul')
        self.output_from_crosshaul = Port(NetworkPacket, name + '_output_from_crosshaul')
        self.output_new_sdn_path = Port(NewSDNPath, name + '_output_new_sdn_path')
        self.add_in_port(self.input_to_crosshaul)
        self.add_out_port(self.output_from_crosshaul)
        self.add_out_port(self.output_new_sdn_path)

    def check_in_ports(self):
        self._check_crosshaul()
        self._check_access_control()
        self._check_transport()

    def _check_crosshaul(self):
        for msg in self.input_crosshaul_dl.values:
            node_from_phys, net_msg = self.__expand_physical_message(msg)
            if net_msg.node_to != self.ap_id:
                self.add_msg_to_queue(self.output_from_crosshaul, net_msg)
            else:
                node_from_net, app_msg = self.__expand_network_message(net_msg)
                if isinstance(app_msg, StartHandOverResponse):
                    self.add_msg_to_queue(self.output_start_ho_response, app_msg)
                elif isinstance(app_msg, SwitchPathResponse):
                    self.add_msg_to_queue(self.output_switch_path_response, app_msg)
                elif isinstance(app_msg, NewSDNPath):
                    self.add_msg_to_queue(self.output_new_sdn_path, app_msg)
                elif isinstance(app_msg, CreatePathResponse):
                    self.add_msg_to_queue(self.output_create_path_response, app_msg)
                elif isinstance(app_msg, RemovePathResponse):
                    self.add_msg_to_queue(self.output_remove_path_response, app_msg)
                else:
                    raise Exception("AP could not identify message type")
        for msg in self.input_crosshaul_ul.values:
            node_from_phys, net_msg = self.__expand_physical_message(msg)
            node_from_net, app_msg = self.__expand_network_message(net_msg)
            if isinstance(app_msg, StartHandOverRequest):
                self.add_msg_to_queue(self.output_start_ho_request, app_msg)
            else:
                raise Exception("AP could not identify message type")

    def _check_access_control(self):
        for msg in self.input_start_ho_request.values:
            self.__add_access_control_msg_to_crosshaul_ul(msg, msg.ap_to, msg.ap_to)
        for msg in self.input_start_ho_response.values:
            self.__add_access_control_msg_to_crosshaul_dl(msg, msg.ap_from, msg.ap_from)
        for port in [self.input_create_path_request, self.input_remove_path_request, self.input_switch_path_request]:
            for msg in port.values:
                self.__add_access_control_msg_to_crosshaul_ul(msg, self.amf_id, self.amf_id)

    def _check_transport(self):
        for msg in self.input_to_crosshaul.values:
            dc_id = msg.node_to
            self.__add_transport_msg_to_crosshaul_ul(msg, dc_id)

    def __encapsulate_network_packet(self, node_from, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(node_from, node_to, header, application_message)

    def __encapsulate_physical_packet(self, node_to, network_message):
        header = self.crosshaul_config.header
        power, bandwidth, spectral_efficiency = self.crosshaul_transceiver.get()
        return PhysicalPacket(self.ap_id, node_to, power, bandwidth, spectral_efficiency, header, network_message)

    def __expand_physical_message(self, physical_message):
        assert self.ap_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def __expand_network_message(self, network_message):
        assert self.ap_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __add_access_control_msg_to_crosshaul_ul(self, msg, network_to, physical_to):
        network = self.__encapsulate_network_packet(self.ap_id, network_to, msg)
        msg = self.__encapsulate_physical_packet(physical_to, network)
        size = msg.compute_size()
        channel = "access_control_ul"
        self.add_msg_to_buffer(self.output_crosshaul_ul, msg, channel, size, msg.bandwidth, msg.spectral_efficiency)

    def __add_access_control_msg_to_crosshaul_dl(self, msg, network_to, physical_to):
        network = self.__encapsulate_network_packet(self.ap_id, network_to, msg)
        msg = self.__encapsulate_physical_packet(physical_to, network)
        size = msg.compute_size()
        channel = "access_control_dl"
        self.add_msg_to_buffer(self.output_crosshaul_dl, msg, channel, size, msg.bandwidth, msg.spectral_efficiency)

    def __add_transport_msg_to_crosshaul_ul(self, msg, physical_to):
        msg = self.__encapsulate_physical_packet(physical_to, msg)
        size = msg.compute_size()
        channel = "transport"
        self.add_msg_to_buffer(self.output_crosshaul_ul, msg, channel, size, msg.bandwidth, msg.spectral_efficiency)
