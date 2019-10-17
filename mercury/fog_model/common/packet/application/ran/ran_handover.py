from ...application import ApplicationPacket


class RANHandOverPacket(ApplicationPacket):
    def __init__(self, ap_from, ap_to, ue_id, header=0):
        super().__init__(header)
        self.ap_from = ap_from
        self.ap_to = ap_to
        self.ue_id = ue_id


class RANHandOverRequestPacket(RANHandOverPacket):
    pass


class RANHandOverResponsePacket(RANHandOverPacket):
    def __init__(self, ap_from, ap_to, ue_id, response, header=0):
        super().__init__(ap_from, ap_to, ue_id, header)
        self.response = response


class StartHandOverRequest(RANHandOverRequestPacket):
    pass


class StartHandOverResponse(RANHandOverResponsePacket):
    def __init__(self, ap_to, ap_from, ue_id, response, header=0):
        super().__init__(ap_from, ap_to, ue_id, response, header)


class HandOverStarted(RANHandOverRequestPacket):
    def __init__(self, ap_from, ue_id, ap_to, header=0):
        super().__init__(ap_from, ap_to, ue_id, header)


class HandOverReady(RANHandOverRequestPacket):
    def __init__(self, ue_id, ap_to, ap_from, header=0):
        super().__init__(ap_from, ap_to, ue_id, header)


class HandOverFinished(RANHandOverResponsePacket):
    def __init__(self, ap_to, ue_id, ap_from, response, header=0):
        super().__init__(ap_from, ap_to, ue_id, response, header)


class HandOverResponse(RANHandOverResponsePacket):
    def __init__(self, ue_id, ap_from, ap_to, response, header=0):
        super().__init__(ap_from, ap_to, ue_id, response, header)
