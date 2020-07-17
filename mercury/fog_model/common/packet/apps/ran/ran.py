class RadioAccessNetworkConfiguration:
    def __init__(self, header: int, pss_period: float, rrc_period: float, timeout: float, bypass_amf: bool):
        self.header = header
        self.pss_period = pss_period
        self.rrc_period = rrc_period
        self.timeout = timeout
        self.bypass_amf = bypass_amf
