import logging
from math import ceil
from xdevs.models import Port, INFINITY
from ...common import FiniteStateMachine, logging_overhead
from .internal_interfaces import ServiceRequired, ConnectedAccessPoint, ExtendedPSS, AntennaPowered
from ...common.packet.apps.ran import RadioAccessNetworkConfiguration
from ...common.packet.apps.ran.ran_access import AccessRequest, AccessResponse, RadioResourceControl, \
    DisconnectRequest, DisconnectResponse
from ...common.packet.apps.ran.ran_handover import HandOverStarted, HandOverReady, HandOverFinished, \
    HandOverResponse

PHASE_DISCONNECTED = 'disconnected'
PHASE_TO_SNIFF = 'to_sniff'
PHASE_SNIFF = 'sniff'
PHASE_AWAIT_CONNECTION = 'await_connection'
PHASE_CONNECTED = 'connected_ap'
PHASE_AWAIT_HO = 'await_ho'
PHASE_AWAIT_DISCONNECTION = 'disconnect_request'

ACCESS_MANAGER_PHASES = [PHASE_DISCONNECTED, PHASE_TO_SNIFF, PHASE_SNIFF, PHASE_AWAIT_CONNECTION, PHASE_CONNECTED,
                         PHASE_AWAIT_HO, PHASE_AWAIT_DISCONNECTION]
LOGGING_OVERHEAD = ""


class AccessManager(FiniteStateMachine):
    """
    User Equipment network access_points_config manager xDEVS module

    :param str name: name of the xDEVS module
    :param str ue_id: ID of the User Equipment
    :param RadioAccessNetworkConfiguration rac_config: Radio Access Network configuration parameters
    """
    def __init__(self, name, ue_id, rac_config):
        # unwrap RAN configuration parameters
        self.header = rac_config.header
        self.signaling_window = rac_config.pss_period * 2 if rac_config.pss_period > 0 else 1
        self.rrc_period = rac_config.rrc_period
        self.timeout = rac_config.timeout

        self.ue_id = ue_id

        self.services_required = list()
        self.rrc_required = False
        self.potential_ap_id = None
        self.ap_id = None
        self.new_ap_id = None
        self.resource_list = dict()

        self.input_service_required = Port(ServiceRequired, 'input_service_required')
        self.input_pss = Port(ExtendedPSS, 'input_pss')
        self.input_access_response = Port(AccessResponse, 'input_access_response')
        self.input_disconnect_response = Port(DisconnectResponse, 'input_disconnect_response')
        self.input_ho_started = Port(HandOverStarted, 'input_ho_started')
        self.input_ho_finished = Port(HandOverFinished, 'input_ho_finished')
        self.output_access_request = Port(AccessRequest, 'output_access_request')
        self.output_disconnect_request = Port(DisconnectRequest, 'output_disconnect_request')
        self.output_rrc = Port(RadioResourceControl, 'output_rrc')
        self.output_ho_ready = Port(HandOverReady, 'output_ho_ready')
        self.output_ho_response = Port(HandOverResponse, 'output_ho_response')
        self.output_connected_ap = Port(ConnectedAccessPoint, 'output_connected_ap')
        self.output_antenna_powered = Port(AntennaPowered, 'output_antenna_powered')
        self.output_repeat_location = Port(str, 'output_repeat_location')

        # FSM stuff
        int_table = {
            PHASE_DISCONNECTED: self.internal_phase_disconnected,
            PHASE_TO_SNIFF: self.internal_phase_to_sniff,
            PHASE_SNIFF: self.internal_phase_sniff,
            PHASE_AWAIT_CONNECTION: self.internal_phase_await_connection,
            PHASE_CONNECTED: self.internal_phase_connected,
            PHASE_AWAIT_HO: self.internal_phase_await_ho,
            PHASE_AWAIT_DISCONNECTION: self.internal_phase_await_disconnection
        }
        ext_table = {
            PHASE_DISCONNECTED: self.external_phase_disconnected,
            PHASE_TO_SNIFF: self.external_phase_to_sniff,
            PHASE_SNIFF: self.external_phase_sniff,
            PHASE_AWAIT_CONNECTION: self.external_phase_await_connection,
            PHASE_CONNECTED: self.external_phase_connected,
            PHASE_AWAIT_HO: self.external_phase_await_ho,
            PHASE_AWAIT_DISCONNECTION: self.external_phase_await_disconnection
        }
        lambda_table = {
            PHASE_DISCONNECTED: None,
            PHASE_TO_SNIFF: None,
            PHASE_SNIFF: None,
            PHASE_AWAIT_CONNECTION: self.lambda_phase_await_connection,
            PHASE_CONNECTED: self.lambda_phase_connected,
            PHASE_AWAIT_HO: self.lambda_phase_await_ho,
            PHASE_AWAIT_DISCONNECTION: self.lambda_phase_await_disconnection
        }
        initial_state = PHASE_DISCONNECTED
        initial_timeout = INFINITY

        super().__init__(ACCESS_MANAGER_PHASES, int_table, ext_table,
                         lambda_table, initial_state, initial_timeout, name)

        self.add_in_port(self.input_service_required)
        self.add_in_port(self.input_pss)
        self.add_in_port(self.input_access_response)
        self.add_in_port(self.input_disconnect_response)
        self.add_in_port(self.input_ho_started)
        self.add_in_port(self.input_ho_finished)
        self.add_out_port(self.output_access_request)
        self.add_out_port(self.output_disconnect_request)
        self.add_out_port(self.output_rrc)
        self.add_out_port(self.output_ho_ready)
        self.add_out_port(self.output_ho_response)
        self.add_out_port(self.output_connected_ap)
        self.add_out_port(self.output_antenna_powered)
        self.add_out_port(self.output_repeat_location)

    @staticmethod
    def internal_phase_disconnected():
        return PHASE_DISCONNECTED, INFINITY

    def internal_phase_to_sniff(self):
        return PHASE_SNIFF, self.signaling_window

    def internal_phase_sniff(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        best_ap_id = self._find_best_ap()
        # CASE 1: UE detected a suitable AP
        if best_ap_id is not None:
            logging.info(overhead + "%s detected %s to be the optimal AP. Trying to connect" % (self.ue_id, best_ap_id))
            self.potential_ap_id = best_ap_id
            return PHASE_AWAIT_CONNECTION, 0
        # CASE 2: UE didn't detect any AP
        else:
            logging.info(overhead + "%s could not detect any AP. Waiting another time window" % self.ue_id)
            self.potential_ap_id = None
            return PHASE_SNIFF, self.signaling_window

    def internal_phase_await_connection(self):
        return PHASE_AWAIT_CONNECTION, self.timeout

    @staticmethod
    def internal_phase_connected():
        return PHASE_CONNECTED, INFINITY

    def internal_phase_await_ho(self):
        return PHASE_AWAIT_HO, self.timeout

    def internal_phase_await_disconnection(self):
        return PHASE_AWAIT_DISCONNECTION, self.timeout

    def external_phase_disconnected(self):
        self._check_connection_required()
        # In case connection is required, proceed to sniffing APs
        if self.services_required:
            overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
            logging.info(overhead + "%s requires to be connected. Proceeding to sniff APs" % self.ue_id)
            self.add_msg_to_queue(self.output_antenna_powered, AntennaPowered(True))
            self.add_msg_to_queue(self.output_repeat_location, self.ue_id)
            return PHASE_TO_SNIFF, 0

    def external_phase_to_sniff(self):
        self._check_connection_required()

    def external_phase_sniff(self):
        self._check_connection_required()
        # If connection is no longer required, go back to disconnected
        if not self.services_required:
            overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
            logging.info(overhead + "%s does not require to be connected. Keeping disconnected" % self.ue_id)
            self.resource_list = dict()
            return PHASE_DISCONNECTED, INFINITY
        # Otherwise, just refresh resource list and wait until signaling window times out
        self._refresh_resource_list()

    def external_phase_await_connection(self):
        self._check_connection_required()
        self._refresh_resource_list()
        if self.input_access_response:
            job = self.input_access_response.get()
            ap_id = job.ap_id
            assert ap_id == self.potential_ap_id
            response = job.response
            overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
            logging.info(overhead + "%s<---%s: Access response: %s" % (self.ue_id, ap_id, response))
            # CASE 1: access_points_config request succeeded
            if response:
                self.potential_ap_id = None
                self.ap_id = ap_id
                self.add_msg_to_queue(self.output_connected_ap, ConnectedAccessPoint(self.ap_id))
                if self.services_required:
                    return PHASE_CONNECTED, 0
                else:
                    logging.info(overhead + "    UE does not require to be connected. Disconnecting")
                    return PHASE_AWAIT_DISCONNECTION, 0
            # CASE 2: access_points_config request failed.
            else:
                # CASE 2.1: Connection is no longer required
                if not self.services_required:
                    logging.info(overhead + "%s does not require to be connected. Keeping disconnected" % self.ue_id)
                    self.potential_ap_id = None
                    self.resource_list = dict()
                    return PHASE_DISCONNECTED, INFINITY
                # CASE 2.2: Connection is still required
                else:
                    next_state, sigma = self.internal_phase_sniff()
                    if next_state == PHASE_AWAIT_CONNECTION:
                        sigma = self.timeout
                    return next_state, sigma

    def external_phase_connected(self):
        self._check_connection_required()
        self._refresh_resource_list()
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        # CASE 1: Connection is no longer required
        if not self.services_required:
            logging.info(overhead + "%s does not require to be connected. Disconnecting" % self.ue_id)
            self.add_msg_to_queue(self.output_connected_ap, ConnectedAccessPoint(None))
            return PHASE_AWAIT_DISCONNECTION, 0
        # CASE 2: Handover process is about to start
        elif self.input_ho_started:
            job = self.input_ho_started.get()
            ap_id = job.ap_from
            assert ap_id == self.ap_id
            new_ap_id = job.ap_to
            logging.info(overhead + "%s<--%s: handover to AP %s started." % (self.ue_id, ap_id, new_ap_id))
            self.new_ap_id = new_ap_id
            self.add_msg_to_queue(self.output_connected_ap, ConnectedAccessPoint(None))
            return PHASE_AWAIT_HO, 0
        # CASE 3: New RRC message is required
        elif self.rrc_required:
            sigma = self._next_connected_sigma()
            return PHASE_CONNECTED, sigma

    def external_phase_await_ho(self):
        self._check_connection_required()
        self._refresh_resource_list()
        # CASE 1: Handover process finished
        if self.input_ho_finished:
            overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
            job = self.input_ho_finished.get()
            new_ap_id = job.ap_to
            assert new_ap_id == self.new_ap_id
            prev_ap_id = job.ap_from
            assert prev_ap_id == self.ap_id
            response = job.response
            logging.info(overhead + "%s<---%s: Handover from AP %s response: %s" % (self.ue_id, new_ap_id, prev_ap_id,
                                                                                    response))
            if response:
                self.ap_id = new_ap_id
            self.new_ap_id = None
            # Send handover response message to previous AP
            msg = HandOverResponse(self.ue_id, prev_ap_id, new_ap_id, response, self.header)
            self.add_msg_to_queue(self.output_ho_response, msg)
            # CASE 1.1: connection is still required. going back to connected_ap
            if self.services_required:
                self.add_msg_to_queue(self.output_connected_ap, ConnectedAccessPoint(self.ap_id))
                return PHASE_CONNECTED, 0
            # CASE 1.2: Connection is no longer required. Going to await disconnection
            else:
                return PHASE_AWAIT_DISCONNECTION, 0

    def external_phase_await_disconnection(self):
        self._check_connection_required()
        self._refresh_resource_list()
        if self.input_disconnect_response:
            job = self.input_disconnect_response.get()
            ap_id = job.ap_id
            response = job.response
            overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
            logging.info(overhead + "%s<---%s: Disconnect response: %s" % (self.ue_id, ap_id, response))
            # CASE 1: disconnect request succeeded
            if response:
                self.ap_id = None
                # CASE 1.1: connection is required
                if self.services_required:
                    logging.info(overhead + "    UE does requires to be connected. Connecting")
                    next_state, sigma = self.internal_phase_sniff()
                    if next_state == PHASE_AWAIT_CONNECTION:
                        sigma = self.timeout
                    return next_state, sigma
                # CASE 1.2: connection is no longer required
                else:
                    self.resource_list = dict()
                    self.add_msg_to_queue(self.output_antenna_powered, AntennaPowered(False))
                    return PHASE_DISCONNECTED, 0
            # CASE 2: access_points_config request failed.
            else:
                # CASE 2.1: connection is not required
                if not self.services_required:
                    return PHASE_AWAIT_DISCONNECTION, self.timeout
                # CASE 2.2: connection is required
                else:
                    return PHASE_CONNECTED, 0

    def lambda_phase_await_connection(self):
        self.add_msg_to_queue(self.output_access_request, AccessRequest(self.ue_id, self.potential_ap_id, self.header))

    def lambda_phase_await_disconnection(self):
        self.add_msg_to_queue(self.output_disconnect_request, DisconnectRequest(self.ue_id, self.ap_id, self.header))

    def lambda_phase_connected(self):
        if self.rrc_required:
            resource_list = {ap_id: snr for ap_id, snr in self.resource_list.items()}
            msg = RadioResourceControl(self.ue_id, self.ap_id, resource_list, self.header)
            self.add_msg_to_queue(self.output_rrc, msg)
        self.rrc_required = False

    def lambda_phase_await_ho(self):
        self.add_msg_to_queue(self.output_ho_ready, HandOverReady(self.ue_id, self.new_ap_id, self.ap_id, self.header))

    def _find_best_ap(self):
        """Returns the ID of the detected AP which offers the best quality of signal"""
        # CASE 1: No AP PSS were detected
        if not self.resource_list:
            return None
        # CASE 2: At least one AP is in resource list
        resource_list = [(ap_id, snr) for ap_id, snr in self.resource_list.items()]
        resource_list.sort(reverse=True, key=lambda x: x[1])
        return resource_list[0][0]

    def _refresh_resource_list(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        if self.input_pss:
            self.rrc_required = True
            for job in self.input_pss.values:
                logging.info(overhead + '%s<---%s: PSS message' % (self.ue_id, job.ap_id))
                self.resource_list[job.ap_id] = job.snr

    def _check_connection_required(self):
        for job in self.input_service_required.values:
            service_id = job.service_id
            required = job.required
            if not required:
                if service_id in self.services_required:
                    self.services_required.remove(service_id)
            elif service_id not in self.services_required:
                self.services_required.append(service_id)

    def _next_connected_sigma(self):
        if self.rrc_period == 0:
            return 0
        else:
            return ceil(self._clock / self.rrc_period) * self.rrc_period - self._clock
