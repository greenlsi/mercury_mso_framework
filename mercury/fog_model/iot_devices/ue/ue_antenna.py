from xdevs.models import Port
from mercury.msg.network import RadioPacket, PhysicalPacket, NetworkPacket
from mercury.msg.network.packet.app_layer.ran import ConnectRequest, ConnectResponse, RadioResourceControl, \
    DisconnectRequest, DisconnectResponse, HandOverStarted, HandOverReady, HandOverFinished, HandOverResponse
from mercury.msg.iot_devices import ConnectedAccessPoint, ExtendedPSS
from ...common import ExtendedAtomic


class UserEquipmentAntenna(ExtendedAtomic):

    UL_MCS = 'ul_mcs_list'
    DL_MCS = 'dl_mcs_list'
    BANDWIDTH = 'bandwidth'

    def __init__(self, ue_id: str):
        """
        xDEVS module that models the behavior of a User Equipment antenna.

        :param ue_id: ID of the UE with the antenna
        """
        super().__init__(name='iot_devices_{}_antenna'.format(ue_id))
        self.ue_id = ue_id

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
        self.input_access_request = Port(ConnectRequest, 'input_access_request')
        self.input_disconnect_request = Port(DisconnectRequest, 'input_disconnect_request')
        self.input_rrc = Port(RadioResourceControl, 'input_rrc')
        self.input_ho_ready = Port(HandOverReady, 'input_ho_ready')
        self.input_ho_response = Port(HandOverResponse, 'input_ho_response')
        self.input_connected_ap = Port(ConnectedAccessPoint, 'input_connected_ap')
        self.input_antenna_powered = Port(bool, 'input_antenna_powered')
        self.output_pss = Port(ExtendedPSS, 'output_pss')
        self.output_access_response = Port(ConnectResponse, 'output_access_response')
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

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
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
        self.passivate() if self.msg_queue_empty() else self.activate()

    def _check_antenna_powered(self):
        if self.input_antenna_powered:
            self.powered = self.input_antenna_powered.get()

    def _check_connected_ap(self):
        if self.input_connected_ap:
            self.connected_ap = self.input_connected_ap.get().ap_id

    def _check_radio_control_dl(self):
        for job in self.input_radio_control_dl.values:
            ap_id, network_msg = job.expanse_packet()
            ap_id, app_msg = network_msg.expanse_packet()
            if ap_id == self.connected_ap:
                if isinstance(app_msg, HandOverStarted):
                    self.add_msg_to_queue(self.output_ho_started, app_msg)
                else:
                    raise Exception("Unable to determine message type")
            else:
                if isinstance(app_msg, HandOverFinished):
                    self.add_msg_to_queue(self.output_ho_finished, app_msg)
                elif isinstance(app_msg, DisconnectResponse):
                    self.add_msg_to_queue(self.output_disconnect_response, app_msg)
                elif isinstance(app_msg, ConnectResponse):
                    self.add_msg_to_queue(self.output_access_response, app_msg)
                else:
                    raise Exception("Unable to determine message type")

    def _check_radio_transport_dl(self):
        for job in self.input_radio_transport_dl.values:
            ap_id, network_msg = job.expanse_packet()
            # if ap_id == self.connected_ap:
            self.add_msg_to_queue(self.output_service, network_msg)

    def _check_radio_broadcast(self):
        for job in self.input_radio_bc.values:
            ap_id, network_msg = job.expanse_packet()
            ap_id, app_msg = network_msg.expanse_packet()
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
        network = NetworkPacket(self.ue_id, node_to, msg)
        msg = RadioPacket(node_from=self.ue_id, node_to=node_to, data=network)
        self.add_msg_to_queue(self.output_radio_control_ul, msg)

    def _add_network_msg_to_radio_transport_ul(self, msg):
        msg = RadioPacket(node_from=self.ue_id, node_to=self.connected_ap, data=msg)
        self.add_msg_to_queue(self.output_radio_transport_ul, msg)

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
