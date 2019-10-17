import logging
from copy import deepcopy
from collections import deque
from xdevs.models import Port, INFINITY
from ...common import FiniteStateMachine, logging_overhead
from ...common.edge_fed import ResourceManagerConfiguration, ProcessingUnitReport
from .internal_ports import CreateSession, RemoveSession, CreateSessionResponse, RemoveSessionResponse
from .internal_ports import ChangeStatus, ChangeStatusResponse, SetDVFSMode, SetDVFSModeResponse
from .internal_ports import OpenSession, OpenSessionResponse, CloseSession, CloseSessionResponse
from .internal_ports import EDCOverallReport


PHASE_INIT = 'init'
PHASE_IDLE = 'idle'
R_MANAGER_PHASES = [PHASE_INIT, PHASE_IDLE]

LOGGING_OVERHEAD = "            "


class ResourceManager(FiniteStateMachine):
    def __init__(self, name, resource_manager_config, p_units, base_temp=298):
        """
        Resource Manager XDEVS module
        :param str name: name of the XDEVS model
        :param ResourceManagerConfiguration resource_manager_config: Resource Manager configuration
        :param list p_units: list of processing units [(p_unit_id, std_to_spec)]
        :param float base_temp: resource manager base temperature
        """
        # Unwrap configuration parameters
        self.hw_dvfs_mode = resource_manager_config.hw_dvfs_mode
        self.hw_power_off = resource_manager_config.hw_power_off
        self.disp_strategy = resource_manager_config.disp_strategy

        # FSM stuff
        int_table = {
            PHASE_INIT: self.internal_phase_init,
            PHASE_IDLE: self.internal_phase_idle,
        }
        ext_table = {
            PHASE_INIT: self.external_phase_idle,
            PHASE_IDLE: self.external_phase_idle,
        }
        lambda_table = {
            PHASE_INIT: self.lambda_phase_init,
            PHASE_IDLE: self.lambda_phase_idle,
        }
        initial_state = PHASE_INIT
        initial_timeout = 0
        super().__init__(R_MANAGER_PHASES, int_table, ext_table, lambda_table, initial_state, initial_timeout, name)

        # Other resource manager properties
        self.n_pu = len(p_units)
        self.pu_std_to_spec = [p_unit[1] for p_unit in p_units]
        self.pu_reports = [ProcessingUnitReport(p_unit[0], p_unit[1], False, False, 0, 0, 0, base_temp, dict()) for p_unit in p_units]
        self.pu_reports_mirror = deepcopy(self.pu_reports)

        self.pu_status = [None for _ in range(self.n_pu)]               # Changes to be ordered regarding status
        self.pu_dvfs_mode = [None for _ in range(self.n_pu)]            # Changes to be ordered regarding DVFS mode
        self.pu_create_session = [deque() for _ in range(self.n_pu)]    # Create session requests
        self.pu_remove_session = [deque() for _ in range(self.n_pu)]    # Remove session requests
        self.pu_blocked = [False for _ in range(self.n_pu)]             # to record which processing unit is locked

        # Define input/output ports
        self.input_create_session = Port(CreateSession, name + '_input_create_session')
        self.input_remove_session = Port(RemoveSession, name + '_input_remove_session')
        self.input_change_status_response = Port(ChangeStatusResponse, name + '_input_change_status_response')
        self.input_set_dvfs_mode_response = Port(SetDVFSModeResponse, name + '_input_set_dvfs_mode_response')
        self.input_open_session_response = Port(OpenSessionResponse, name + '_input_open_session_response')
        self.input_close_session_response = Port(CloseSessionResponse, name + '_input_close_session_response')
        self.output_create_session_response = Port(CreateSessionResponse, name + '_output_create_service_response')
        self.output_remove_session_response = Port(RemoveSessionResponse, name + '_output_remove_service_response')
        self.output_change_status = Port(ChangeStatus, name + '_output_change_status')
        self.output_set_dvfs_mode = Port(SetDVFSMode, name + '_output_set_dvfs_mode')
        self.output_open_session = Port(OpenSession, name + '_output_open_session')
        self.output_close_session = Port(CloseSession, name + '_output_close_session')
        self.output_overall_report = Port(EDCOverallReport, name + '_output_overall_report')

        self.add_in_port(self.input_create_session)             # port for incoming new pxsch messages
        self.add_in_port(self.input_remove_session)             # port for incoming remove pxsch messages
        self.add_in_port(self.input_change_status_response)     # port for incoming overall status messages
        self.add_in_port(self.input_set_dvfs_mode_response)     #
        self.add_in_port(self.input_open_session_response)      #
        self.add_in_port(self.input_close_session_response)     #
        self.add_out_port(self.output_create_session_response)  # port for leaving power report messages
        self.add_out_port(self.output_remove_session_response)  # port for leaving created pxsch messages
        self.add_out_port(self.output_change_status)            # port for leaving change status messages
        self.add_out_port(self.output_set_dvfs_mode)            # port for leaving new property messages
        self.add_out_port(self.output_open_session)             # port for leaving free task messages
        self.add_out_port(self.output_close_session)            # port for leaving new tasks messages
        self.add_out_port(self.output_overall_report)           # port for leaving new tasks messages

    def internal_phase_init(self):
        return PHASE_IDLE, INFINITY

    def internal_phase_idle(self):
        return PHASE_IDLE, INFINITY

    def external_phase_idle(self):
        self.trigger_dispatching()
        self.trigger_scheduling()
        if self.msg_queue_empty():
            return PHASE_IDLE, INFINITY
        else:
            return PHASE_IDLE, 0

    def lambda_phase_init(self):
        self.trigger_initial_dispatching()
        self.trigger_scheduling()

    def lambda_phase_idle(self):
        pass

    def trigger_initial_dispatching(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        self._check_p_units_status_and_dvfs_mode(overhead)
        msg = EDCOverallReport(self.pu_reports)
        self.add_msg_to_queue(self.output_overall_report, msg)

    def trigger_dispatching(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        flag = self._check_p_units_ports(overhead)
        if flag:
            msg = EDCOverallReport(self.pu_reports)
            self.add_msg_to_queue(self.output_overall_report, msg)
        self._check_remove_session_port(overhead)
        self._check_create_session_port(overhead)
        self._check_p_units_status_and_dvfs_mode(overhead)

    def trigger_scheduling(self):
        for pu_index in range(self.n_pu):
            # If processing unit is blocked, go to another processing unit
            if self.pu_blocked[pu_index]:
                continue
            # Otherwise, check if there is any pending operation
            flag = False
            new_status = self.pu_status[pu_index]
            new_dvfs_mode = self.pu_dvfs_mode[pu_index]
            sessions_to_remove = self.pu_remove_session[pu_index]
            sessions_to_create = self.pu_create_session[pu_index]
            if new_dvfs_mode is not None:
                flag = True
                msg = SetDVFSMode(pu_index, new_dvfs_mode)
                self.add_msg_to_queue(self.output_set_dvfs_mode, msg)
                self.pu_dvfs_mode[pu_index] = None
            elif new_status:
                flag = True
                msg = ChangeStatus(pu_index, new_status)
                self.add_msg_to_queue(self.output_change_status, msg)
                self.pu_status[pu_index] = None
            elif sessions_to_remove:
                flag = True
                session = sessions_to_remove.popleft()
                msg = CloseSession(pu_index, session[0], session[1])
                self.add_msg_to_queue(self.output_close_session, msg)
            elif sessions_to_create:
                flag = True
                session = sessions_to_create.popleft()
                msg = OpenSession(pu_index, session[0], session[1], session[2])
                self.add_msg_to_queue(self.output_open_session, msg)
            elif new_status is not None:
                flag = True
                msg = ChangeStatus(pu_index, new_status)
                self.add_msg_to_queue(self.output_change_status, msg)
                self.pu_status[pu_index] = None
            else:
                pass  # Everything up to date TODO check that mirror is the same?
            # If applies, block processing unit
            self.pu_blocked[pu_index] = flag

    def _check_p_units_ports(self, overhead):
        flag = False

        for msg in self.input_open_session_response.values:
            flag = True
            pu_index = msg.pu_index
            service_id = msg.service_id
            session_id = msg.session_id
            response = msg.response
            report = msg.report
            logging.info(overhead + "%s received Open Session (%s,%s) response: %s" % (self.name, service_id, session_id, response))
            if not response:
                raise Exception("Session could not be opened in processing unit")
            self.pu_blocked[pu_index] = False
            self.pu_reports[pu_index] = deepcopy(report)
            msg = CreateSessionResponse(service_id, session_id, response)
            self.add_msg_to_queue(self.output_create_session_response, msg)

        for msg in self.input_close_session_response.values:
            flag = True
            pu_index = msg.pu_index
            service_id = msg.service_id
            session_id = msg.session_id
            response = msg.response
            report = msg.report
            logging.info(overhead + "%s received Close Session (%s,%s) response: %s" % (self.name, service_id, session_id, response))
            if not response:
                raise Exception("Session could not be closed in processing unit")
            self.pu_blocked[pu_index] = False
            self.pu_reports[pu_index] = deepcopy(report)
            msg = RemoveSessionResponse(service_id, session_id, response)
            self.add_msg_to_queue(self.output_remove_session_response, msg)

        for msg in self.input_change_status_response.values:
            flag = True
            pu_index = msg.pu_index
            response = msg.response
            report = msg.report
            status = report.status
            logging.info(overhead + "%s received Change Status %s response: %s" % (self.name, status, response))
            if not response:
                raise Exception("Processing unit could not change its status")
            self.pu_blocked[pu_index] = False
            self.pu_reports[pu_index] = deepcopy(report)

        for msg in self.input_set_dvfs_mode_response.values:
            flag = True
            pu_index = msg.pu_index
            response = msg.response
            report = msg.report
            dvfs_mode = report.dvfs_mode
            logging.info(overhead + "%s received Set DVFS mode %s response: %s" % (self.name, dvfs_mode, response))
            if not response:
                raise Exception("Processing unit could not be switched off")
            self.pu_blocked[pu_index] = False
            self.pu_reports[pu_index] = deepcopy(report)

        return flag

    def _check_remove_session_port(self, overhead):
        """Process incoming remove pxsch requests"""
        for job in self.input_remove_session.values:
            service_id = job.service_id
            session_id = job.session_id
            logging.info(overhead + "%s received remove session (%s,%s) request" % (self.name, service_id, session_id))

            pu_index = self.__find_pu_with_session(service_id, session_id)
            if pu_index is not None:
                logging.info(overhead + "    session found at processing unit %d" % pu_index)
                self._close_session(pu_index, service_id, session_id)
            else:
                # If simulator reaches this point, the pxsch is not in any processing unit
                logging.warning(overhead + "    Session to remove was not found. Returning affirmative response")
                msg = RemoveSessionResponse(service_id, session_id, True)
                self.add_msg_to_queue(self.output_remove_session_response, msg)

    def _check_create_session_port(self, overhead):
        """Process incoming create pxsch requests"""
        for job in self.input_create_session.values:
            service_id = job.service_id
            session_id = job.session_id
            std_u = job.service_u
            logging.info(overhead + "%s received create session (%s,%s, %.2f) request" % (self.name, service_id, session_id, std_u))

            # 1. Check that pxsch is not already deployed
            pu_index = self.__find_pu_with_session(service_id, session_id)
            if pu_index is not None:
                logging.warning(overhead + "    Service already created. Returning affirmative response")
                msg = CreateSessionResponse(service_id, session_id, True)
                self.add_msg_to_queue(self.output_create_session_response, msg)
                continue
            # 2. Look for processing unit to allocate the pxsch
            pu_index = self.disp_strategy.allocate_task(service_id, session_id, std_u, self.pu_reports_mirror)
            # CASE 2.1: There are not enough resources
            if pu_index is None:
                logging.warning(overhead + "    Data center has not enough resources. Returning negative response")
                msg = CreateSessionResponse(service_id, session_id, False)
                self.add_msg_to_queue(self.output_create_session_response, msg)
            # CASE 2.2: There are enough resources
            else:
                logging.info(overhead + "    Service to be deployed in processing unit %d" % pu_index)
                spec_u = self.pu_std_to_spec[pu_index] * std_u
                self._open_session(pu_index, service_id, session_id, spec_u)

    def _check_p_units_status_and_dvfs_mode(self, overhead):
        # If processing unit is empty, proceed to power it off (if applies)
        new_status = self.disp_strategy.change_p_units_status(self.pu_reports_mirror, self.hw_power_off)
        new_dvfs_mode = self.disp_strategy.set_dvfs_mode(self.pu_reports_mirror, self.hw_dvfs_mode)
        for pu_index in range(self.n_pu):
            status = new_status[pu_index]
            dvfs_mode = new_dvfs_mode[pu_index]
            if self._change_status(pu_index, status):
                logging.info(overhead + "    Processing unit's status needs to be changed to %s" % status)
            if self._set_dvfs_mode(pu_index, dvfs_mode):
                logging.info(overhead + "    Processing unit's DVFS mode needs to be changed to %s" % dvfs_mode)

    def _close_session(self, pu_index, service_id, session_id):
        ongoing_sessions = self.pu_reports_mirror[pu_index].ongoing_sessions
        spec_u = ongoing_sessions[service_id].pop(session_id)
        if not ongoing_sessions[service_id]:
            ongoing_sessions.pop(service_id)
        self.pu_reports_mirror[pu_index].utilization = self.__compute_utilization(ongoing_sessions)
        try:
            self.pu_create_session[pu_index].remove((service_id, session_id, spec_u))
            self.add_msg_to_queue(self.output_create_session_response, CreateSessionResponse(service_id, session_id, False))
            self.add_msg_to_queue(self.output_remove_session_response, RemoveSessionResponse(service_id, session_id, True))
        except ValueError:
            self.pu_remove_session[pu_index].append((service_id, session_id))

    def _open_session(self, pu_index, service_id, session_id, service_u):
        ongoing_sessions = self.pu_reports_mirror[pu_index].ongoing_sessions
        if service_id not in ongoing_sessions:
            ongoing_sessions[service_id] = dict()
        ongoing_sessions[service_id][session_id] = service_u
        self.pu_reports_mirror[pu_index].utilization = self.__compute_utilization(ongoing_sessions)
        self.pu_create_session[pu_index].append((service_id, session_id, service_u))

    def _change_status(self, pu_index, status):
        """
        Change the virtual status of a given processing unit and puts in queue the order
        :param int pu_index: index of the target processing unit
        :param bool status: new processing unit status (False for switching off, True for switching on)
        :return: False if change is not possible;True if change is possible
        """
        res = False
        # Check if it is possible to change the processing unit status
        if self.pu_reports_mirror[pu_index].status != status:
            res = status or not self.pu_reports_mirror[pu_index].ongoing_sessions
        # If change is possible, change mirror and add action to buffer
        if res:
            self.pu_reports_mirror[pu_index].status = status
            self.pu_status[pu_index] = status
        return res

    def _set_dvfs_mode(self, pu_index, dvfs_mode):
        """
        Change the virtual DVFS mode of a given processing unit and puts in queue the order
        :param int pu_index: index of the target processing unit
        :param bool dvfs_mode: new processing unit status (False for switching off, True for switching on)
        :return: False if change is not possible;True if change is possible
        """
        res = self.pu_reports_mirror[pu_index].dvfs_mode != dvfs_mode
        if res:
            self.pu_reports_mirror[pu_index].dvfs_mode = dvfs_mode
            if not dvfs_mode:
                self.pu_reports_mirror[pu_index].dvfs_index = 100
            self.pu_dvfs_mode[pu_index] = dvfs_mode
        return res

    @staticmethod
    def __compute_utilization(ongoing_sessions):
        utilization = 0
        for _, sessions in ongoing_sessions.items():
            for _, service_u in sessions.items():
                utilization += service_u
        return utilization

    def __find_pu_with_session(self, service_id, session_id):
        for pu_index in range(self.n_pu):
            ongoing_sessions = self.pu_reports_mirror[pu_index].ongoing_sessions
            if service_id in ongoing_sessions and session_id in ongoing_sessions[service_id]:
                return pu_index
        return None
