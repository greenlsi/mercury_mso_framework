from ...application import ApplicationPacket


class RANAccessControlPacket(ApplicationPacket):
    def __init__(self, ap_id, ue_id, header=0):
        super().__init__(header)
        self.ap_id = ap_id
        self.ue_id = ue_id


class RANAccessControlRequest(RANAccessControlPacket):
    pass


class RANAccessControlResponse(RANAccessControlPacket):
    def __init__(self, ap_id, ue_id, response, header=0):
        super().__init__(ap_id, ue_id, header)
        self.response = response


class CreatePathRequest(RANAccessControlRequest):
    pass


class RemovePathRequest(RANAccessControlRequest):
    pass


class SwitchPathRequest(RANAccessControlRequest):
    def __init__(self, ap_id, ue_id, prev_ap_id, header=0):
        super().__init__(ap_id, ue_id, header)
        self.prev_ap_id = prev_ap_id


class CreatePathResponse(RANAccessControlResponse):
    pass


class RemovePathResponse(RANAccessControlResponse):
    pass


class SwitchPathResponse(RANAccessControlResponse):
    def __init__(self, ap_id, ue_id, prev_ap_id, response, header=0):
        super().__init__(ap_id, ue_id, response, header)
        self.prev_ap_id = prev_ap_id
