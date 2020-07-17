from xdevs.models import Port
from ...common import Stateless
from ...common.packet.packet import PhysicalPacket, NetworkPacketConfiguration, NetworkPacket
from .internal_interfaces import ConnectedAccessPoint, ExtendedPSS, AntennaPowered
from ...common.packet.apps.ran.ran_access import AccessRequest, AccessResponse, RadioResourceControl, \
    DisconnectRequest, DisconnectResponse
from ...common.packet.apps.ran.ran_handover import HandOverStarted, HandOverReady, HandOverFinished, \
    HandOverResponse


class UserEquipmentAntenna(Stateless):
    """
    xDEVS module that models the behavior of a User Equipment antenna.
    :param name: Name of the antenna DEVS module
    :param ue_id: ID of the UE with the antenna
    :param network_config: network packets configuration
    """

    UL_MCS = 'ul_mcs_list'
    DL_MCS = 'dl_mcs_list'
    BANDWIDTH = 'bandwidth'

    def __init__(self, name: str, ue_id: str, network_config: NetworkPacketConfiguration):

        super().__init__(name=name)
        self.ue_id = ue_id
        self.network_config = network_config

        self.connected_ap = None
        self.powered = False
        self.connection_parameters = dict()

        # Radio-antenna ports
        self.input_radio_bc = Port(PhysicalPacket, 'input_radio_bc')
        self.input_radio_control_dl = Port(PhysicalPacket, 'input_radio_control_dl')
        self.input_radio_transport_dl = Port(PhysicalPacket, 'input_radio_transport_dl')
        self.output_radio_control_ul = Port(PhysicalPacket, 'output_radio_control_ul')
        self.output_radio_transport_ul = Port(PhysicalPacket, 'output_radio_transport_ul')
        self.add_in_port(self.input_radio_bc)
        self.add_in_port(self.input_radio_control_dl)
        self.add_in_port(self.input_radio_transport_dl)
        self.add_out_port(self.output_radio_control_ul)
        self.add_out_port(self.output_radio_transport_ul)

        # Ambassador-antenna ports
        self.input_service = Port(NetworkPacket, 'input_ambassador')
        self.output_service = Port(NetworkPacket, 'output_ambassador')
        self.add_in_port(self.input_service)
        self.add_out_port(self.output_service)

        # Access manager-antenna ports
        self.input_access_request = Port(AccessRequest, 'input_access_request')
        self.input_disconnect_request = Port(DisconnectRequest, 'input_disconnect_request')
        self.input_rrc = Port(RadioResourceControl, 'input_rrc')
        self.input_ho_ready = Port(HandOverReady, 'input_ho_ready')
        self.input_ho_response = Port(HandOverResponse, 'input_ho_response')
        self.input_connected_ap = Port(ConnectedAccessPoint, 'input_connected_ap')
        self.input_antenna_powered = Port(AntennaPowered, 'input_antenna_powered')
        self.output_pss = Port(ExtendedPSS, 'output_pss')
        self.output_access_response = Port(AccessResponse, 'output_access_response')
        self.output_disconnect_response = Port(DisconnectResponse, 'output_disconnect_response')
        self.output_ho_started = Port(HandOverStarted, 'output_ho_started')
        self.output_ho_finished = Port(HandOverFinished, 'output_ho_finished')
        self.add_in_port(self.input_access_request)
        self.add_in_port(self.input_disconnect_request)
        self.add_in_port(self.input_rrc)
        self.add_in_port(self.input_ho_ready)
        self.add_in_port(self.input_ho_response)
        self.add_in_port(self.input_connected_ap)
        self.add_in_port(self.input_antenna_powered)
        self.add_out_port(self.output_pss)
        self.add_out_port(self.output_access_response)
        self.add_out_port(self.output_disconnect_response)
        self.add_out_port(self.output_ho_started)
        self.add_out_port(self.output_ho_finished)

    def check_in_ports(self):
        self._check_antenna_powered()
        self._check_connected_ap()
        if self.connected_ap is not None:
            assert self.powered
        if self.powered:
            self._check_radio_control_dl()
            self._check_radio_transport_dl()
            self._check_radio_broadcast()
            self._check_access_manager()
            self._check_service_ambassador()

    def _check_antenna_powered(self):
        if self.input_antenna_powered:
            self.powered = self.input_antenna_powered.get().powered

    def _check_connected_ap(self):
        if self.input_connected_ap:
            self.connected_ap = self.input_connected_ap.get().ap_id

    def _check_radio_control_dl(self):
        for job in self.input_radio_control_dl.values:
            ap_id, network_msg = self._expand_physical_message(job)
            ap_id, app_msg = self._expand_network_message(network_msg)
            if ap_id == self.connected_ap:
                if isinstance(app_msg, HandOverStarted):
                    self.add_msg_to_queue(self.output_ho_started, app_msg)
                elif isinstance(app_msg, AccessResponse):
                    self.add_msg_to_queue(self.output_access_response, app_msg)
                else:
                    raise Exception("Unable to determine message type")
            else:
                if isinstance(app_msg, HandOverFinished):
                    self.add_msg_to_queue(self.output_ho_finished, app_msg)
                elif isinstance(app_msg, DisconnectResponse):
                    self.add_msg_to_queue(self.output_disconnect_response, app_msg)
                elif isinstance(app_msg, AccessResponse):
                    self.add_msg_to_queue(self.output_access_response, app_msg)
                else:
                    raise Exception("Unable to determine message type")

    def _check_radio_transport_dl(self):
        for job in self.input_radio_transport_dl.values:
            ap_id, network_msg = self._expand_physical_message(job)
            # if ap_id == self.connected_ap:
            self.add_msg_to_queue(self.output_service, network_msg)

    def _check_radio_broadcast(self):
        for job in self.input_radio_bc.values:
            ap_id, network_msg = self._expand_physical_message(job)
            ap_id, app_msg = self._expand_network_message(network_msg)
            self.add_msg_to_queue(self.output_pss, ExtendedPSS(ap_id, job.snr))

    def _check_access_manager(self):
        for msg in self.input_access_request.values:
            self._add_app_msg_to_radio_control_ul(msg, msg.ap_id)
        for msg in self.input_disconnect_request.values:
            self._add_app_msg_to_radio_control_ul(msg, msg.ap_id)
        for msg in self.input_rrc.values:
            self._add_app_msg_to_radio_control_ul(msg, msg.ap_id)
        for msg in self.input_ho_ready.values:
            self._add_app_msg_to_radio_control_ul(msg, msg.ap_to)
        for msg in self.input_ho_response.values:
            self._add_app_msg_to_radio_control_ul(msg, msg.ap_from)

    def _check_service_ambassador(self):
        for msg in self.input_service.values:
            self._add_network_msg_to_radio_transport_ul(msg)

    def _add_app_msg_to_radio_control_ul(self, msg, node_to):
        network = self._encapsulate_network_packet(self.ue_id, node_to, msg)
        msg = self._encapsulate_physical_packet(node_to, network)
        self.add_msg_to_queue(self.output_radio_control_ul, msg)

    def _add_network_msg_to_radio_transport_ul(self, msg):
        physical_to = self.connected_ap
        msg = self._encapsulate_physical_packet(physical_to, msg)
        self.add_msg_to_queue(self.output_radio_transport_ul, msg)

    def _expand_physical_message(self, physical_message):
        assert self.ue_id == physical_message.node_to or physical_message.node_to is None
        return physical_message.node_from, physical_message.data

    def _expand_network_message(self, network_message):
        assert self.ue_id == network_message.node_to or network_message.node_to is None
        return network_message.node_from, network_message.data

    def _encapsulate_network_packet(self, node_from: str, node_to: str, application_message):
        header = self.network_config.header
        return NetworkPacket(node_from, node_to, header, application_message)

    def _encapsulate_physical_packet(self, node_to: str, network_message: NetworkPacket):
        return PhysicalPacket(node_from=self.ue_id, node_to=node_to, data=network_message)

    def process_internal_messages(self):
        pass
