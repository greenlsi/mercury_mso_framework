from .application import ApplicationPacket


class ServiceConfiguration:
    """
    Configuration class for services_config
    :param str service_id: ID of the service
    :param float service_u: Service utilization factor
    :param int header: size (in bits) of headers of a given service
    :param float generation_rate: data stream generation rate (in bps)
    :param float packaging_time: time (in seconds) encapsulated in each service session message
    :param float min_closed_t: minimum time (in seconds) to wait before opening a service session
    :param float min_open_t: minimum time (in seconds) to wait before closing a service session
    :param float service_timeout: time (in seconds) to wait before considering a message without response timed out
    :param int window_size: maximum number of session requests that can be sent simultaneously with no response
    """
    def __init__(self, service_id, service_u, header, generation_rate, packaging_time, min_closed_t, min_open_t,
                 service_timeout, window_size=1):
        self.service_id = service_id
        self.service_u = service_u
        self.header = header
        self.generation_rate = generation_rate
        self.packaging_time = packaging_time
        self.data = packaging_time * generation_rate
        self.min_closed_t = min_closed_t
        self.min_open_t = min_open_t
        self.service_timeout = service_timeout
        self.window_size = window_size


class ServicePacket(ApplicationPacket):
    pass


class ServiceRequest(ServicePacket):
    def __init__(self, service_id, session_id, header=0, data=0, packet_id=None):
        super().__init__(header, data, packet_id)
        self.service_id = service_id
        self.session_id = session_id


class ServiceResponse(ServicePacket):
    def __init__(self, service_id, session_id, response, header=0, packet_id=None):
        super().__init__(header, 0, packet_id)
        self.service_id = service_id
        self.session_id = session_id
        self.response = response


class CreateSessionRequestPacket(ServiceRequest):
    pass


class RemoveSessionRequestPacket(ServiceRequest):
    pass


class OngoingSessionRequestPacket(ServiceRequest):
    pass


class CreateSessionResponsePacket(ServiceResponse):
    pass


class RemoveSessionResponsePacket(ServiceResponse):
    pass


class OngoingSessionResponsePacket(ServiceResponse):
    pass


class GetDataCenterRequest(ServiceRequest):
    def __init__(self, ue_id, service_id, header=0, data=0, packet_id=None):
        super().__init__(service_id, None, header, data, packet_id)
        self.ue_id = ue_id


class GetDataCenterResponse(ServiceResponse):
    def __init__(self, ue_id, service_id, dc_id, header=0, packet_id=None):
        super().__init__(service_id, None, dc_id, header, packet_id)
        self.ue_id = ue_id
        self.dc_id = dc_id


class ServiceDelayReport:
    def __init__(self, ue_id, service_id, instant_generated, instant_sent, instant_received, delay, times_sent):
        self.ue_id = ue_id
        self.service_id = service_id
        self.instant_generated = instant_generated
        self.instant_sent = instant_sent
        self.instant_received = instant_received
        self.delay = delay
        self.times_sent = times_sent
