class SessionMessage:
    def __init__(self, service_id, session_id):
        self.service_id = service_id
        self.session_id = session_id


class SessionResponseMessage(SessionMessage):
    def __init__(self, service_id, session_id, response):
        super().__init__(service_id, session_id)
        self.response = response


class CreateSession(SessionMessage):
    def __init__(self, service_id, session_id, service_u):
        super().__init__(service_id, session_id)
        self.service_u = service_u


class RemoveSession(SessionMessage):
    pass


class CreateSessionResponse(SessionResponseMessage):
    pass


class RemoveSessionResponse(SessionResponseMessage):
    pass


class ProcessingUnitMessage:
    def __init__(self, pu_index):
        self.pu_index = pu_index


class ProcessingUnitResponseMessage(ProcessingUnitMessage):
    def __init__(self, pu_index, response, report):
        super().__init__(pu_index)
        self.response = response
        self.report = report


class ProcessingUnitSessionMessage:
    def __init__(self, pu_index, service_id, session_id):
        self.pu_index = pu_index
        self.service_id = service_id
        self.session_id = session_id


class ProcessingUnitSessionResponseMessage(ProcessingUnitResponseMessage):
    def __init__(self, pu_index, service_id, session_id, response, report):
        super().__init__(pu_index, response, report)
        self.service_id = service_id
        self.session_id = session_id


class ChangeStatus(ProcessingUnitMessage):
    def __init__(self, pu_index, status):
        super().__init__(pu_index)
        self.status = status


class SetDVFSMode(ProcessingUnitMessage):
    def __init__(self, pu_index, dvfs_mode):
        super().__init__(pu_index)
        self.dvfs_mode = dvfs_mode


class OpenSession(ProcessingUnitSessionMessage):
    def __init__(self, pu_index, service_id, session_id, service_u):
        super().__init__(pu_index, service_id, session_id)
        self.service_u = service_u


class CloseSession(ProcessingUnitSessionMessage):
    pass


class ChangeStatusResponse(ProcessingUnitResponseMessage):
    pass


class SetDVFSModeResponse(ProcessingUnitResponseMessage):
    pass


class OpenSessionResponse(ProcessingUnitSessionResponseMessage):
    pass


class CloseSessionResponse(ProcessingUnitSessionResponseMessage):
    pass


class EDCOverallReport:
    def __init__(self, p_units_reports):
        self.p_units_reports = p_units_reports
