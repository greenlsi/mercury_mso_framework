class ProcessingUnitMessage:
    def __init__(self, rack_id: str, pu_index: int):
        self.rack_id = rack_id
        self.pu_index = pu_index


class ProcessingUnitResponseMessage(ProcessingUnitMessage):
    def __init__(self, rack_id: str, pu_index: int, response: bool):
        super().__init__(rack_id, pu_index)
        self.response = response


class ProcessingUnitSessionRequestMessage(ProcessingUnitMessage):
    def __init__(self, rack_id: str, pu_index: int, service_id: str, session_id: str):
        super().__init__(rack_id, pu_index)
        self.pu_index = pu_index
        self.service_id = service_id
        self.session_id = session_id


class ProcessingUnitSessionResponseMessage(ProcessingUnitResponseMessage):
    def __init__(self, rack_id: str, pu_index: int, service_id: str, session_id: str, response: bool):
        super().__init__(rack_id, pu_index, response)
        self.service_id = service_id
        self.session_id = session_id


class ChangeStatus(ProcessingUnitMessage):
    def __init__(self, rack_id: str, pu_index: int, status: bool):
        super().__init__(rack_id, pu_index)
        self.status = status


class SetDVFSMode(ProcessingUnitMessage):
    def __init__(self, rack_id: str, pu_index: int, dvfs_mode: bool):
        super().__init__(rack_id, pu_index)
        self.dvfs_mode = dvfs_mode


class OpenSessionRequest(ProcessingUnitSessionRequestMessage):
    pass


class OngoingSessionRequest(ProcessingUnitSessionRequestMessage):
    def __init__(self, rack_id: str, pu_index: int, service_id: str, session_id: str, packet_id: int):
        super().__init__(rack_id, pu_index, service_id, session_id)
        self.packet_id = packet_id


class CloseSessionRequest(ProcessingUnitSessionRequestMessage):
    pass


class ChangeStatusResponse(ProcessingUnitResponseMessage):
    def __init__(self, rack_id: str, pu_index: int, status: bool, response: bool):
        super().__init__(rack_id, pu_index, response)
        self.status = status


class SetDVFSModeResponse(ProcessingUnitResponseMessage):
    def __init__(self, rack_id: str, pu_index: int, dvfs_mode: bool, response: bool):
        self.dvfs_mode = dvfs_mode
        super().__init__(rack_id, pu_index, response)


class OpenSessionResponse(ProcessingUnitSessionResponseMessage):
    pass


class OngoingSessionResponse(ProcessingUnitSessionResponseMessage):
    def __init__(self, rack_id: str, pu_index: int, service_id: str, session_id: str, packet_id: int, response: bool):
        super().__init__(rack_id, pu_index, service_id, session_id, response)
        self.packet_id = packet_id


class CloseSessionResponse(ProcessingUnitSessionResponseMessage):
    pass


class PowerGenerationReport:
    def __init__(self, source_id: str, generated_power: float):
        self.source_id = source_id
        self.generated_power = generated_power
