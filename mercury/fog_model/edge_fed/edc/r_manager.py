import logging
from collections import deque
from copy import deepcopy
from xdevs.models import Port
from ...common import Stateless, logging_overhead
from ...common.edge_fed.edge_fed import EdgeDataCenterReport
from ...common.edge_fed.r_manager import ResourceManagerConfiguration
from ...common.edge_fed.rack import RackReport
from ...common.packet.apps.service import CreateSessionRequestPacket, RemoveSessionRequestPacket, \
    OngoingSessionRequestPacket, CreateSessionResponsePacket, RemoveSessionResponsePacket, OngoingSessionResponsePacket
from .dispatching import DispatchingStrategyFactory
from .internal_ports import ChangeStatus, ChangeStatusResponse, SetDVFSMode, SetDVFSModeResponse
from .internal_ports import OpenSessionRequest, OpenSessionResponse, OngoingSessionRequest, OngoingSessionResponse, \
    CloseSessionRequest, CloseSessionResponse

LOGGING_OVERHEAD = "            "


class ResourceManager(Stateless):
    """
    Resource Manager XDEVS module
    :param str name: name of the XDEVS model
    :param str edc_id: EDC ID
    :param tuple edc_location: EDC location
    :param ResourceManagerConfiguration r_manager_config: Resource Manager configuration
    :param dict services_config: dictionary of services configuration
    :param float env_temp: resource manager environment temperature
    """
    dispatching_factory = DispatchingStrategyFactory()

    def __init__(self, name: str, edc_id: str, edc_location: tuple, r_manager_config, services_config, env_temp=298):

        # Unwrap configuration parameters
        self.hw_dvfs_mode = r_manager_config.hw_dvfs_mode
        self.hw_power_off = r_manager_config.hw_power_off
        self.n_hot_standby = r_manager_config.n_hot_standby
        disp_strategy_name = r_manager_config.disp_strategy_name
        disp_strategy_config = r_manager_config.disp_strategy_config
        self.disp_strategy = self.dispatching_factory.create_strategy(disp_strategy_name, **disp_strategy_config)

        self.edc_id = edc_id
        self.edc_location = edc_location
        self.services_config = services_config
        self.env_temp = env_temp
        self.power = 0
        self.utilization = 0
        self.edc_max_u = 0

        super().__init__(name=name)

        # Other resource manager properties
        self.rack_reports = dict()

        self.expected_dvfs = dict()
        self.expected_status = dict()
        self.expected_created = dict()
        self.expected_ack = dict()
        self.expected_u = dict()
        self.real_dvfs = dict()
        self.real_status = dict()
        self.real_created = dict()
        self.real_u = dict()
        self.max_u = dict()

        self.starting = dict()
        self.stopping = dict()
        self.acking = dict()

        self.status_queue = dict()  # Changes to be ordered regarding status
        self.dvfs_queue = dict()  # Changes to be ordered regarding DVFS mode
        self.open_queue = dict()  # Create session requests
        self.ack_queue = dict()  # Ongoing session requests
        self.close_queue = dict()  # Remove session requests

        self.pu_blocked = list()

        # Define input/output ports
        self.input_create_session = Port(CreateSessionRequestPacket, name + '_input_create_session')
        self.input_ongoing_session_request = Port(OngoingSessionRequestPacket, name + '_input_ongoing_session_request')
        self.input_remove_session = Port(RemoveSessionRequestPacket, name + '_input_remove_session')
        self.input_racks_report = Port(RackReport, name + '_input_racks_report')
        self.input_change_status_response = Port(ChangeStatusResponse, name + '_input_change_status_response')
        self.input_set_dvfs_mode_response = Port(SetDVFSModeResponse, name + '_input_set_dvfs_mode_response')
        self.input_open_session_response = Port(OpenSessionResponse, name + '_input_open_session_response')
        self.input_ongoing_session_response = Port(OngoingSessionResponse, name + '_input_ongoing_sess_response')
        self.input_close_session_response = Port(CloseSessionResponse, name + '_input_close_session_response')
        self.output_create_session_response = Port(CreateSessionResponsePacket, name + '_output_create_service_resp')
        self.output_ongoing_session_response = Port(OngoingSessionResponsePacket, name + '_output_ongoing_session_resp')
        self.output_remove_session_response = Port(RemoveSessionResponsePacket, name + '_output_remove_service_resp')
        self.output_change_status = Port(ChangeStatus, name + '_output_change_status')
        self.output_set_dvfs_mode = Port(SetDVFSMode, name + '_output_set_dvfs_mode')
        self.output_open_session = Port(OpenSessionRequest, name + '_output_open_session')
        self.output_ongoing_session = Port(OngoingSessionRequest, name + '_output_ongoing_session')
        self.output_close_session = Port(CloseSessionRequest, name + '_output_close_session')
        self.output_edc_report = Port(EdgeDataCenterReport, name + '_output_edc_report')

        self.add_in_port(self.input_create_session)  # port for incoming new pxsch messages
        self.add_in_port(self.input_ongoing_session_request)  #
        self.add_in_port(self.input_remove_session)  # port for incoming remove pxsch messages
        self.add_in_port(self.input_racks_report)  #
        self.add_in_port(self.input_change_status_response)  # port for incoming overall status messages
        self.add_in_port(self.input_set_dvfs_mode_response)  #
        self.add_in_port(self.input_open_session_response)  #
        self.add_in_port(self.input_ongoing_session_response)
        self.add_in_port(self.input_close_session_response)  #
        self.add_out_port(self.output_create_session_response)  # port for leaving power report messages
        self.add_out_port(self.output_ongoing_session_response)  #
        self.add_out_port(self.output_remove_session_response)  # port for leaving created pxsch messages
        self.add_out_port(self.output_change_status)  # port for leaving change status messages
        self.add_out_port(self.output_set_dvfs_mode)  # port for leaving new property messages
        self.add_out_port(self.output_open_session)  # port for leaving free task messages
        self.add_out_port(self.output_ongoing_session)
        self.add_out_port(self.output_close_session)  # port for leaving new tasks messages
        self.add_out_port(self.output_edc_report)  # port for leaving new tasks messages

    def check_in_ports(self):
        self.check_rack_reports()
        self.trigger_dispatching()
        self.trigger_scheduling()

    def process_internal_messages(self):
        pass

    def check_rack_reports(self):
        if self.input_racks_report:
            for rack_report in self.input_racks_report.values:
                rack_id = rack_report.rack_id
                if rack_id not in self.max_u:
                    self._discover_rack(rack_id, rack_report)
                else:
                    for pu_index, pu_report in rack_report.pu_report_list.items():
                        if pu_index not in self.max_u[rack_id]:
                            self._discover_pu(rack_id, pu_index, pu_report)
                self.rack_reports[rack_id] = deepcopy(rack_report)
            self.send_edc_report()

    def _discover_rack(self, rack_id, rack_report):
        to_fill = [self.expected_dvfs, self.expected_status, self.expected_created, self.expected_ack, self.expected_u,
                   self.real_dvfs, self.real_status, self.real_created, self.real_u, self.max_u, self.starting,
                   self.stopping, self.acking]
        for fill in to_fill:
            fill[rack_id] = dict()
        for pu_index, pu_report in rack_report.pu_report_list.items():
            self._discover_pu(rack_id, pu_index, pu_report)

    def _discover_pu(self, rack_id, pu_index, pu_report):
        self.expected_dvfs[rack_id][pu_index] = pu_report.dvfs_mode
        self.real_dvfs[rack_id][pu_index] = pu_report.dvfs_mode
        self.expected_status[rack_id][pu_index] = pu_report.status
        self.real_status[rack_id][pu_index] = pu_report.status
        self.expected_created[rack_id][pu_index] = list()
        self.expected_ack[rack_id][pu_index] = list()
        self.real_created[rack_id][pu_index] = list()
        for service_id, sessions in pu_report.ongoing_sessions.items():
            for session_id in sessions:
                self.expected_created[rack_id][pu_index].append((service_id, session_id))
                self.real_created[rack_id][pu_index].append((service_id, session_id))
        self.expected_u[rack_id][pu_index] = pu_report.utilization
        self.real_u[rack_id][pu_index] = pu_report.utilization
        self.max_u[rack_id][pu_index] = pu_report.max_u
        self.starting[rack_id][pu_index] = list()
        self.stopping[rack_id][pu_index] = list()
        self.acking[rack_id][pu_index] = list()

    def trigger_dispatching(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        self._check_pu_ports(overhead)
        self._check_ongoing_session_port(overhead)
        self._check_remove_session_port(overhead)
        self._check_create_session_port(overhead)
        self._check_p_units_status_and_dvfs_mode(overhead)

    def trigger_scheduling(self):
        to_delete = list()
        # 1. Check new DVFS modes
        for label, new_dvfs_mode in self.dvfs_queue.items():
            rack_id, pu_index = label
            if not self.strong_blocking(rack_id, pu_index):
                msg = SetDVFSMode(rack_id, pu_index, new_dvfs_mode)
                self.add_msg_to_queue(self.output_set_dvfs_mode, msg)
                self.pu_blocked.append(label)
                to_delete.append(label)
        for label in to_delete:
            self.dvfs_queue.pop(label)
        to_delete.clear()
        # 2. Check new Switch on commands
        for label, new_status in self.status_queue.items():
            rack_id, pu_index = label
            if new_status and not self.strong_blocking(rack_id, pu_index):
                msg = ChangeStatus(rack_id, pu_index, new_status)
                self.add_msg_to_queue(self.output_change_status, msg)
                self.pu_blocked.append(label)
                to_delete.append(label)
        for label in to_delete:
            self.status_queue.pop(label)
        to_delete.clear()
        # 3. Check ongoing session requests
        for label, to_ongoing in self.ack_queue.items():
            rack_id, pu_index = label
            if label not in self.pu_blocked:
                to_delete.append(label)
                for req in to_ongoing:
                    service_id, session_id, packet_id = req
                    msg = OngoingSessionRequest(rack_id, pu_index, service_id, session_id, packet_id)
                    self.add_msg_to_queue(self.output_ongoing_session, msg)
                    self.acking[rack_id][pu_index].append(req)
        for label in to_delete:
            self.ack_queue.pop(label)
        to_delete.clear()
        # 4. Check new session removals
        for label, to_remove in self.close_queue.items():
            rack_id, pu_index = label
            if (rack_id, pu_index) not in self.pu_blocked:
                to_delete.append(label)
                for req in to_remove:
                    service_id, session_id = req
                    msg = CloseSessionRequest(rack_id, pu_index, service_id, session_id)
                    self.add_msg_to_queue(self.output_close_session, msg)
                    self.stopping[label[0]][label[1]].append(req)
        for label in to_delete:
            self.close_queue.pop(label)
        to_delete.clear()
        # 5. Check new session creations
        for label, to_create in self.open_queue.items():
            rack_id, pu_index = label
            if (rack_id, pu_index) not in self.pu_blocked:
                to_delete.append(label)
                for req in to_create:
                    service_id, session_id = req
                    msg = OpenSessionRequest(rack_id, pu_index, service_id, session_id)
                    self.add_msg_to_queue(self.output_open_session, msg)
                    self.starting[rack_id][pu_index].append(req)
        for label in to_delete:
            self.open_queue.pop(label)
        to_delete.clear()
        # 6. Check new Switch off commands
        for label, new_status in self.status_queue.items():
            rack_id, pu_index = label
            if not new_status and not self.strong_blocking(rack_id, pu_index):
                msg = ChangeStatus(rack_id, pu_index, new_status)
                self.add_msg_to_queue(self.output_change_status, msg)
                to_delete.append(label)
                self.pu_blocked.append(label)
        for label in to_delete:
            self.status_queue.pop(label)

    def strong_blocking(self, rack_id, pu_index):
        return (rack_id, pu_index) in self.pu_blocked or self.acking[rack_id][pu_index] \
               or self.starting[rack_id][pu_index] or self.stopping[rack_id][pu_index]

    def send_edc_report(self):
        self._recompute_edc_status()
        msg = EdgeDataCenterReport(self.edc_id, self.edc_location, self.utilization, self.edc_max_u, self.power,
                                   self.env_temp, self.rack_reports)
        self.add_msg_to_queue(self.output_edc_report, msg)

    def _recompute_edc_status(self):
        power = 0
        std_u = 0
        max_std_u = 0
        for rack_id, rack_report in self.rack_reports.items():
            power += rack_report.overall_power
            std_u += rack_report.utilization
            max_std_u += rack_report.max_u
        self.power = power
        self.utilization = std_u
        self.edc_max_u = max_std_u

    def _check_pu_ports(self, overhead):
        for msg in self.input_ongoing_session_response.values:
            rack_id = msg.rack_id
            pu_index = msg.pu_index
            service_id = msg.service_id
            session_id = msg.session_id
            packet_id = msg.packet_id
            response = msg.response
            logging.info(overhead + "%s received Ongoing Session (%s,%s,%s) response: %s" % (self.name, service_id,
                                                                                             session_id, str(packet_id),
                                                                                             response))
            self.acking[rack_id][pu_index].remove((service_id, session_id, packet_id))
            self.expected_ack[rack_id][pu_index].remove((service_id, session_id))
            service_header = self.services_config[service_id].header
            msg = OngoingSessionResponsePacket(service_id, session_id, response, service_header, packet_id)
            self.add_msg_to_queue(self.output_ongoing_session_response, msg)

        for msg in self.input_open_session_response.values:
            rack_id = msg.rack_id
            pu_index = msg.pu_index
            service_id = msg.service_id
            session_id = msg.session_id
            response = msg.response
            logging.info(overhead + "%s received Open Session (%s,%s) response: %s" % (self.name, service_id,
                                                                                       session_id, response))
            utilization = self.services_config[service_id].service_u
            if response:
                self.real_u[rack_id][pu_index] += utilization
                self.real_created[rack_id][pu_index].append((service_id, session_id))
            else:
                self.expected_u[rack_id][pu_index] -= utilization
                self.expected_created[rack_id][pu_index].remove((service_id, session_id))
            self.starting[rack_id][pu_index].remove((service_id, session_id))
            header = self.services_config[service_id].header
            msg = CreateSessionResponsePacket(service_id, session_id, response, header)
            self.add_msg_to_queue(self.output_create_session_response, msg)

        for msg in self.input_close_session_response.values:
            rack_id = msg.rack_id
            pu_index = msg.pu_index
            service_id = msg.service_id
            session_id = msg.session_id
            response = msg.response
            logging.info(overhead + "%s received Close Session (%s,%s) response: %s" % (self.name, service_id,
                                                                                        session_id, response))
            utilization = self.services_config[service_id].service_u
            if response:  # If successfully created, add it to created list
                self.real_u[rack_id][pu_index] -= utilization
                self.real_created[rack_id][pu_index].remove((service_id, session_id))
            else:
                self.expected_u[rack_id][pu_index] += utilization
                self.expected_created[rack_id][pu_index].append((service_id, session_id))
            self.stopping[rack_id][pu_index].remove((service_id, session_id))
            header = self.services_config[service_id].header
            msg = RemoveSessionResponsePacket(service_id, session_id, response, header)
            self.add_msg_to_queue(self.output_remove_session_response, msg)

        for msg in self.input_change_status_response.values:
            rack_id = msg.rack_id
            pu_index = msg.pu_index
            status = msg.status
            response = msg.response
            assert response  # Change status should never fail
            self.pu_blocked.remove((rack_id, pu_index))
            self.real_status[rack_id][pu_index] = status
            logging.info(overhead + "%s received from PU Change Status %s response: %s" % (self.name, status, response))

        for msg in self.input_set_dvfs_mode_response.values:
            rack_id = msg.rack_id
            pu_index = msg.pu_index
            dvfs_mode = msg.dvfs_mode
            response = msg.response
            assert response  # Change DVFS mode should never fail
            self.pu_blocked.remove((rack_id, pu_index))
            self.real_dvfs[rack_id][pu_index] = dvfs_mode
            logging.info(overhead + "%s received Set DVFS mode %s response: %s" % (self.name, dvfs_mode, response))

    def _check_ongoing_session_port(self, overhead):
        """Process incoming ongoing session requests"""
        for job in self.input_ongoing_session_request.values:
            service_id = job.service_id
            session_id = job.session_id
            packet_id = job.packet_id
            logging.info(overhead + "%s received ongoing session (%s,%s,%s) request" % (self.name, service_id,
                                                                                        session_id, str(packet_id)))
            try:
                rack_id, pu_index = self.__find_pu_with_session(self.real_created, service_id, session_id)
            except TypeError:
                logging.warning(overhead + "    Session could not be found. Sending negative response")
                header = self.services_config[service_id].header
                msg = OngoingSessionResponsePacket(service_id, session_id, False, header, packet_id)
                self.add_msg_to_queue(self.output_ongoing_session_response, msg)
            else:
                logging.info(overhead + "    session found at processing unit ({},{})".format(rack_id, pu_index))
                if (service_id, session_id) not in self.expected_created[rack_id][pu_index]:
                    logging.warning(overhead + "    Session is being removed. Sending negative response")
                    header = self.services_config[service_id].header
                    msg = OngoingSessionResponsePacket(service_id, session_id, False, header, packet_id)
                    self.add_msg_to_queue(self.output_ongoing_session_response, msg)
                else:
                    self._ongoing_session(rack_id, pu_index, service_id, session_id, packet_id)

    def _check_remove_session_port(self, overhead):
        """Process incoming remove service requests"""
        for job in self.input_remove_session.values:
            service_id = job.service_id
            session_id = job.session_id
            logging.info(overhead + "%s received remove session (%s,%s) request" % (self.name, service_id, session_id))
            try:
                rack_id, pu_index = self.__find_pu_with_session(self.real_created, service_id, session_id)
            except TypeError:
                # If simulator reaches this point, the service is not in any processing unit
                logging.warning(overhead + "    Session to remove could not be found. Sending affirmative response")
                header = self.services_config[service_id].header
                msg = RemoveSessionResponsePacket(service_id, session_id, True, header)
                self.add_msg_to_queue(self.output_remove_session_response, msg)
            else:
                logging.info(overhead + "    session found at PU ({},{})".format(rack_id, pu_index))
                if (service_id, session_id) not in self.expected_created[rack_id][pu_index]:
                    logging.warning(overhead + "    Session is already being removed. Ignoring duplicate")
                elif (service_id, session_id) in self.expected_ack[rack_id][pu_index]:
                    logging.warning(overhead + "    Session is busy acknowledging data. Sending negative response")
                    header = self.services_config[service_id].header
                    msg = OngoingSessionResponsePacket(service_id, session_id, False, header)
                    self.add_msg_to_queue(self.output_ongoing_session_response, msg)
                else:
                    self._close_session(rack_id, pu_index, service_id, session_id)

    def _check_create_session_port(self, overhead):
        """Process incoming create service requests"""
        for job in self.input_create_session.values:
            service_id = job.service_id
            session_id = job.session_id
            utilization = self.services_config[service_id].service_u
            logging.info(overhead + "%s received create session (%s,%s) request" % (self.name, service_id, session_id))
            # 1. Check that service is not already deployed
            try:
                _, _ = self.__find_pu_with_session(self.real_created, service_id, session_id)
                logging.warning(overhead + "    Service already created. Returning affirmative response")
                header = self.services_config[service_id]
                msg = CreateSessionResponsePacket(service_id, session_id, True, header)
                self.add_msg_to_queue(self.output_create_session_response, msg)
            except TypeError:
                try:
                    _, _ = self.__find_pu_with_session(self.expected_created, service_id, session_id)
                    logging.warning(overhead + "    Service already being created. Ignoring duplicate")
                except TypeError:
                    # 2. Look for processing unit to allocate the service
                    rack_id, pu_index = self.disp_strategy.allocate_task(service_id, session_id, utilization,
                                                                         self.expected_u, self.max_u)
                    # CASE 2.1: There are not enough resources
                    if rack_id is None or pu_index is None:
                        logging.warning(overhead + "    Session could not be created. Sending negative response")
                        header = self.services_config[service_id]
                        msg = CreateSessionResponsePacket(service_id, session_id, False, header)
                        self.add_msg_to_queue(self.output_create_session_response, msg)
                    # CASE 2.2: There are enough resources
                    else:
                        logging.info(overhead + "    Service to be deployed in PU ({},{})".format(rack_id, pu_index))
                        self._open_session(rack_id, pu_index, service_id, session_id)

    def _check_p_units_status_and_dvfs_mode(self, overhead):
        # If processing unit is empty, proceed to power it off (if applies)
        new_status = self.disp_strategy.change_p_units_status(self.expected_created, self.max_u, self.hw_power_off,
                                                              self.n_hot_standby)
        for rack_id, p_units in new_status.items():
            for pu_index, status in p_units.items():
                if status != self.expected_status[rack_id][pu_index]:
                    logging.info(overhead + "    Status of processing unit ({},{}) needs to be changed to {}"
                                 .format(rack_id, pu_index, status))
                    self._change_status(rack_id, pu_index, status)

        new_dvfs = self.disp_strategy.set_dvfs_mode(self.expected_dvfs, self.hw_dvfs_mode)
        for rack_id, p_units in new_dvfs.items():
            for pu_index, dvfs_mode in p_units.items():
                logging.info(overhead + "    DVFS mode of processing unit ({},{}) needs to be changed to {}"
                             .format(rack_id, pu_index, dvfs_mode))
                self._set_dvfs_mode(rack_id, pu_index, dvfs_mode)

    def _ongoing_session(self, rack_id, pu_index, service_id, session_id, packet_id):
        self.expected_ack[rack_id][pu_index].append((service_id, session_id))
        try:
            self.ack_queue[(rack_id, pu_index)].append((service_id, session_id, packet_id))
        except KeyError:
            self.ack_queue[(rack_id, pu_index)] = deque([(service_id, session_id, packet_id)])

    def _close_session(self, rack_id, pu_index, service_id, session_id):
        service_u = self.services_config[service_id].service_u
        self.expected_created[rack_id][pu_index].remove((service_id, session_id))
        self.expected_u[rack_id][pu_index] -= service_u
        try:
            self.close_queue[(rack_id, pu_index)].append((service_id, session_id))
        except KeyError:
            self.close_queue[(rack_id, pu_index)] = deque([(service_id, session_id)])

    def _open_session(self, rack_id, pu_index, service_id, session_id):
        service_u = self.services_config[service_id].service_u
        self.expected_created[rack_id][pu_index].append((service_id, session_id))
        self.expected_u[rack_id][pu_index] += service_u
        try:
            self.open_queue[(rack_id, pu_index)].append((service_id, session_id))
        except KeyError:
            self.open_queue[(rack_id, pu_index)] = deque([(service_id, session_id)])

    def _change_status(self, rack_id, pu_index, status):
        """
        Change the virtual status of a given processing unit and puts in queue the order
        :param str rack_id: ID of the rack that contains the processing unit
        :param int pu_index: index of the target processing unit
        :param bool status: new processing unit status (False for switching off, True for switching on)
        """
        self.expected_status[rack_id][pu_index] = status
        self.status_queue[(rack_id, pu_index)] = status

    def _set_dvfs_mode(self, rack_id, pu_index, dvfs_mode):
        """
        Change the virtual DVFS mode of a given processing unit and puts in queue the order
        :param str rack_id: ID of the rack that contains the processing unit
        :param int pu_index: index of the target processing unit
        :param bool dvfs_mode: new processing unit status (False for switching off, True for switching on)
        """
        self.expected_dvfs[(rack_id, pu_index)] = dvfs_mode
        self.dvfs_queue[(rack_id, pu_index)] = dvfs_mode

    @staticmethod
    def __find_pu_with_session(session_list, service_id, session_id):
        for rack_id, p_units in session_list.items():
            for pu_index, sessions in p_units.items():
                if (service_id, session_id) in sessions:
                    return rack_id, pu_index
