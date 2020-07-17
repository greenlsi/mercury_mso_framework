from ...common.packet.apps.ran.ran_access import PrimarySynchronizationSignal


class ConnectedAccessPoint:
    def __init__(self, ap_id):
        self.ap_id = ap_id


class AntennaPowered:
    def __init__(self, powered):
        self.powered = powered


class ExtendedPSS(PrimarySynchronizationSignal):
    def __init__(self, ap_id, snr):
        super().__init__(ap_id)
        self.snr = snr


class ServiceRequired:
    def __init__(self, service_id, required):
        self.service_id = service_id
        self.required = required
