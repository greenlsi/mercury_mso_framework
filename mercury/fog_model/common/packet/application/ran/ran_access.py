from ...application import ApplicationPacket


class RANAccessPacket(ApplicationPacket):
    def __init__(self, ap_id, header=0):
        super().__init__(header)
        self.ap_id = ap_id


class PrimarySynchronizationSignal(RANAccessPacket):
    def __init__(self, ap_id, header=0):
        super().__init__(ap_id, header)


class AccessRequest(RANAccessPacket):
    def __init__(self, ue_id, ap_id, header=0):
        super().__init__(ap_id, header)
        self.ue_id = ue_id


class DisconnectRequest(AccessRequest):
    pass


class AccessResponse(AccessRequest):
    def __init__(self, ap_id, ue_id, response, header=0):
        super().__init__(ue_id, ap_id, header)
        self.response = response


class DisconnectResponse(AccessResponse):
    pass


class RadioResourceControl(AccessRequest):
    def __init__(self, ue_id, ap_id, rrc_list, header=0):
        super().__init__(ue_id, ap_id, header)
        self.rrc_list = rrc_list


class MCSMessage(RANAccessPacket):
    def __init__(self, ap_id, ue_id, mcs_index, efficiency, bandwidth):
        super().__init__(ap_id)
        self.ue_id = ue_id
        self.mcs_index = mcs_index
        self.efficiency = efficiency
        self.bandwidth = bandwidth


class NewUpLinkMCS(MCSMessage):
    pass


class NewDownLinkMCS(MCSMessage):
    def __init__(self, ue_id, ap_id, mcs_index, efficiency, bandwidth):
        super().__init__(ap_id, ue_id, mcs_index, efficiency, bandwidth)
