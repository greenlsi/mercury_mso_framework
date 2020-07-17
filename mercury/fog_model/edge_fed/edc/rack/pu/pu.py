import logging
from collections import deque
from xdevs.models import Port, INFINITY
from .....common import FiniteStateMachine, logging_overhead
from .....common.edge_fed.pu import ProcessingUnitReport, ProcessingUnitConfiguration
from .pu_pwr import ProcessingUnitPowerModelFactory
from .pu_temp import ProcessingUnitTemperatureModelFactory
from ...internal_ports import OpenSessionRequest, OpenSessionResponse, OngoingSessionRequest, OngoingSessionResponse, \
    CloseSessionRequest, CloseSessionResponse, ChangeStatus, ChangeStatusResponse, SetDVFSMode, SetDVFSModeResponse

PHASE_START = 'start'
PHASE_OFF = 'off'
PHASE_ON = 'on'
PHASE_BUSY = 'busy'
PHASE_TO_ON = 'to_on'
PHASE_TO_OFF = 'to_off'
P_UNIT_PHASES = [PHASE_START, PHASE_OFF, PHASE_ON, PHASE_BUSY, PHASE_TO_ON, PHASE_TO_OFF]

LOGGING_OVERHEAD = "            "


class ProcessingUnit(FiniteStateMachine):
    """
    Processing unit model for xDEVS
    :param str name: name of the XDEVS module
    :param ProcessingUnitConfiguration pu_config: Processing Unit Configuration
    :param str rack_id: ID of the rack that contains the processing unit
    :param int pu_index: processing unit corresponding index within the EDC
    :param dict services_config: dictionary with the configuration of every service in the scenario
    :param float env_temp: Processing unit base temperature (in Kelvin)
    """
    pu_power_factory = ProcessingUnitPowerModelFactory()
    pu_temp_factory = ProcessingUnitTemperatureModelFactory()

    def __init__(self, name, pu_config, rack_id, pu_index, services_config, env_temp=298):
        # Unwrap configuration parameters
        self.pu_id = pu_config.p_unit_id
        self.dvfs_table = pu_config.dvfs_table
        self.max_u = pu_config.max_u
        self.max_start_stop = pu_config.max_start_stop
        self.t_on = pu_config.t_on
        self.t_off = pu_config.t_off
        self.t_start = pu_config.t_start
        self.t_stop = pu_config.t_stop
        self.t_operation = pu_config.t_operation

        power_model_name = pu_config.power_model_name
        power_model_config = pu_config.power_model_config
        self.power_model = self.pu_power_factory.create_model(power_model_name, **power_model_config)

        temp_model_name = pu_config.temp_model_name
        temp_model_config = pu_config.temp_model_config
        self.temp_model = self.pu_temp_factory.create_model(temp_model_name, **temp_model_config)
        # dictionary that contains how much computing resources require a single session of a given service
        self.services_u = {service_id: service_conf.service_u for service_id, service_conf in services_config.items()}

        # Set status attributes
        self.rack_id = rack_id          # ID of the rack that contains the processing unit
        self.pu_index = pu_index        # corresponding index of the PU within the rack of the EDC
        self.status = False             # PU status. By default, all the PUs start powered off
        self.dvfs_mode = False          # DVFS mode. By default, it is not activated
        self.dvfs_index = 0             # index of current DVFS configuration
        self.utilization = 0.0          # utilization factor
        self.u_per_service = dict()     # utilization factor splitted by service {service_id: utilization}
        self.ongoing_sessions = dict()  # ongoing sessions {service_id: [session_id]}
        self.power = 0                  # PU required power consumption
        self.env_temp = env_temp        # Environment temperature of the processing unit
        self.temperature = env_temp     # PU temperature of PU. Initially, it is set to env_temp

        self.start_buffer = deque()     # Buffer of sessions that require to be started
        self.stop_buffer = deque()      # Buffer of sessions that require to be stopped

        self.starting = list()          # Sessions that are being started
        self.acking = list()            # Requests of ongoing sessions that are being processed
        self.removing = list()          # Sessions that are being stopped

        self.open_tasks = dict()        # Event schedule for services being started
        self.ongoing_tasks = dict()     # Event schedule for ongoing services that are processing requests
        self.close_tasks = dict()       # Event schedule for services being stopped

        # FSM stuff
        int_table = {
            PHASE_START: self.internal_phase_off,
            PHASE_OFF: self.internal_phase_off,
            PHASE_TO_OFF: self.internal_phase_off,
            PHASE_ON: self.internal_phase_on,
            PHASE_BUSY: self.internal_phase_on,
            PHASE_TO_ON: self.internal_phase_on,
        }
        ext_table = {
            PHASE_START: None,
            PHASE_OFF: self.external_phase_off,
            PHASE_ON: self.external_phase_on,
            PHASE_BUSY: self.external_phase_on,
            PHASE_TO_OFF: None,
            PHASE_TO_ON: None,
        }
        lambda_table = {phase: None for phase in P_UNIT_PHASES}
        lambda_table[PHASE_START] = self.lambda_send_pu_report
        lambda_table[PHASE_BUSY] = self.lambda_send_tasks
        initial_state = PHASE_START
        initial_timeout = 0
        super().__init__(P_UNIT_PHASES, int_table, ext_table, lambda_table, initial_state, initial_timeout, name)

        # I/O ports
        self.input_change_status = Port(ChangeStatus, name + '_input_change_status')
        self.input_set_dvfs_mode = Port(SetDVFSMode, name + '_input_set_dvfs_mode')
        self.input_open_session = Port(OpenSessionRequest, name + '_input_open_session')
        self.input_ongoing_session = Port(OngoingSessionRequest, name + '_input_ongoing_session')
        self.input_close_session = Port(CloseSessionRequest, name + '_input_close_session')
        self.output_p_unit_report = Port(ProcessingUnitReport, name + '_output_p_unit_report')
        self.output_change_status_response = Port(ChangeStatusResponse, name + '_output_change_status_response')
        self.output_set_dvfs_mode_response = Port(SetDVFSModeResponse, name + '_output_set_dvfs_mode_response')
        self.output_open_session_response = Port(OpenSessionResponse, name + '_output_create_session_response')
        self.output_ongoing_session_response = Port(OngoingSessionResponse, name + '_output_ongoing_session_response')
        self.output_close_session_response = Port(CloseSessionResponse, name + '_output_remove_session_response')

        self.add_in_port(self.input_change_status)                  # port for incoming change status messages
        self.add_in_port(self.input_set_dvfs_mode)                  # port for incoming new DVFS mode messages
        self.add_in_port(self.input_open_session)                   # port for incoming create session messages
        self.add_in_port(self.input_ongoing_session)                # port for incoming ongoing session messages
        self.add_in_port(self.input_close_session)                  # port for incoming remove session messages
        self.add_out_port(self.output_p_unit_report)                # port for leaving processing unit report messages
        self.add_out_port(self.output_change_status_response)       # port for leaving change status response messages
        self.add_out_port(self.output_set_dvfs_mode_response)       # port for leaving new DVFS mode response messages
        self.add_out_port(self.output_open_session_response)        # port for leaving open session response messages
        self.add_out_port(self.output_ongoing_session_response)     # port for leaving ongoing session response messages
        self.add_out_port(self.output_close_session_response)       # port for leaving close session response messages

    @staticmethod
    def add_response_to_queue(queue, t, msg):
        if t not in queue:
            queue[t] = list()
        queue[t].append(msg)

    def internal_phase_on(self):
        # Trigger pending close service processes
        while self.stop_buffer and self.enough_size():
            service_id, session_id = self.stop_buffer.popleft()
            self.removing.append((service_id, session_id))
            t = self._clock + self.t_stop
            msg = CloseSessionResponse(self.rack_id, self.pu_index, service_id, session_id, True)
            self.add_response_to_queue(self.close_tasks, t, msg)
        # Trigger pending open service processes
        delta = sum([self.services_u[service_id] for service_id, session_id in self.starting])
        while self.start_buffer and self.enough_size():
            service_id, session_id = self.start_buffer[0]
            utilization = self.services_u[service_id]
            # Check that there are enough available resources before triggering new services
            if self.utilization + delta + utilization <= self.max_u:
                delta += utilization
                service_id, session_id = self.start_buffer.popleft()
                self.starting.append((service_id, session_id))
                t = self._clock + self.t_start
                msg = OpenSessionResponse(self.rack_id, self.pu_index, service_id, session_id, True)
                self.add_response_to_queue(self.open_tasks, t, msg)
            # Otherwise, it is required to wait until other services are removed before adding new service to the queue
            else:
                break
        # Compute next event
        min_ongoing = min(self.ongoing_tasks) - self._clock if self.ongoing_tasks else INFINITY
        min_open = min(self.open_tasks) - self._clock if self.open_tasks else INFINITY
        min_close = min(self.close_tasks) - self._clock if self.close_tasks else INFINITY
        next_event = min(min_ongoing, min_open, min_close)
        next_phase = PHASE_BUSY if next_event < INFINITY else PHASE_ON
        return next_phase, next_event

    @staticmethod
    def internal_phase_off():
        return PHASE_OFF, INFINITY

    def external_phase_off(self):
        """Operations to perform in phase OFF"""
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        next_phase = PHASE_OFF
        next_timeout = 0
        report = False
        # CASE 1: Processing unit received set DVFS mode message
        if self.input_set_dvfs_mode:
            dvfs = self._check_set_dvfs_mode_port(overhead)
            if dvfs != self.dvfs_mode:
                self.dvfs_mode = dvfs
                report = True
            msg = SetDVFSModeResponse(self.rack_id, self.pu_index, dvfs, True)
            self.add_msg_to_queue(self.output_set_dvfs_mode_response, msg)
        # CASE 2: Processing Unit received change status (switch on) message
        elif self.input_change_status:
            status = self._check_change_status_port(overhead)
            if status:
                self.status = status
                report = True
                next_phase = PHASE_TO_ON
                next_timeout = self.t_on
            msg = ChangeStatusResponse(self.rack_id, self.pu_index, status, True)
            self.add_msg_to_queue(self.output_change_status_response, msg)
        else:
            self._off_affirmative_stops(overhead)
            self._off_negative_ongoings(overhead)
            self._off_negative_starts(overhead)
        # Send report if required
        if report:
            self._refresh_properties()
            self.send_pu_report()
        return next_phase, next_timeout

    def external_phase_on(self):
        """Operations to perform in phase ON"""
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        report = False
        # CASE 1: Any service-related request
        self._check_ongoing_session_requests(overhead)
        self._check_close_session_requests(overhead)
        self._check_open_session_requests(overhead)
        next_phase, next_timeout = self.internal_phase_on()
        # If no events are scheduled, then we can change the DVFS mode or the status
        if next_phase == PHASE_ON:
            # CASE 2: Processing Unit received change status message
            if self.input_change_status:
                next_timeout = 0
                status = self._check_change_status_port(overhead)
                response = status
                if not status and not self.ongoing_sessions and not self.starting:
                    self.status = status
                    response = True
                    report = True
                    next_phase = PHASE_TO_OFF
                    next_timeout = self.t_off
                # Add response to queue
                msg = ChangeStatusResponse(self.rack_id, self.pu_index, status, response)
                self.add_msg_to_queue(self.output_change_status_response, msg)
            # CASE 3: Processing unit received set DVFS mode message
            elif self.input_set_dvfs_mode:
                next_timeout = 0
                dvfs = self._check_set_dvfs_mode_port(overhead)
                if dvfs != self.dvfs_mode:
                    self.dvfs_mode = dvfs
                    report = True
                msg = SetDVFSModeResponse(self.rack_id, self.pu_index, dvfs, True)
                self.add_msg_to_queue(self.output_set_dvfs_mode_response, msg)
        if report:
            self._refresh_properties()
            self.send_pu_report()
        return next_phase, next_timeout

    def lambda_send_pu_report(self):
        self.send_pu_report()

    def lambda_send_tasks(self):
        ongoing_due = self.ongoing_tasks.pop(self._clock, list())
        for msg in ongoing_due:
            self.add_msg_to_queue(self.output_ongoing_session_response, msg)
            if msg.response:
                self.acking.remove((msg.service_id, msg.session_id))
        close_due = self.close_tasks.pop(self._clock, list())
        needs_report = False
        for msg in close_due:
            if msg.response:
                needs_report |= self.remove_session(msg.service_id, msg.session_id)
            self.add_msg_to_queue(self.output_close_session_response, msg)
        open_due = self.open_tasks.pop(self._clock, list())
        for msg in open_due:
            if msg.response:
                needs_report |= self.create_session(msg.service_id, msg.session_id)
            self.add_msg_to_queue(self.output_open_session_response, msg)
        if needs_report:
            self._refresh_properties()
            self.send_pu_report()

    def _check_change_status_port(self, overhead):
        """
        Checks the change status port
        :param str overhead: logging overhead
        :return bool: new requested status
        """
        if self.input_change_status:
            status = self.input_change_status.get().status
            logging.info(overhead + "%s received change status->%s message" % (self.name, status))
            if not status and (self.ongoing_sessions or self.open_tasks):
                logging.warning(overhead + "    Impossible to switch off. Sending negative response.")
            return status

    def _check_set_dvfs_mode_port(self, overhead):
        """
        Checks the DVFS mode port
        :param str overhead: logging overhead
        :return bool: result of the operation
        """
        if self.input_set_dvfs_mode:
            dvfs_mode = self.input_set_dvfs_mode.get().dvfs_mode
            logging.info(overhead + "%s received set DVFS mode->%r message" % (self.name, dvfs_mode))
            return dvfs_mode

    def _check_ongoing_session_requests(self, overhead):
        """
        Checks the close session port
        :param str overhead: logging overhead
        :return str, str: pxsch ID and session ID
        """
        for msg in self.input_ongoing_session.values:
            service_id = msg.service_id
            session_id = msg.session_id
            packet_id = msg.packet_id
            logging.info(overhead + "%s received ongoing session->(%s,%s,%s) request" % (self.name, service_id,
                                                                                         session_id, str(packet_id)))
            res = service_id in self.ongoing_sessions and session_id in self.ongoing_sessions[service_id]
            t = self._clock
            if res:
                if (service_id, session_id) in self.removing or (service_id, session_id) in self.stop_buffer:
                    res = False
                    logging.warning(overhead + "    session is being removed. Sending negative response.")
                else:
                    self.acking.append((service_id, session_id))
                    t += self.t_operation
            else:
                logging.warning(overhead + "    session not found. Sending negative response.")
            msg = OngoingSessionResponse(self.rack_id, self.pu_index, service_id, session_id, packet_id, res)
            self.add_response_to_queue(self.ongoing_tasks, t, msg)

    def _check_close_session_requests(self, overhead):
        """
        Checks the close session port
        :param str overhead: logging overhead
        :return str, str: service ID and session ID
        """
        for msg in self.input_close_session.values:
            service_id = msg.service_id
            session_id = msg.session_id
            logging.info(overhead + "%s received close session->(%s,%s) request" % (self.name, service_id, session_id))
            res = service_id in self.ongoing_sessions and session_id in self.ongoing_sessions[service_id]
            if res:
                if (service_id, session_id) in self.removing or (service_id, session_id) in self.stop_buffer:
                    logging.warning(overhead + "    session is already being removed. Ignoring request.")
                elif (service_id, session_id) in self.acking:
                    logging.warning(overhead + "    session is busy. Sending negative response.")
                    msg = CloseSessionResponse(self.rack_id, self.pu_index, service_id, session_id, False)
                    self.add_response_to_queue(self.close_tasks, self._clock, msg)
                else:
                    self.stop_buffer.append((service_id, session_id))
            else:
                logging.warning(overhead + "    session not found. Sending affirmative response.")
                msg = CloseSessionResponse(self.rack_id, self.pu_index, service_id, session_id, True)
                self.add_response_to_queue(self.close_tasks, self._clock, msg)

    def _check_open_session_requests(self, overhead):
        """
        Checks the open session port
        :param str overhead: logging overhead
        :return str, str, float: pxsch ID, session ID and std_u factor to be used
        """
        delta = self._initial_delta()
        for msg in self.input_open_session.values:
            service_id = msg.service_id
            session_id = msg.session_id
            logging.info(overhead + "%s received open session->(%s,%s) request" % (self.name, service_id, session_id))
            service_u = self.services_u[service_id]
            if (service_id, session_id) in self.starting:
                logging.warning(overhead + "    Session is already being created. Ignoring request.")
            elif service_id in self.ongoing_sessions and session_id in self.ongoing_sessions[service_id]:
                logging.warning(overhead + "    Session already exists. Sending affirmative response.")
                msg = OpenSessionResponse(self.rack_id, self.pu_index, service_id, session_id, True)
                self.add_response_to_queue(self.open_tasks, self._clock, msg)
            elif 0 <= service_u <= self.max_u - self.utilization - delta:
                delta += service_u
                self.start_buffer.append((service_id, session_id))
            else:
                logging.warning(overhead + "    Unable to create session. Sending negative response.")
                msg = OpenSessionResponse(self.rack_id, self.pu_index, service_id, session_id, False)
                self.add_response_to_queue(self.open_tasks, self._clock, msg)

    def _initial_delta(self):
        delta = 0
        for service_id, session_id in self.starting:
            delta += self.services_u[service_id]
        for service_id, session_id in self.start_buffer:
            delta += self.services_u[service_id]
        for service_id, session_id in self.removing:
            delta -= self.services_u[service_id]
        for service_id, session_id in self.stop_buffer:
            delta -= self.services_u[service_id]
        return delta

    def enough_size(self):
        return self.max_start_stop <= 0 or self.max_start_stop > len(self.starting) + len(self.removing)

    def _off_negative_ongoings(self, overhead):
        for msg in self.input_ongoing_session.values:
            service_id = msg.service_id
            session_id = msg.session_id
            packet_id = msg.packet_id
            logging.info(overhead + "%s received ongoing session->(%s,%s,%s) request" % (self.name, service_id,
                                                                                         session_id, str(packet_id)))
            logging.warning(overhead + "    PU is switched off. Sending Negative response.")
            msg = OngoingSessionResponse(self.rack_id, self.pu_index, service_id, session_id, packet_id, False)
            self.add_msg_to_queue(self.output_ongoing_session_response, msg)

    def _off_affirmative_stops(self, overhead):
        for msg in self.input_close_session.values:
            service_id = msg.service_id
            session_id = msg.session_id
            logging.info(overhead + "%s received close session->(%s,%s) request" % (self.name, service_id, session_id))
            logging.warning(overhead + "    PU is switched off. Sending affirmative response.")
            msg = CloseSessionResponse(self.rack_id, self.pu_index, service_id, session_id, True)
            self.add_msg_to_queue(self.output_close_session_response, msg)

    def _off_negative_starts(self, overhead):
        for msg in self.input_open_session.values:
            service_id = msg.service_id
            session_id = msg.session_id
            logging.info(overhead + "%s received create session->(%s,%s) request" % (self.name, service_id, session_id))
            logging.warning(overhead + "    PU is switched off. Sending Negative response.")
            msg = OpenSessionResponse(self.rack_id, self.pu_index, service_id, session_id, False)
            self.add_msg_to_queue(self.output_open_session_response, msg)

    def remove_session(self, service_id, session_id):
        """
        Removes an ongoing task and frees resources
        :param str service_id: ID of the pxsch to be removed
        :param str session_id: ID of the session to be removed
        """
        res = False
        if service_id in self.ongoing_sessions:
            if session_id in self.ongoing_sessions[service_id]:
                res = True
                self.removing.remove((service_id, session_id))
                self.ongoing_sessions[service_id].remove(session_id)
            if not self.ongoing_sessions[service_id]:
                self.ongoing_sessions.pop(service_id)
        return res

    def ack_session(self, service_id, session_id):
        self.acking.remove((service_id, session_id))

    def create_session(self, service_id, session_id):
        """
        Earmarks resources for new incoming task
        :param str service_id: ID of the task to be processed
        :param str session_id: ID of the task to be processed
        """
        res = False
        if service_id not in self.ongoing_sessions:
            self.ongoing_sessions[service_id] = list()
        if session_id not in self.ongoing_sessions[service_id]:
            res = True
            self.starting.remove((service_id, session_id))
            self.ongoing_sessions[service_id].append(session_id)
        return res

    def _refresh_properties(self):
        """Refreshes the values of the processing unit"""
        self.__compute_utilization()
        self.__compute_dvfs_index()
        self.__compute_power()
        self.__compute_temperature()

    def __compute_utilization(self):
        """Computes std_u factor of the processing unit"""
        utilization = 0
        u_per_service = dict()
        for service_id, sessions in self.ongoing_sessions.items():
            u = self.services_u[service_id] * len(sessions)
            u_per_service[service_id] = u
            utilization += u
        self.utilization = utilization
        self.u_per_service = u_per_service

    def __compute_dvfs_index(self):
        """Computes the DVFS table index that fits the best"""
        # CASE 1: processing unit is switched off -> DVFS index set to 0
        if not self.status:
            self.dvfs_index = 0
        # CASE 2: DVFS mode is set to false -> DVFS index set to 100
        elif not self.dvfs_mode:
            self.dvfs_index = 100
        # CASE 3: DVFS mode is set to true -> find lowest DVFS index that fulfills computing requirements
        else:
            relative_u = self.utilization / self.max_u * 100
            self.dvfs_index = min([i for i in self.dvfs_table if i >= relative_u])

    def __compute_power(self):
        """Computes the processing unit power consumption"""
        try:
            self.power = self.power_model.compute_power(self.status, self.utilization, self.max_u, self.dvfs_index,
                                                        self.dvfs_table)
        except AttributeError:
            self.power = 0

    def __compute_temperature(self):
        """Computes the processing unit temperature"""
        try:
            self.temperature = self.temp_model.compute_temperature(self.status, self.utilization, self.max_u,
                                                                   self.dvfs_index, self.dvfs_table)
        except AttributeError:
            self.temperature = self.env_temp

    def send_pu_report(self):
        ongoing_sessions = {service_id: [session_id for session_id in sessions]
                            for service_id, sessions in self.ongoing_sessions.items()}
        u_per_service = {service_id: u for service_id, u in self.u_per_service.items()}
        msg = ProcessingUnitReport(self.rack_id, self.pu_index, self.pu_id, self.max_u, self.max_start_stop,
                                   self.status, self.dvfs_mode, self.dvfs_index, self.utilization, self.power,
                                   self.temperature, ongoing_sessions, u_per_service)
        self.add_msg_to_queue(self.output_p_unit_report, msg)
