from __future__ import annotations
from mercury.msg.cloud import CloudProfileReport
from mercury.msg.packet.app_packet.srv_packet import SrvRelatedResponse
from mercury.msg.profile import CloudProfile
from ..common import ExtendedAtomic
from xdevs.models import Port


class CloudProfiler(ExtendedAtomic):
    def __init__(self, cloud_id: str, srv_profiling_windows: dict[str, float]):
        self.cloud_id: str = cloud_id
        super().__init__(f'{self.cloud_id}_profiler')
        self.report_required = False
        self.cloud_profile: CloudProfile = CloudProfile(cloud_id, srv_profiling_windows)
        self.prev_reports: dict[tuple[str, str, str], CloudProfileReport] = dict()

        self.input_srv: Port[SrvRelatedResponse] = Port(SrvRelatedResponse, 'input_srv')
        self.output_profile: Port[CloudProfileReport] = Port(CloudProfileReport, 'output_profile_report')
        self.output_srv: Port[SrvRelatedResponse] = Port(SrvRelatedResponse, 'output_srv')
        self.add_in_port(self.input_srv)
        self.add_out_port(self.output_profile)
        self.add_out_port(self.output_srv)

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def deltint_extension(self):
        self.report_required |= self.cloud_profile.clean(self._clock)
        if self.report_required:
            self.send_profile()
        self.report_required = False
        self.hold_in('passive', self.next_sigma())

    def deltext_extension(self, e):
        self.continuef(e)
        if self.input_srv:
            self.report_required = True
            for response in self.input_srv.values:
                self.cloud_profile.push(self._clock, response)
                self.add_msg_to_queue(self.output_srv, response)
        self.deltint_extension()

    def lambdaf_extension(self):
        pass

    def send_profile(self):
        for srv_id, srv_profile in self.cloud_profile.profiles.items():
            n_clients = srv_profile.n_clients
            for req_type, profile in srv_profile.profiles.items():
                for result, window in profile.profiles.items():
                    new_report = CloudProfileReport(self.cloud_id, srv_id, n_clients, req_type, result, window.report())
                    prev_report = self.prev_reports.get((srv_id, req_type, result))
                    if prev_report is None or new_report != prev_report:
                        self.prev_reports[(srv_id, req_type, result)] = new_report
                        self.add_msg_to_queue(self.output_profile, new_report)

    def next_sigma(self):
        return self.cloud_profile.t_next - self._clock if self.msg_queue_empty() else 0
