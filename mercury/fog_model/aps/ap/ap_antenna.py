from xdevs.models import Port
from mercury.msg.network import PhysicalPacket, RadioPacket, NetworkPacket, EnableChannels
from mercury.msg.network.packet.app_layer.ran import PrimarySynchronizationSignal, ConnectRequest, ConnectResponse, \
    RadioResourceControl, DisconnectRequest, DisconnectResponse, HandOverStarted, HandOverReady, HandOverFinished, \
    HandOverResponse
from ...common import ExtendedAtomic


class AccessPointAntenna(ExtendedAtomic):
    def __init__(self, ap_id: str):
        """
        Access Point Antenna xDEVS implementation
        :param str ap_id: AP ID
        """
        super().__init__('aps_ap_{}_antenna'.format(ap_id))

        self.ap_id = ap_id

        self.ue_connected = list()

        self.input_radio_control_ul = Port(PhysicalPacket, 'input_radio_control_ul')
        self.input_radio_transport_ul = Port(PhysicalPacket, 'input_radio_transport_ul')
        self.output_radio_bc = Port(PhysicalPacket, 'output_radio_bc')
        self.output_radio_control_dl = Port(PhysicalPacket, 'output_radio_control_dl')
        self.output_radio_transport_dl = Port(PhysicalPacket, 'output_radio_transport_dl')
        self.add_in_port(self.input_radio_control_ul)
        self.add_in_port(self.input_radio_transport_ul)
        self.add_out_port(self.output_radio_bc)
        self.add_out_port(self.output_radio_control_dl)
        self.add_out_port(self.output_radio_transport_dl)

        self.input_connected_ue_list = Port(EnableChannels, 'input_connected_ue_list')
        self.add_in_port(self.input_connected_ue_list)

        self.input_pss = Port(PrimarySynchronizationSignal, 'input_pss')
        self.add_in_port(self.input_pss)

        self.input_access_response = Port(ConnectResponse, 'input_access_response')
        self.input_disconnect_response = Port(DisconnectResponse, 'input_disconnect_response')
        self.input_ho_started = Port(HandOverStarted, 'input_ho_started')
        self.input_ho_finished = Port(HandOverFinished, 'input_ho_finished')
        self.output_rrc = Port(RadioResourceControl, 'output_rrc')
        self.output_access_request = Port(ConnectRequest, 'output_access_request')
        self.output_disconnect_request = Port(DisconnectRequest, 'output_disconnect_request')
        self.output_ho_ready = Port(HandOverReady, 'output_ho_ready')
        self.output_ho_response = Port(HandOverResponse, 'output_ho_response')
        self.add_in_port(self.input_access_response)
        self.add_in_port(self.input_disconnect_response)
        self.add_in_port(self.input_ho_started)
        self.add_in_port(self.input_ho_finished)
        self.add_out_port(self.output_rrc)
        self.add_out_port(self.output_access_request)
        self.add_out_port(self.output_disconnect_request)
        self.add_out_port(self.output_ho_ready)
        self.add_out_port(self.output_ho_response)

        self.input_to_radio_dl = Port(NetworkPacket, 'input_to_radio_dl')
        self.output_from_radio_ul = Port(NetworkPacket, 'output_from_radio_ul')
        self.add_in_port(self.input_to_radio_dl)
        self.add_out_port(self.output_from_radio_ul)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        self._check_new_ue_list()
        self._check_radio_control_ul()
        self._check_radio_transport_ul()
        self._check_signaling()
        self._check_access_control()
        self._check_transport()
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def _check_new_ue_list(self):
        if self.input_connected_ue_list:
            ue_list = self.input_connected_ue_list.get().slave_nodes
            self.ue_connected = ue_list

    def _check_radio_control_ul(self):
        for job in self.input_radio_control_ul.values:
            ue_id, network_msg = job.expanse_packet()
            ue_id, app_msg = network_msg.expanse_packet()
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
                elif isinstance(app_msg, ConnectRequest):
                    self.add_msg_to_queue(self.output_access_request, app_msg)
                else:
                    raise Exception("Unable to determine message type")

    def _check_radio_transport_ul(self):
        for job in self.input_radio_transport_ul.values:
            ue_id, network_msg = job.expanse_packet()
            if ue_id in self.ue_connected:
                if network_msg.node_to != self.ap_id:
                    self.add_msg_to_queue(self.output_from_radio_ul, network_msg)
                else:
                    raise Exception("Unable to determine message type")

    def _check_signaling(self):
        for msg in self.input_pss.values:
            self._add_app_msg_to_radio_bc(msg)

    def _check_access_control(self):
        for msg in self.input_access_response.values:
            self._add_app_msg_to_radio_control_dl(msg)
        for msg in self.input_disconnect_response.values:
            self._add_app_msg_to_radio_control_dl(msg)
        for msg in self.input_ho_started.values:
            self._add_app_msg_to_radio_control_dl(msg)
        for msg in self.input_ho_finished.values:
            self._add_app_msg_to_radio_control_dl(msg)

    def _check_transport(self):
        for msg in self.input_to_radio_dl.values:
            self._add_network_msg_to_radio_transport_dl(msg)

    def _add_app_msg_to_radio_bc(self, msg):
        network = NetworkPacket(self.ap_id, msg.ue_id, msg)
        phys = RadioPacket(self.ap_id, network.node_to, network)
        self.add_msg_to_queue(self.output_radio_bc, phys)

    def _add_app_msg_to_radio_control_dl(self, msg):
        network_to = msg.ue_id
        physical_to = msg.ue_id
        network = NetworkPacket(self.ap_id, network_to, msg)
        phys = RadioPacket(self.ap_id, physical_to, network)
        self.add_msg_to_queue(self.output_radio_control_dl, phys)

    def _add_network_msg_to_radio_transport_dl(self, msg: NetworkPacket):
        physical_to = msg.node_to
        phys = RadioPacket(self.ap_id, physical_to, msg)
        self.add_msg_to_queue(self.output_radio_transport_dl, phys)
