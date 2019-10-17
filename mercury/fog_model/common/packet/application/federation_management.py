from .application import ApplicationPacket


class FederationManagementConfiguration:
    """
    Configuration for all federation management-related messages.

    :param int header: size (in bits) of the header of radio access application messages
    :param int edc_report_data: size (in bits) of the body of EDC report messages
    """
    def __init__(self, header, edc_report_data):
        self.header = header
        self.edc_report_data = edc_report_data


class FederationManagementPacket(ApplicationPacket):
    pass


class EdgeDataCenterReportPacket(FederationManagementPacket):
    def __init__(self, edc_report, header=0, data=0, packet_id=None):
        super().__init__(header, data, packet_id)
        self.edc_report = edc_report


class EdgeFederationReportPacket(FederationManagementPacket):
    def __init__(self, edc_reports, header=0, data=0, packet_id=None):
        super().__init__(header, data, packet_id)
        self.edc_reports = edc_reports


class NewSDNPath(FederationManagementPacket):
    def __init__(self, service_route, header=0, data=0, packet_id=None):
        super().__init__(header, data, packet_id)
        self.service_route = service_route
