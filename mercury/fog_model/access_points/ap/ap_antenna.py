from typing import Union
from xdevs.models import Port
from ...network import EnableChannels
from ...common import Stateless
from ...common.packet.packet import PhysicalPacket, NetworkPacketConfiguration, NetworkPacket
from ...common.packet.apps.ran.ran_access import PrimarySynchronizationSignal, AccessRequest, AccessResponse, \
    RadioResourceControl, DisconnectRequest, DisconnectResponse
from ...common.packet.apps.ran.ran_handover import HandOverStarted, HandOverReady, HandOverFinished, \
    HandOverResponse
from ...common.packet.apps.service import GetDataCenterRequest, GetDataCenterResponse


class AccessPointAntenna(Stateless):
    def __init__(self, name: str, ap_id: str, network_config: NetworkPacketConfiguration):
        """
        Access Point Antenna xDEVS implementation
        :param str name: name of the xDEVS module
        :param str ap_id: AP ID
        :param NetworkPacketConfiguration network_config: Network packets configuration
        """
        super().__init__(name=name)

        self.ap_id = ap_id
        self.network_config = network_config

        self.ue_connected = list()

        self.input_radio_control_ul = Port(PhysicalPacket, name + '_input_radio_control_ul')
        self.input_radio_transport_ul = Port(PhysicalPacket, name + '_input_radio_transport_ul')
        self.output_radio_bc = Port(PhysicalPacket, name + '_output_radio_bc')
        self.output_radio_control_dl = Port(PhysicalPacket, name + '_output_radio_control_dl')
        self.output_radio_transport_dl = Port(PhysicalPacket, name + '_output_radio_transport_dl')
        self.add_in_port(self.input_radio_control_ul)
        self.add_in_port(self.input_radio_transport_ul)
        self.add_out_port(self.output_radio_bc)
        self.add_out_port(self.output_radio_control_dl)
        self.add_out_port(self.output_radio_transport_dl)

        self.input_connected_ue_list = Port(EnableChannels, name + '_input_connected_ue_list')
        self.add_in_port(self.input_connected_ue_list)

        self.input_pss = Port(PrimarySynchronizationSignal, name + '_input_pss')
        self.add_in_port(self.input_pss)

        self.input_access_response = Port(AccessResponse, name + '_input_access_response')
        self.input_disconnect_response = Port(DisconnectResponse, name + '_input_disconnect_response')
        self.input_ho_started = Port(HandOverStarted, name + '_input_ho_started')
        self.input_ho_finished = Port(HandOverFinished, name + '_input_ho_finished')
        self.output_rrc = Port(RadioResourceControl, name + '_output_rrc')
        self.output_access_request = Port(AccessRequest, name + '_output_access_request')
        self.output_disconnect_request = Port(DisconnectRequest, name + '_output_disconnect_request')
        self.output_ho_ready = Port(HandOverReady, name + '_output_ho_ready')
        self.output_ho_response = Port(HandOverResponse, name + '_output_ho_response')
        self.add_in_port(self.input_access_response)
        self.add_in_port(self.input_disconnect_response)
        self.add_in_port(self.input_ho_started)
        self.add_in_port(self.input_ho_finished)
        self.add_out_port(self.output_rrc)
        self.add_out_port(self.output_access_request)
        self.add_out_port(self.output_disconnect_request)
        self.add_out_port(self.output_ho_ready)
        self.add_out_port(self.output_ho_response)

        self.input_service_routing_response = Port(GetDataCenterResponse, name + '_input_service_routing_response')
        self.input_to_radio_dl = Port(NetworkPacket, name + '_input_to_radio_dl')
        self.output_service_routing_request = Port(GetDataCenterRequest, name + '_output_service_routing_response')
        self.output_from_radio_ul = Port(NetworkPacket, name + '_output_from_radio_ul')
        self.add_in_port(self.input_service_routing_response)
        self.add_in_port(self.input_to_radio_dl)
        self.add_out_port(self.output_service_routing_request)
        self.add_out_port(self.output_from_radio_ul)

    def check_in_ports(self):
        self._check_new_ue_list()
        self._check_radio_control_ul()
        self._check_radio_transport_ul()
        self._check_signaling()
        self._check_access_control()
        self._check_transport()

    def _check_new_ue_list(self):
        if self.input_connected_ue_list:
            ue_list = self.input_connected_ue_list.get().nodes_to
            self.ue_connected = ue_list

    def _check_radio_control_ul(self):
        for job in self.input_radio_control_ul.values:
            ue_id, network_msg = self.__expand_physical_message(job)
            ue_id, app_msg = self.__expand_network_message(network_msg)
            if ue_id in self.ue_connected:
                if isinstance(app_msg, RadioResourceControl):
                    self.add_msg_to_queue(self.output_rrc, app_msg)
                elif isinstance(app_msg, HandOverResponse):
                    self.add_msg_to_queue(self.output_ho_response, app_msg)
                elif isinstance(app_msg, DisconnectRequest):
                    self.add_msg_to_queue(self.output_disconnect_request, app_msg)
                else:
                    raise Exception("Unable to determine message type")
            else:
                if isinstance(app_msg, HandOverReady):
                    self.add_msg_to_queue(self.output_ho_ready, app_msg)
                elif isinstance(app_msg, AccessRequest):
                    self.add_msg_to_queue(self.output_access_request, app_msg)
                else:
                    raise Exception("Unable to determine message type")

    def _check_radio_transport_ul(self):
        for job in self.input_radio_transport_ul.values:
            ue_id, network_msg = self.__expand_physical_message(job)
            if ue_id in self.ue_connected:
                if network_msg.node_to != self.ap_id:
                    self.add_msg_to_queue(self.output_from_radio_ul, network_msg)
                else:
                    ap_id, app_msg = self.__expand_network_message(network_msg)
                    if isinstance(app_msg, GetDataCenterRequest):
                        self.add_msg_to_queue(self.output_service_routing_request, app_msg)
                    else:
                        raise Exception("Unable to determine message type")

    def _check_signaling(self):
        for msg in self.input_pss.values:
            self.__add_app_msg_to_radio_bc(msg)

    def _check_access_control(self):
        for msg in self.input_access_response.values:
            self.__add_app_msg_to_radio_control_dl(msg)
        for msg in self.input_disconnect_response.values:
            self.__add_app_msg_to_radio_control_dl(msg)
        for msg in self.input_ho_started.values:
            self.__add_app_msg_to_radio_control_dl(msg)
        for msg in self.input_ho_finished.values:
            self.__add_app_msg_to_radio_control_dl(msg)

    def _check_transport(self):
        for msg in self.input_service_routing_response.values:
            self.__add_app_msg_to_radio_transport_dl(msg)
        for msg in self.input_to_radio_dl.values:
            self.__add_network_msg_to_radio_transport_dl(msg)

    def __encapsulate_network_packet(self, node_from, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(node_from, node_to, header, application_message)

    def __encapsulate_physical_packet(self, node_to: Union[str, None], network_message: NetworkPacket):
        return PhysicalPacket(node_from=self.ap_id, node_to=node_to, data=network_message)

    def __expand_physical_message(self, physical_message):
        assert self.ap_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def __expand_network_message(self, network_message):
        assert self.ap_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __add_app_msg_to_radio_bc(self, msg):
        network = self.__encapsulate_network_packet(self.ap_id, msg.ue_id, msg)
        phys = self.__encapsulate_physical_packet(network.node_to, network)
        self.add_msg_to_queue(self.output_radio_bc, phys)

    def __add_app_msg_to_radio_control_dl(self, msg):
        network_to = msg.ue_id
        physical_to = msg.ue_id
        network = self.__encapsulate_network_packet(self.ap_id, network_to, msg)
        phys = self.__encapsulate_physical_packet(physical_to, network)
        self.add_msg_to_queue(self.output_radio_control_dl, phys)

    def __add_app_msg_to_radio_transport_dl(self, msg):
        network_to = msg.ue_id
        network = self.__encapsulate_network_packet(self.ap_id, network_to, msg)
        self.__add_network_msg_to_radio_transport_dl(network)

    def __add_network_msg_to_radio_transport_dl(self, msg: NetworkPacket):
        physical_to = msg.node_to
        phys = self.__encapsulate_physical_packet(physical_to, msg)
        self.add_msg_to_queue(self.output_radio_transport_dl, phys)

    def process_internal_messages(self):
        pass
