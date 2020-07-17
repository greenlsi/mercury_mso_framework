import logging
from collections import deque
from xdevs.models import Port, INFINITY
from ....common import FiniteStateMachine, logging_overhead
from ..internal_interfaces import ServiceRequired, ConnectedAccessPoint
from ....common.packet.packet import NetworkPacket, NetworkPacketConfiguration
from ....common.packet.apps.service import ServiceConfiguration, ServiceDelayReport, CreateSessionRequestPacket,\
    CreateSessionResponsePacket, RemoveSessionRequestPacket, RemoveSessionResponsePacket, OngoingSessionRequestPacket, \
    OngoingSessionResponsePacket, GetDataCenterRequest, GetDataCenterResponse

PHASE_SESSION_CLOSED = "session_closed"
PHASE_NOTIFY_SERVICE_REQUIRED = "notify_service_required"
PHASE_AWAIT_DC = "await_dc"
PHASE_AWAIT_OPEN_SESSION = "await_open_session"
PHASE_SESSION_OPENED = "session_opened"
PHASE_AWAIT_CLOSE_SESSION = "await_close_session"
PHASE_NOTIFY_SERVICE_NOT_REQUIRED = "notify_service_not_required"
SESSION_MANAGER_PHASES = [PHASE_SESSION_CLOSED, PHASE_NOTIFY_SERVICE_REQUIRED, PHASE_AWAIT_DC, PHASE_AWAIT_OPEN_SESSION,
                          PHASE_SESSION_OPENED, PHASE_AWAIT_CLOSE_SESSION, PHASE_NOTIFY_SERVICE_NOT_REQUIRED]

LOGGING_OVERHEAD = ""

DATA = "data"
INITIAL_CLOCK = "initial_clock"
TIMES_SENT = "times_sent"
FIRST_TIME_SENT = "first_time_sent"
ACKNOWLEDGED = "acknowledged"
NEXT_TIMEOUT = "next_timeout"


class ServiceSessionManager(FiniteStateMachine):
    def __init__(self, name: str, ue_id: str, service_config: ServiceConfiguration,
                 network_config: NetworkPacketConfiguration, t_initial: float, lite_id: str = None):
        """
        Service Session Manager xDEVS module

        :param name: name of the xDEVS module
        :param ue_id: User Equipment ID
        :param service_config: service configuration
        :param network_config: network configuration
        :param t_initial: initial back off time before creating the first package
        """
        # unwrap configuration parameters
        self.service_id = service_config.service_id
        self.ue_id = ue_id
        self.service_header = service_config.header
        self.min_closed_t = service_config.min_closed_t
        self.min_open_t = service_config.min_open_t
        self.service_timeout = service_config.service_timeout
        self.network_header = network_config.header

        self.window_size = service_config.window_size
        self.labeling_pointer = 0
        self.data_buffer = deque()
        self.request_buffer = deque()

        self.connected_ap = lite_id
        self.dc_id = None

        self.next_timeout = 0
        self.min_timeout = max(self.min_closed_t, t_initial)

        # FSM stuff
        int_table = {
            PHASE_SESSION_CLOSED: self.internal_phase_session_closed,
            PHASE_NOTIFY_SERVICE_REQUIRED: self.internal_phase_notify_service_required,
            PHASE_AWAIT_DC: self.internal_phase_await_dc,
            PHASE_AWAIT_OPEN_SESSION: self.internal_phase_to_open_session,
            PHASE_SESSION_OPENED: self.internal_phase_session_opened,
            PHASE_AWAIT_CLOSE_SESSION: self.internal_phase_to_close_session,
            PHASE_NOTIFY_SERVICE_NOT_REQUIRED: self.internal_phase_notify_service_not_required
        }
        ext_table = {
            PHASE_SESSION_CLOSED: self.external_phase_session_closed,
            PHASE_NOTIFY_SERVICE_REQUIRED: self.external_phase_notify_service_required,
            PHASE_AWAIT_DC: self.external_phase_await_dc,
            PHASE_AWAIT_OPEN_SESSION: self.external_phase_await_open_session,
            PHASE_SESSION_OPENED: self.external_phase_session_opened,
            PHASE_AWAIT_CLOSE_SESSION: self.external_phase_await_close_session,
            PHASE_NOTIFY_SERVICE_NOT_REQUIRED: self.external_phase_notify_service_not_required
        }
        lambda_table = {
            PHASE_SESSION_CLOSED: self.lambda_phase_session_closed,
            PHASE_NOTIFY_SERVICE_REQUIRED: self.lambda_phase_notify_service_required,
            PHASE_AWAIT_DC: self.lambda_phase_to_await_dc,
            PHASE_AWAIT_OPEN_SESSION: self.lambda_phase_to_open_session,
            PHASE_SESSION_OPENED: self.lambda_phase_opened_session,
            PHASE_AWAIT_CLOSE_SESSION: self.lambda_phase_to_close_session,
            PHASE_NOTIFY_SERVICE_NOT_REQUIRED: self.lambda_phase_notify_service_not_required
        }
        initial_state = PHASE_SESSION_CLOSED
        initial_timeout = INFINITY

        super().__init__(SESSION_MANAGER_PHASES, int_table, ext_table, lambda_table, initial_state, initial_timeout)

        self.input_session_request = Port(OngoingSessionRequestPacket, name + '_input_ongoing_session_request')
        self.input_network = Port(NetworkPacket, name + '_input_network')
        self.output_network = Port(NetworkPacket, name + '_output_network')
        self.output_service_delay_report = Port(ServiceDelayReport, name + '_output_service_delay_report')
        self.add_in_port(self.input_session_request)
        self.add_in_port(self.input_network)
        self.add_out_port(self.output_network)
        self.add_out_port(self.output_service_delay_report)

        self.input_connected_ap = Port(ConnectedAccessPoint, name + '_input_connected_ap')
        self.output_service_required = Port(ServiceRequired, name + '_output_service_required')
        self.add_in_port(self.input_connected_ap)
        self.add_out_port(self.output_service_required)

    def internal_phase_session_closed(self):
        # CASE 1: UE is not connected to the RAN
        if self.connected_ap is None:
            return PHASE_SESSION_CLOSED, INFINITY
        # CASE 2: UE is connected but data buffer is empty
        elif not self.data_buffer:
            return PHASE_SESSION_CLOSED, INFINITY
        # CASE 3: UE is connected and data buffer is not empty BUT minimum timeout has not expired yet
        elif self._clock < self.min_timeout:
            return PHASE_SESSION_CLOSED, max(0, self.min_timeout - self._clock)
        # CASE 4: UE is connected, data buffer is not empty AND minimum timeout has expired
        else:
            return PHASE_NOTIFY_SERVICE_REQUIRED, 0

    def internal_phase_notify_service_required(self):
        # CASE 1: UE is not connected to the RAN
        if self.connected_ap is None:
            return PHASE_AWAIT_DC, INFINITY
        # CASE 2: UE is connected to the RAN
        else:
            self.next_timeout = self._clock
            return PHASE_AWAIT_DC, 0

    def internal_phase_await_dc(self):
        # CASE 1: UE is not connected to the RAN
        if self.connected_ap is None:
            return PHASE_AWAIT_DC, INFINITY
        # CASE 2: UE is connected to the RAN
        else:
            # If timeout has been triggered, actualize it
            if self._clock >= self.next_timeout:
                self.next_timeout = self._clock + self.service_timeout
            return PHASE_AWAIT_DC, max(0, self.next_timeout - self._clock)

    def internal_phase_to_open_session(self):
        # CASE 1: UE is not connected to the RAN
        if self.connected_ap is None:
            return PHASE_AWAIT_OPEN_SESSION, INFINITY
        # CASE 2: UE is connected to the RAN
        else:
            # If timeout has been triggered, actualize it
            if self._clock >= self.next_timeout:
                self.next_timeout = self._clock + self.service_timeout
            return PHASE_AWAIT_OPEN_SESSION, max(0, self.next_timeout - self._clock)

    def internal_phase_session_opened(self):
        # CASE 1: UE is not connected to the RAN
        if self.connected_ap is None:
            return PHASE_SESSION_OPENED, INFINITY
        # CASE 2: UE is connected to the RAN but no data is to be sent
        elif not (self.data_buffer or self.request_buffer):
            # CASE 2.1: minimum timeout has NOT expired yet
            if self._clock < self.min_timeout:
                return PHASE_SESSION_OPENED, max(0, self.min_timeout - self._clock)
            # CASE 2.2: minimum timeout has expired
            else:
                self.next_timeout = self._clock
                return PHASE_AWAIT_CLOSE_SESSION, 0
        # CASE 3: UE is connected to the RAN and data needs to be sent
        else:
            return PHASE_SESSION_OPENED, self._compute_next_timeout()

    def internal_phase_to_close_session(self):
        # CASE 1: UE is not connected to the RAN
        if self.connected_ap is None:
            return PHASE_AWAIT_OPEN_SESSION, INFINITY
        # CASE 2: UE is connected to the RAN
        else:
            # If timeout has been triggered, actualize it
            if self._clock >= self.next_timeout:
                self.next_timeout = self._clock + self.service_timeout
            return PHASE_AWAIT_CLOSE_SESSION, max(0, self.next_timeout - self._clock)

    def internal_phase_notify_service_not_required(self):
        self.min_timeout = self._clock + self.min_closed_t
        # CASE 1: UE is not connected to the RAN
        if self.connected_ap is None:
            return PHASE_SESSION_CLOSED, INFINITY
        # CASE 2: UE is connected but data buffer is empty
        elif not self.data_buffer:
            return PHASE_SESSION_CLOSED, INFINITY
        # CASE 3: UE is connected and data buffer is not empty BUT minimum timeout has not expired yet
        else:
            return PHASE_SESSION_CLOSED, max(0, self.min_timeout - self._clock)

    def external_phase_session_closed(self):
        self._get_connected_ap()
        self._get_new_data_packet()
        if self.data_buffer:
            if self._clock < self.min_timeout:
                return PHASE_SESSION_CLOSED, max(self.min_timeout - self._clock, 0)
            else:
                return PHASE_NOTIFY_SERVICE_REQUIRED, 0

    def external_phase_notify_service_required(self):
        self._get_connected_ap()
        self._get_new_data_packet()

    def external_phase_await_dc(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        prev_ap = self.connected_ap
        self._get_connected_ap()
        self._get_new_data_packet()
        for job in self.input_network.values:
            node_from, msg = self.__expand_network_message(job)
            if isinstance(msg, GetDataCenterResponse):
                self.dc_id = msg.dc_id
                logging.info(overhead + '%s %s\'s requests to be processed at %s' % (self.ue_id, self.service_id,
                                                                                     self.dc_id))
                self.next_timeout = self._clock + self.service_timeout
                return PHASE_AWAIT_OPEN_SESSION, 0
        if prev_ap != self.connected_ap:
            return PHASE_AWAIT_DC, 0

    def external_phase_await_open_session(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        prev_ap = self.connected_ap
        self._get_connected_ap()
        self._get_new_data_packet()
        for job in self.input_network.values:
            node_from, msg = self.__expand_network_message(job)
            if isinstance(msg, CreateSessionResponsePacket):
                assert node_from == self.dc_id
                service_id = msg.service_id
                response = msg.response
                logging.info(overhead + "%s received create session %s response: %s" % (self.ue_id, service_id,
                                                                                        response))
                if response:
                    self.min_timeout = self._clock + self.min_open_t
                    return PHASE_SESSION_OPENED, 0
                else:
                    logging.warning(overhead + "    Create session failed. waiting until timeout and trying again...")
        if prev_ap != self.connected_ap:
            return PHASE_AWAIT_OPEN_SESSION, 0

    def external_phase_session_opened(self):
        prev_ap = self.connected_ap
        self._get_connected_ap()
        self._get_new_data_packet()
        clean = self._clean_request_buffer()
        # CASE 1: there is data waiting to be sent and request buffer is not full
        if clean or (self.data_buffer and len(self.request_buffer) < self.window_size):
            return PHASE_SESSION_OPENED, 0
        # CASE 2: both data buffers are empty
        elif not (self.data_buffer or self.request_buffer):
            # CASE 2.1: minimum time with opened session has not been met yet
            if self._clock >= self.min_timeout:
                return PHASE_SESSION_OPENED, self.next_timeout - self._clock
            # CASE 2.2: everything OK. proceed to close the session
            else:
                self.next_timeout = self._clock
                return PHASE_AWAIT_CLOSE_SESSION, 0
        if prev_ap != self.connected_ap:
            return PHASE_SESSION_OPENED, 0

    def external_phase_await_close_session(self):
        prev_ap = self.connected_ap
        self._get_connected_ap()
        self._get_new_data_packet()
        for job in self.input_network.values:
            node_from, msg = self.__expand_network_message(job)
            if isinstance(msg, RemoveSessionResponsePacket):
                overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
                service_id = msg.service_id
                response = msg.response
                logging.info(overhead + "%s received remove session %s response: %s" % (self.ue_id, service_id,
                                                                                        response))
                if msg.response:
                    self.dc_id = None
                    return PHASE_NOTIFY_SERVICE_NOT_REQUIRED, 0
                else:
                    logging.warning(overhead + "    Remove session failed. waiting until timeout and trying again...")
        if prev_ap != self.connected_ap:
            return PHASE_AWAIT_CLOSE_SESSION, 0

    def external_phase_notify_service_not_required(self):
        self._get_connected_ap()
        self._get_new_data_packet()

    def lambda_phase_session_closed(self):
        pass

    def lambda_phase_notify_service_required(self):
        self.add_msg_to_queue(self.output_service_required, ServiceRequired(self.service_id, True))

    def lambda_phase_to_await_dc(self):
        # if self.connected_ap is not None and self.next_timeout <= self._clock:
        if self.connected_ap is not None:
            app_msg = GetDataCenterRequest(self.ue_id, self.service_id, self.service_header)
            net_msg = self.__encapsulate_network_packet(self.connected_ap, app_msg)
            self.add_msg_to_queue(self.output_network, net_msg)

    def lambda_phase_to_open_session(self):
        # if self.connected_ap is not None and self.next_timeout <= self._clock:
        if self.connected_ap is not None:
            app_msg = CreateSessionRequestPacket(self.service_id, self.ue_id, self.service_header)
            net_msg = self.__encapsulate_network_packet(self.dc_id, app_msg)
            self.add_msg_to_queue(self.output_network, net_msg)

    def lambda_phase_opened_session(self):
        # if self.connected_ap is not None and self.next_timeout <= self._clock:
        if self.connected_ap is not None:
            self._add_msg_to_request_buffer()
            self._resend_timedout_messages()

    def lambda_phase_to_close_session(self):
        # if self.connected_ap is not None and self.next_timeout <= self._clock:
        if self.connected_ap is not None:
            app_msg = RemoveSessionRequestPacket(self.service_id, self.ue_id, self.service_header)
            net_msg = self.__encapsulate_network_packet(self.dc_id, app_msg)
            self.add_msg_to_queue(self.output_network, net_msg)

    def lambda_phase_notify_service_not_required(self):
        self.add_msg_to_queue(self.output_service_required, ServiceRequired(self.service_id, False))

    def _get_connected_ap(self):
        if self.input_connected_ap:
            self.connected_ap = self.input_connected_ap.get().ap_id

    def _get_new_data_packet(self):
        for job in self.input_session_request.values:
            msg = OngoingSessionRequestPacket(self.service_id, self.ue_id, self.service_header, job.data,
                                              self.labeling_pointer)
            struct = {
                DATA: msg,
                INITIAL_CLOCK: self._clock,
                ACKNOWLEDGED: False,
                TIMES_SENT: 0,
                FIRST_TIME_SENT: self._clock,
                NEXT_TIMEOUT: self._clock
            }
            self.data_buffer.append(struct)
            self.labeling_pointer = (self.labeling_pointer + 1) % (2 * self.window_size)

    def _clean_request_buffer(self):
        header = logging_overhead(self._clock, LOGGING_OVERHEAD)
        clean = False
        for job in self.input_network.values:
            node_from, msg = self.__expand_network_message(job)
            if isinstance(msg, OngoingSessionResponsePacket):
                packet_id = msg.packet_id
                response = msg.response
                for msg in self.request_buffer:
                    if msg[DATA].packet_id == packet_id:
                        ue_id = self.ue_id
                        service_id = self.service_id
                        logging.info(header + "%s received ongoing service %s response: %s" % (ue_id, service_id,
                                                                                               response))
                        if response:
                            clean = True
                            msg[ACKNOWLEDGED] = True
                            instant_generated = msg[INITIAL_CLOCK]
                            instant_received = self._clock
                            delay = instant_received - instant_generated
                            instant_sent = msg[FIRST_TIME_SENT]
                            times_sent = msg[TIMES_SENT]
                            logging.info(header + "    perceived delay: %.3f seconds" % delay)
                            delay_report = ServiceDelayReport(ue_id, service_id, instant_generated, instant_sent,
                                                              instant_received, delay, times_sent)
                            self.add_msg_to_queue(self.output_service_delay_report, delay_report)
                            self.next_timeout = self._clock
                        else:
                            logging.warning(header + "    Request failed. Waiting for timeout and resending packet")
        n_msg_out = 0
        for msg in self.request_buffer:
            if msg[ACKNOWLEDGED]:
                n_msg_out += 1
            else:
                break
        [self.request_buffer.popleft() for _ in range(n_msg_out)]
        return clean

    def _add_msg_to_request_buffer(self):
        header = logging_overhead(self._clock, LOGGING_OVERHEAD)
        while self.data_buffer and (len(self.request_buffer) < self.window_size):
            job = self.data_buffer.popleft()
            index = str(job[DATA].packet_id)
            logging.info(header + '%s sending ongoing service %s request (%s)' % (self.ue_id, self.service_id, index))
            job[NEXT_TIMEOUT] = self._clock + self.service_timeout
            job[FIRST_TIME_SENT] = self._clock
            job[TIMES_SENT] = 1
            self.request_buffer.append(job)
            net_msg = self.__encapsulate_network_packet(self.dc_id, job[DATA])
            self.add_msg_to_queue(self.output_network, net_msg)

    def _resend_timedout_messages(self):
        header = logging_overhead(self._clock, LOGGING_OVERHEAD)
        for msg in self.request_buffer:
            if (not msg[ACKNOWLEDGED]) and msg[NEXT_TIMEOUT] <= self._clock:
                logging.warning(header + '%s experienced an ongoing service %s (%s) request timeout. Resending request'
                                % (self.ue_id, self.service_id, msg[DATA].packet_id))
                msg[NEXT_TIMEOUT] = self._clock + self.service_timeout
                msg[TIMES_SENT] += 1
                net_msg = self.__encapsulate_network_packet(self.dc_id, msg[DATA])
                self.add_msg_to_queue(self.output_network, net_msg)

    def _compute_next_timeout(self):
        next_timeout = self._clock + self.service_timeout
        for msg in self.request_buffer:
            if (not msg[ACKNOWLEDGED]) and msg[NEXT_TIMEOUT] < next_timeout:
                next_timeout = msg[NEXT_TIMEOUT]
        return max(next_timeout - self._clock, 0)

    def __expand_network_message(self, network_message):
        assert self.ue_id == network_message.node_to
        return network_message.node_from, network_message.data

    def __encapsulate_network_packet(self, node_to, application_message):
        header = self.network_header
        return NetworkPacket(self.ue_id, node_to, header, application_message)
