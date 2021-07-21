from xdevs.models import Port
from mercury.config.core import CoreConfig
from mercury.config.radio import RadioAccessNetworkConfig
from mercury.msg.network import PhysicalPacket, CrosshaulPacket, NetworkPacket
from mercury.msg.network.packet.app_layer.ran import CreatePathRequest, RemovePathRequest, SwitchPathRequest, \
    CreatePathResponse, RemovePathResponse, SwitchPathResponse, StartHandOverRequest, StartHandOverResponse
from ...common import ExtendedAtomic


class CrosshaulTransceiver(ExtendedAtomic):
    def __init__(self, ap_id: str):
        """
        Access Point transceiver implementation for xDEVS
        :param ap_id: ID of the corresponding Edge Data Center
        """
        super().__init__('aps_ap_{}_crosshaul'.format(ap_id))

        self.ap_id = ap_id

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

        self.bypass_amf = RadioAccessNetworkConfig.bypass_amf
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
        self.add_in_port(self.input_to_crosshaul)
        self.add_out_port(self.output_from_crosshaul)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        self._check_crosshaul()
        self._check_access_control()
        self._check_transport()
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def _check_crosshaul(self):
        for msg in self.input_crosshaul.values:
            node_from_phys, net_msg = msg.expanse_packet()
            if net_msg.node_to != self.ap_id:
                self.add_msg_to_queue(self.output_from_crosshaul, net_msg)
            else:
                node_from_net, app_msg = net_msg.expanse_packet()
                if isinstance(app_msg, StartHandOverRequest):
                    self.add_msg_to_queue(self.output_start_ho_request, app_msg)
                if isinstance(app_msg, StartHandOverResponse):
                    self.add_msg_to_queue(self.output_start_ho_response, app_msg)
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
            self._add_access_control_msg_to_crosshaul(msg, msg.ap_to, msg.ap_to)
        for msg in self.input_start_ho_response.values:
            self._add_access_control_msg_to_crosshaul(msg, msg.ap_from, msg.ap_from)
        if not self.bypass_amf:
            for port in [self.input_create_path_request, self.input_remove_path_request, self.input_switch_path_request]:
                for msg in port.values:
                    self._add_access_control_msg_to_crosshaul(msg, CoreConfig.CORE_ID, CoreConfig.CORE_ID)

    def _check_transport(self):
        for msg in self.input_to_crosshaul.values:
            dc_id = msg.node_to
            self._add_transport_msg_to_crosshaul(msg, dc_id)

    def _add_access_control_msg_to_crosshaul(self, msg, network_to, physical_to):
        network = NetworkPacket(self.ap_id, network_to, msg)
        physical = CrosshaulPacket(self.ap_id, physical_to, network)
        self.add_msg_to_queue(self.output_crosshaul, physical)

    def _add_transport_msg_to_crosshaul(self, msg, physical_to):
        self.add_msg_to_queue(self.output_crosshaul, CrosshaulPacket(self.ap_id, physical_to, msg))
