import logging
from xdevs.models import Port, INFINITY
from ...common import FiniteStateMachine, logging_overhead
from ...common.edge_fed import ProcessingUnitReport, ProcessingUnitConfiguration
from .internal_ports import ChangeStatus, ChangeStatusResponse, SetDVFSMode, SetDVFSModeResponse
from .internal_ports import OpenSession, OpenSessionResponse, CloseSession, CloseSessionResponse

PHASE_OFF = 'off'
PHASE_ON = 'on'
PHASE_OPERATION = 'operation'
PHASE_OFF_TO_ON = 'off_on'
PHASE_ON_TO_OFF = 'on_off'
P_UNIT_PHASES = [PHASE_OFF, PHASE_ON, PHASE_OPERATION, PHASE_OFF_TO_ON, PHASE_ON_TO_OFF]

LOGGING_OVERHEAD = "            "


class ProcessingUnit(FiniteStateMachine):
    """
    Processing unit model for xDEVS
    :param str name: name of the XDEVS module
    :param ProcessingUnitConfiguration p_unit_configuration: Processing Unit Configuration
    :param int pu_index: processing unit corresponding index within the EDC
    :param float base_temp: Processing unit base temperature (in Kelvin)
    """
    def __init__(self, name, p_unit_configuration, pu_index, base_temp=298):
        # Unwrap configuration parameters
        self.p_unit_id = p_unit_configuration.p_unit_id
        self.dvfs_table = p_unit_configuration.dvfs_table
        self.std_to_spec_u = p_unit_configuration.std_to_spec_u
        self.t_off_on = p_unit_configuration.t_off_on
        self.t_on_off = p_unit_configuration.t_on_off
        self.t_operation = p_unit_configuration.t_operation
        self.power_model = p_unit_configuration.power_model

        # Set status attributes
        self.pu_index = pu_index        # processing unit corresponding index within the EDC
        self.status = False             # by default, all the processing units start powered off
        self.dvfs_mode = False          # DVFS mode. By default, it is not activated
        self.dvfs_index = 0             # index of current DVFS configuration
        self.utilization = 0.0          # real utilization factor
        self.ongoing_sessions = dict()  # {service_id: {session_id: service_u}}
        self.power = 0                  # Initial power is 0
        self.temperature = base_temp    # Initial temperature is set to base_temp

        # FSM stuff
        int_table = {
            PHASE_OFF: self.internal_phase,
            PHASE_ON: self.internal_phase,
            PHASE_ON_TO_OFF: self.internal_phase,
            PHASE_OFF_TO_ON: self.internal_phase,
            PHASE_OPERATION: self.internal_phase,
        }
        ext_table = {
            PHASE_OFF: self.external_phase_off,
            PHASE_ON: self.external_phase_on,
            PHASE_ON_TO_OFF: None,
            PHASE_OFF_TO_ON: None,
            PHASE_OPERATION: None,
        }
        lambda_table = {
            PHASE_OFF: None,
            PHASE_ON: None,
            PHASE_ON_TO_OFF: None,
            PHASE_OFF_TO_ON: None,
            PHASE_OPERATION: None,
        }
        initial_state = PHASE_OFF
        initial_timeout = INFINITY
        super().__init__(P_UNIT_PHASES, int_table, ext_table, lambda_table, initial_state, initial_timeout, name)

        # I/O ports
        self.input_change_status = Port(ChangeStatus, name + '_input_change_status')
        self.input_set_dvfs_mode = Port(SetDVFSMode, name + '_input_set_dvfs_mode')
        self.input_open_session = Port(OpenSession, name + '_input_open_session')
        self.input_close_session = Port(CloseSession, name + '_input_close_session')
        self.output_change_status_response = Port(ChangeStatusResponse, name + '_output_change_status_response')
        self.output_set_dvfs_mode_response = Port(SetDVFSModeResponse, name + '_output_set_dvfs_mode_response')
        self.output_open_session_response = Port(OpenSessionResponse, name + '_output_open_session_response')
        self.output_close_session_response = Port(CloseSessionResponse, name + '_output_close_session_response')

        self.add_in_port(self.input_change_status)              # port for incoming change status messages
        self.add_in_port(self.input_set_dvfs_mode)              # port for incoming new DVFS mode messages
        self.add_in_port(self.input_open_session)               # port for incoming open session messages
        self.add_in_port(self.input_close_session)              # port for incoming close session messages
        self.add_out_port(self.output_change_status_response)   # port for leaving change status response messages
        self.add_out_port(self.output_set_dvfs_mode_response)   # port for leaving new DVFS mode response messages
        self.add_out_port(self.output_open_session_response)    # port for leaving open session response messages
        self.add_out_port(self.output_close_session_response)   # port for leaving close session response messages

    def internal_phase(self):
        """Manages internal phase timeouts"""
        if self.phase == PHASE_OPERATION or self.phase == PHASE_ON or self.phase == PHASE_OFF_TO_ON:
            return PHASE_ON, INFINITY
        else:
            return PHASE_OFF, INFINITY

    def external_phase_off(self):
        """Operations to perform in phase OFF"""
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)

        # CASE 1: Processing Unit received change status message
        status = self._check_change_status_port(overhead)
        if status is not None:
            next_state = PHASE_OFF
            next_timeout = 0
            # 1.1 Processing unit is requested to switch on
            if status and self.change_status(status):
                logging.info(overhead + "    processing unit is being switched on...")
                next_state = PHASE_OFF_TO_ON
                next_timeout = self.t_off_on
            # 1.2 Processing unit is requested to switch off
            else:
                logging.warning(overhead + "    processing unit already switched off. Sending affirmative response")
            # Send result to change status response port
            msg = ChangeStatusResponse(self.pu_index, True, self.get_report())
            self.add_msg_to_queue(self.output_change_status_response, msg)
            return next_state, next_timeout
        # CASE 2: Processing unit received set DVFS mode message
        if self._check_set_dvfs_mode_port(overhead):
            return PHASE_OFF, 0
        # CASE 3: Processing unit received remove session message
        service_id, session_id = self._check_close_session_port(overhead)
        if service_id is not None and session_id is not None:
            logging.warning(overhead + "    processing unit is switched off. Sending affirmative response")
            msg = CloseSessionResponse(self.pu_index, service_id, session_id, True, self.get_report())
            self.add_msg_to_queue(self.output_close_session_response, msg)
            return PHASE_OFF, 0
        # CASE 4: Processing unit received create session message
        service_id, session_id, service_u = self._check_open_session_port(overhead)
        if service_id is not None and session_id is not None and service_u is not None:
            logging.warning(overhead + "    processing unit is switched off. Sending negative response")
            msg = OpenSessionResponse(self.pu_index, service_id, session_id, False, self.get_report())
            self.add_msg_to_queue(self.output_open_session_response, msg)
            return PHASE_OFF, 0
        raise Exception(overhead + "processing unit woke up but no message has been detected. This should never happen")

    def external_phase_on(self):
        """Operations to perform in phase ON"""
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)

        # CASE 1: Processing Unit received change status message
        status = self._check_change_status_port(overhead)
        if status is not None:
            response = True
            next_state = PHASE_ON
            next_timeout = 0
            if status:
                logging.warning(overhead + "    processing unit already switched on. Sending affirmative response")
            elif self.change_status(status):
                logging.info(overhead + "    processing unit is being switched off...")
                next_state = PHASE_ON_TO_OFF
                next_timeout = self.t_on_off
            else:
                logging.warning(overhead + "    processing unit has pending sessions. Sending negative response")
                response = False

            msg = ChangeStatusResponse(self.pu_index, response, self.get_report())
            self.add_msg_to_queue(self.output_change_status_response, msg)
            return next_state, next_timeout
        # CASE 2: Processing unit received set DVFS mode message
        if self._check_set_dvfs_mode_port(overhead):
            return PHASE_ON, 0
        service_id, session_id = self._check_close_session_port(overhead)
        # CASE 3: Processing unit received remove session message
        if service_id is not None and session_id is not None:
            next_state = PHASE_ON
            next_timeout = 0
            if self.remove_session(service_id, session_id):
                logging.info(overhead + "    processing unit is removing the session...")
                next_state = PHASE_OPERATION
                next_timeout = self.t_operation
            else:
                logging.warning(overhead + "    processing unit cannot find the session. Sending affirmative response")
            msg = CloseSessionResponse(self.pu_index, service_id, session_id, True, self.get_report())
            self.add_msg_to_queue(self.output_close_session_response, msg)
            return next_state, next_timeout
        service_id, session_id, service_u = self._check_open_session_port(overhead)
        # CASE 4: Processing unit received create session message
        if service_id is not None and session_id is not None and service_u is not None:
            response = False
            next_state = PHASE_ON
            next_timeout = 0
            if self.create_service(service_id, session_id, service_u):
                response = True
                next_state = PHASE_OPERATION
                next_timeout = self.t_operation
                logging.debug(overhead + "    processing unit is creating the new session...")
            else:
                logging.warning(overhead + "    processing unit cannot create the session. Sending negative response")
            msg = OpenSessionResponse(self.pu_index, service_id, session_id, response, self.get_report())
            self.add_msg_to_queue(self.output_open_session_response, msg)
            return next_state, next_timeout
        raise Exception(overhead + "%s woke up but no message has been detected. This should never happen")

    def get_report(self):
        """
        Returns a report of the current processing unit status
        :return ProcessingUnitReport: processing unit report"""
        return ProcessingUnitReport(self.p_unit_id, self.std_to_spec_u, self.status, self.dvfs_mode, self.dvfs_index,
                                    self.utilization, self.power, self.temperature, self.ongoing_sessions)

    def _check_change_status_port(self, overhead):
        """
        Checks the change status port
        :param str overhead: logging overhead
        :return bool: new requested status
        """
        status = None
        if self.input_change_status:
            status = self.input_change_status.get().status
            logging.info(overhead + "%s received change status->%s message" % (self.name, status))
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
            if self.dvfs_mode == dvfs_mode:
                logging.warning(overhead + "    Nothing to change. Sending affirmative response")
            else:
                self.set_dvfs_mode(dvfs_mode)
                logging.info(overhead + "    processing unit successfully changed its DVFS mode")
            msg = SetDVFSModeResponse(self.pu_index, True, self.get_report())
            self.add_msg_to_queue(self.output_set_dvfs_mode_response, msg)
            return True
        return False

    def _check_close_session_port(self, overhead):
        """
        Checks the close session port
        :param str overhead: logging overhead
        :return str, str: pxsch ID and session ID
        """
        service_id = None
        session_id = None
        if self.input_close_session:
            msg = self.input_close_session.get()
            service_id = msg.service_id
            session_id = msg.session_id
            logging.info(overhead + "%s received close session->(%s,%s) request" % (self.name, service_id, session_id))
        return service_id, session_id

    def _check_open_session_port(self, overhead):
        """
        Checks the open session port
        :param str overhead: logging overhead
        :return str, str, float: pxsch ID, session ID and utilization factor to be used
        """
        service_id = None
        session_id = None
        service_u = None
        if self.input_open_session:
            msg = self.input_open_session.get()
            service_id = msg.service_id
            session_id = msg.session_id
            service_u = msg.service_u
            logging.info(overhead + "%s received create session->(%s,%s,%.2f) request" % (self.name, service_id, session_id, service_u))
        return service_id, session_id, service_u

    def change_status(self, status):
        """
        Changes processing unit status
        :param bool status: new status (False to switch off, True to switch on)
        :return bool: result of the action (True if success)"""
        if self.ongoing_sessions:
            return False
        else:
            self.status = status
            self._refresh_properties()
            return True

    def set_dvfs_mode(self, new_dvfs_mode):
        """
        Sets DVFS mode to a new value
        :param bool new_dvfs_mode: new DVFS mode (False to deactivate, True to activate)
        """
        self.dvfs_mode = new_dvfs_mode
        self._refresh_properties()

    def remove_session(self, service_id, session_id):
        """
        Removes an ongoing task and frees resources
        :param str service_id: ID of the pxsch to be removed
        :param str session_id: ID of the session to be removed
        :return bool: result of the action (True if success)
        """
        if service_id in self.ongoing_sessions:
            session = self.ongoing_sessions[service_id].pop(session_id, None)
            if session is None:
                return False
            else:
                if not self.ongoing_sessions[service_id]:
                    self.ongoing_sessions.pop(service_id)
                self._refresh_properties()
                return True
        else:
            return False

    def create_service(self, service_id, session_id, service_u):
        """
        Earmarks resources for new incoming task
        :param str service_id: ID of the task to be processed
        :param str session_id: ID of the task to be processed
        :param float service_u: Specific utilization factor of the task to be processed
        :return bool: result of the action (True if success)
        """
        # CASE 1: processing unit is switched off
        if not self.status:
            return False
        # CASE 2: new session has invalid size (less than 0)
        elif service_u < 0:
            return False
        # CASE 3: new session cannot be created due to lack of resources
        elif self.utilization + service_u > 100:
            return False
        # CASE 4: new session ID is already in ongoing sessions (it cannot happen)
        elif service_id in self.ongoing_sessions and session_id in self.ongoing_sessions[service_id]:
            raise Exception("New session to be created already exists")
        # CASE 5: new session can be created
        else:
            if service_id not in self.ongoing_sessions:
                self.ongoing_sessions[service_id] = dict()
            self.ongoing_sessions[service_id][session_id] = service_u
            self._refresh_properties()
            return True

    def _refresh_properties(self):
        """Refreshes the values of the processing unit"""
        self.__compute_utilization()
        self.__compute_dvfs_index()
        self.__compute_power()
        self.__compute_temperature()

    def __compute_utilization(self):
        """Computes utilization factor of the processing unit"""
        utilization = 0
        for service, sessions in self.ongoing_sessions.items():
            for session, service_u in sessions.items():
                utilization += service_u
        self.utilization = utilization

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
            dvfs_indexes = [i for i in self.dvfs_table]
            dvfs_indexes.sort()
            index = None
            for dvfs_index in dvfs_indexes:
                if dvfs_index >= self.utilization:
                    index = dvfs_index
                    break
            if index is not None:
                self.dvfs_index = index
            else:
                raise ValueError('Utilization factor is too big for any DVFS configuration')

    def __compute_power(self):
        """Computes the processing unit power consumption"""
        if not self.status or self.power_model is None:
            self.power = 0
        else:
            self.power = self.power_model.compute_power(self.utilization, self.dvfs_index, self.dvfs_table)

    def __compute_temperature(self):
        """Computes the processing unit temperature"""  # TODO implement temperature model
        pass
