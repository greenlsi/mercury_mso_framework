class RadioAccessNetworkConfiguration:
    def __init__(self, header, pss_period, rrc_period, timeout):
        self.header = header
        self.pss_period = pss_period
        self.rrc_period = rrc_period
        self.timeout = timeout
