import logging
from xdevs.models import Port
from ...common import Stateless, logging_overhead
from ...common.packet.application.ran import RadioAccessNetworkConfiguration
from ...common.packet.application.ran.ran_access import AccessRequest, AccessResponse, RadioResourceControl
from ...common.packet.application.ran.ran_access import DisconnectRequest, DisconnectResponse
from ...common.packet.application.ran.ran_access_control import CreatePathRequest, RemovePathRequest, SwitchPathRequest
from ...common.packet.application.ran.ran_access_control import CreatePathResponse, RemovePathResponse, SwitchPathResponse
from ...common.packet.application.ran.ran_handover import StartHandOverRequest, StartHandOverResponse
from ...common.packet.application.ran.ran_handover import HandOverStarted, HandOverReady, HandOverFinished, HandOverResponse
from .internal_interfaces import ConnectedUEList


UE_CONNECTING = 'ue_connecting'
UE_HANDOVER_FROM = 'ue_ho_from'
UE_HANDOVER_READY = 'ue_ho_ready'
UE_CONNECTED = 'ue_connected'
UE_HANDOVER_TO = 'ue_ho_to'
UE_DISCONNECTING = 'ue_disconnecting'

LOGGING_FROM_CROSSHAUL = "    "
LOGGING_FROM_UE = ""


class AccessAndControl(Stateless):
    """
    Access and Control block of Access Points
    :param str name: name of the xDEVS module
    :param str ap_id: ID of the AP
    :param RadioAccessNetworkConfiguration ran_config:
    """
    def __init__(self, name, ap_id, rac_config):
        super().__init__(name=name)

        # inputs/outputs to UEs
        self.input_access_request = Port(AccessRequest, name + '_input_access_request')
        self.input_disconnect_request = Port(DisconnectRequest, name + '_input_disconnect_request')
        self.input_rrc = Port(RadioResourceControl, name + '_input_rrc')
        self.input_ho_ready = Port(HandOverReady, name + '_input_ho_ready')
        self.input_ho_response = Port(HandOverResponse, name + '_input_ho_response')
        self.output_access_response = Port(AccessResponse, name + '_output_access_response')
        self.output_disconnect_response = Port(DisconnectResponse, name + '_output_disconnect_response')
        self.output_ho_started = Port(HandOverStarted, name + '_output_ho_started')
        self.output_ho_finished = Port(HandOverFinished, name + '_output_ho_finished')
        self.add_in_port(self.input_access_request)
        self.add_in_port(self.input_disconnect_request)
        self.add_in_port(self.input_rrc)
        self.add_in_port(self.input_ho_ready)
        self.add_in_port(self.input_ho_response)
        self.add_out_port(self.output_access_response)
        self.add_out_port(self.output_disconnect_response)
        self.add_out_port(self.output_ho_started)
        self.add_out_port(self.output_ho_finished)

        # inputs/outputs to APs
        self.input_start_ho_request = Port(StartHandOverRequest, name + '_input_start_ho_request')
        self.input_start_ho_response = Port(StartHandOverResponse, name + '_input_start_ho_response')
        self.output_start_ho_request = Port(StartHandOverRequest, name + '_output_start_ho_request')
        self.output_start_ho_response = Port(StartHandOverResponse, name + '_output_start_ho_response')
        self.add_in_port(self.input_start_ho_request)
        self.add_in_port(self.input_start_ho_response)
        self.add_out_port(self.output_start_ho_request)
        self.add_out_port(self.output_start_ho_response)

        # inputs/outputs for core network
        self.output_create_path_request = Port(CreatePathRequest, name + '_output_create_path_request')
        self.output_remove_path_request = Port(RemovePathRequest, name + '_output_remove_path_request')
        self.output_switch_path_request = Port(SwitchPathRequest, name + '_output_switch_path_request')
        self.input_create_path_response = Port(CreatePathResponse, name + '_input_create_path_response')
        self.input_remove_path_response = Port(RemovePathResponse, name + '_input_remove_path_response')
        self.input_switch_path_response = Port(SwitchPathResponse, name + '_input_switch_path_response')
        self.add_out_port(self.output_create_path_request)
        self.add_out_port(self.output_remove_path_request)
        self.add_out_port(self.output_switch_path_request)
        self.add_in_port(self.input_create_path_response)
        self.add_in_port(self.input_remove_path_response)
        self.add_in_port(self.input_switch_path_response)

        # AP internal inputs/outputs
        self.output_connected_ue_list = Port(ConnectedUEList, name + '_output_connected_ue_list')
        self.add_out_port(self.output_connected_ue_list)

        self.ap_id = ap_id                  # AP ID
        self.header = rac_config.header     # Header for application packets
        self.ue_path = dict()               # dictionary {UE ID: UE status}
        self.ue_to_ho_to = dict()           # dictionary of connected_ap UE to be handed over {node_id: new_ap_id}
        self.ue_to_ho_from = dict()         # dictionary of UE to be connected_ap via hand over {node_id: prev_ap_id}

    def check_in_ports(self):
        self._process_access_messages()
        self._process_handover_messages()

    def _process_access_messages(self):
        overhead_xh = logging_overhead(self._clock, LOGGING_FROM_CROSSHAUL)
        overhead_ue = logging_overhead(self._clock, LOGGING_FROM_UE)
        # Process Create path responses from AMF
        for job in self.input_create_path_response.values:
            self.__process_create_path_response(job, overhead_xh)
        # Process remove path responses from AMF
        for job in self.input_remove_path_response.values:
            self.__process_remove_path_response(job, overhead_xh)
        # Process switch path responses from AMF
        for job in self.input_switch_path_response.values:
            self.__process_switch_path_response(job, overhead_xh)
        # handle UEs' pxcch requests
        for job in self.input_access_request.values:
            self.__process_access_request(job, overhead_ue)
        # handle UEs' disconnect requests
        for job in self.input_disconnect_request.values:
            self.__process_disconnect_request(job, overhead_ue)
        # handle UEs' radio resource control messages
        for job in self.input_rrc.values:
            self.__process_rrc_msg(job, overhead_ue)

    def _process_handover_messages(self):
        overhead_xh = logging_overhead(self._clock, LOGGING_FROM_CROSSHAUL)
        overhead_ue = logging_overhead(self._clock, LOGGING_FROM_UE)
        # process other AP's start handover messages
        for job in self.input_start_ho_request.values:
            self._process_start_ho_request(job, overhead_xh)
        # process other AP's start handover response messages
        for job in self.input_start_ho_response.values:
            self._process_start_ho_response(job, overhead_xh)
        # handle UEs' handover ready messages
        for job in self.input_ho_ready.values:
            self._process_ue_ready(job, overhead_ue)
        # handle UEs' handover response messages
        for job in self.input_ho_response.values:
            self._process_ue_ho_response(job, overhead_ue)

    def __process_create_path_response(self, job, overhead):
        """
        Process AMF response regarding UEs service requests.
        :param CreatePathResponse job: AMF's Create Path response message
        :param str overhead: logging overhead
        """
        ue_id = job.ue_id
        response = job.response
        logging.info(overhead + '%s<---AMF: Create Path for %s response: %s' % (self.ap_id, ue_id, response))
        # If service request succeeded, add UE to connected_ap list and send to transport module new UE message
        assert self.ue_path.pop(ue_id) == UE_CONNECTING
        if response:
            self.ue_path[ue_id] = UE_CONNECTED
            self.__send_connected_ue_list()
        self.add_msg_to_queue(self.output_access_response, AccessResponse(self.ap_id, ue_id, response, self.header))

    def __process_remove_path_response(self, job, overhead):
        """
        Process AMF response regarding UEs disconnect requests.
        :param RemovePathResponse job: AMF's Remove Path response message
        :param str overhead: logging overhead
        """
        ue_id = job.ue_id
        response = job.response
        logging.info(overhead + '%s<---AMF: Remove Path for %s response: %s' % (self.ap_id, ue_id, response))
        # If disconnect request succeeded, add UE to connected_ap list and send to transport module new UE message
        assert self.ue_path.pop(ue_id) == UE_DISCONNECTING
        if response:
            self.__send_connected_ue_list()
        else:
            self.ue_path[ue_id] = UE_CONNECTED
        self.add_msg_to_queue(self.output_disconnect_response, DisconnectResponse(self.ap_id, ue_id, response,
                                                                                   self.header))

    def __process_switch_path_response(self, job, overhead):
        """
        Process switch path responses from AMF
        :param SwitchPathResponse job: switch Path Response message to be processed
        :param str overhead: logging overhead
        """
        ue_id = job.ue_id
        response = job.response
        assert self.ue_path.pop(ue_id) == UE_HANDOVER_READY
        logging.info(overhead + '%s<---AMF Switch Path %s response: %s' % (self.ap_id, ue_id, response))
        if response:
            self.ue_path[ue_id] = UE_CONNECTED
            self.__send_connected_ue_list()
        msg = HandOverFinished(self.ap_id, ue_id, self.ue_to_ho_from[ue_id], response, self.header)
        self.add_msg_to_queue(self.output_ho_finished, msg)

    def __process_access_request(self, job, overhead):
        """
        Process pxcch requests messages from UEs
        :param AccessRequest job: Access Request message
        :param str overhead: logging overhead
        """
        ue_id = job.ue_id
        logging.info(overhead + '%s--->%s: Access request' % (ue_id, self.ap_id))
        # If UE is already connected_ap, send affirmative response
        if ue_id in self.ue_path:
            if self.ue_path[ue_id] == UE_CONNECTED:
                msg = AccessResponse(self.ap_id, ue_id, True, self.header)
                self.add_msg_to_queue(self.output_access_response, msg)
            else:
                logging.warning(overhead + '    UE has state %s. Ignoring Service request' % self.ue_path[ue_id])
        # Else, if UE is not to be connected_ap, send connection request to AMF
        else:
            self.ue_path[ue_id] = UE_CONNECTING
            msg = CreatePathRequest(self.ap_id, ue_id, self.header)
            self.add_msg_to_queue(self.output_create_path_request, msg)

    def __process_disconnect_request(self, job, overhead):
        """
        Process disconnect requests from UEs
        :param DisconnectRequest job: disconnect request message
        :param str overhead: logging overhead
        """
        ue_id = job.ue_id
        logging.info(overhead + '%s--->%s: disconnect request' % (ue_id, self.ap_id))
        # If UE is already disconnected, send affirmative response
        if ue_id not in self.ue_path:
            logging.warning(overhead + '    UE is not connected_ap. Sending affirmative response')
            msg = DisconnectResponse(self.ap_id, ue_id, True, self.header)
            self.add_msg_to_queue(self.output_disconnect_response, msg)
        elif self.ue_path[ue_id] == UE_CONNECTED:
            self.ue_path[ue_id] = UE_DISCONNECTING
            msg = RemovePathRequest(self.ap_id, ue_id, self.header)
            self.add_msg_to_queue(self.output_remove_path_request, msg)
        else:
            logging.warning(overhead + '    UE has state %s. Ignoring Service request' % self.ue_path[ue_id])

    def __process_rrc_msg(self, job, overhead):
        """
        Process UE Radio Resource Control messages and determine whether a HO is required or not.
        :param RadioResourceControl job: incoming Radio Resource Control message
        :param str overhead: logging overhead
        """
        ue_id = job.ue_id
        logging.info(overhead + '%s--->%s: RRC message' % (ue_id, self.ap_id))
        if ue_id not in self.ue_path:
            logging.warning(overhead + '    UE is not in routing path. Ignoring RRC message.')
        elif self.ue_path[ue_id] == UE_CONNECTED:
            # Sort resource list and check which AP has more SNR
            resource_list = [(ap_id, snr) for ap_id, snr in job.rrc_list.items()]
            resource_list.sort(reverse=True, key=lambda x: x[1])
            best_ap_id = resource_list[0][0]
            # If the best AP is not self, starts handover process
            if best_ap_id != self.ap_id:
                self.ue_path[ue_id] = UE_HANDOVER_TO
                self.ue_to_ho_to[ue_id] = best_ap_id
                msg = StartHandOverRequest(self.ap_id, best_ap_id, ue_id, self.header)
                self.add_msg_to_queue(self.output_start_ho_request, msg)
        else:
            logging.warning(overhead + '    UE has state %s. Ignoring RRC message' % self.ue_path[ue_id])

    def _process_start_ho_request(self, job, overhead):
        """
        Process incoming Start HO request messages.
        :param StartHandOverRequest job: start handover request message
        :param str overhead: logging overhead
        """
        ap_from = job.ap_from
        ue_id = job.ue_id
        logging.info(overhead + '%s->%s Handover request %s' % (ap_from, self.ap_id, ue_id))
        # Insert UE to be HO'd to ue_to_ho_from list; session and ready flags are set to False
        self.ue_path[ue_id] = UE_HANDOVER_FROM
        self.ue_to_ho_from[ue_id] = ap_from
        msg = StartHandOverResponse(self.ap_id, ap_from, ue_id, True, self.header)
        self.add_msg_to_queue(self.output_start_ho_response, msg)

    def _process_start_ho_response(self, job, overhead):
        """
        Process AP handover response messages.
        :param StartHandOverResponse job: Start Handover Response from AP
        :param str overhead: logging overhead
        """
        ue_id = job.ue_id
        new_ap_id = job.ap_to
        response = job.response
        assert self.ue_path[ue_id] == UE_HANDOVER_TO
        assert new_ap_id == self.ue_to_ho_to[ue_id]
        logging.info(overhead + '%s->%s start handover %s response: %s' % (new_ap_id, self.ap_id, ue_id, response))
        if response:
            msg = HandOverStarted(self.ap_id, ue_id, new_ap_id, self.header)
            self.add_msg_to_queue(self.output_ho_started, msg)
        else:
            self.ue_path[ue_id] = UE_CONNECTED
            self.ue_to_ho_to.pop(ue_id)

    def _process_ue_ready(self, msg, overhead):
        """
        Process incoming UE handover ready messages.
        :param HandOverReady msg: UE Handover Ready message
        :param str overhead: logging overhead
        """
        ue_id = msg.ue_id
        logging.info(overhead + '%s--->%s: HO Ready' % (ue_id, self.ap_id))
        assert self.ue_path[ue_id] == UE_HANDOVER_FROM
        self.ue_path[ue_id] = UE_HANDOVER_READY
        msg = SwitchPathRequest(self.ap_id, ue_id, self.ue_to_ho_from[ue_id], self.header)
        self.add_msg_to_queue(self.output_switch_path_request, msg)

    def _process_ue_ho_response(self, job, overhead):
        """
        Process UE handover response messages and finishes with handover process.
        :param HandOverResponse job: UE handover response message.
        :param str overhead: logging overhead
        """
        ue_id = job.ue_id
        prev_ap_id = job.ap_from
        new_ap_id = job.ap_to
        response = job.response
        logging.info(overhead + '%s--->%s: handover to %s response: %s' %(ue_id, self.ap_id, new_ap_id, response))
        assert prev_ap_id == self.ap_id
        assert self.ue_path.pop(ue_id) == UE_HANDOVER_TO
        assert self.ue_to_ho_to.pop(ue_id) == new_ap_id
        if not response:
            self.ue_path[ue_id] = UE_CONNECTED
        else:
            self.__send_connected_ue_list()

    def __send_connected_ue_list(self):
        """Sends list of connected_ap UEs"""
        connected_states = [UE_CONNECTED, UE_DISCONNECTING, UE_HANDOVER_TO]
        ue_list = [ue for ue, status in self.ue_path.items() if status in connected_states]
        self.add_msg_to_queue(self.output_connected_ue_list, ConnectedUEList(ue_list))

    def process_internal_messages(self):
        pass
