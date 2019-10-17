from xdevs.models import Port
from ....common import Stateless
from ....common.packet.application.service import ServiceConfiguration, OngoingSessionRequestPacket


class ServiceDataGenerator(Stateless):
    """
    Service Data Generator xDEVS module

    :param str name: name of the xDEVS module
    :param str ue_id: User Equipment ID
    :param  ServiceConfiguration service_config: service configuration
    :param float t_initial: initial back off time before creating the first package
    """
    def __init__(self, name, ue_id, service_config, t_initial):
        self.ue_id = ue_id
        # Unwrap configuration parameters
        self.service_id = service_config.service_id
        self.service_u = service_config.service_u
        self.header = service_config.header
        self.data = service_config.data
        self.packaging_time = service_config.packaging_time

        super().__init__(t_initial + self.packaging_time, name)

        # I/O ports
        self.output_session_request = Port(OngoingSessionRequestPacket, name + '_output_session_request')
        self.add_out_port(self.output_session_request)

    def check_in_ports(self):
        pass

    def process_internal_messages(self):
        """Add new ongoing session request packet every time a timeout occurs"""
        msg = OngoingSessionRequestPacket(self.service_id, self.ue_id, self.header, self.data, None)
        self.add_msg_to_queue(self.output_session_request, msg)

    def get_next_timeout(self):
        return self.packaging_time
