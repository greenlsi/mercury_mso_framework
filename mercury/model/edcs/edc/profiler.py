from __future__ import annotations
from mercury.config.transducers import TransducersConfig
from mercury.msg.edcs import EDCProfile, EDCProfileReport, EdgeDataCenterReport
from mercury.msg.packet.app_packet.srv_packet import SrvRelatedResponse
from mercury.msg.smart_grid import EnergyDemand, EnergyConsumption
from ...common import ExtendedAtomic
from xdevs.models import Port


class EDCProfiler(ExtendedAtomic):
    def __init__(self, edc_id: str, srv_profiling_windows: dict[str, float]):
        self.edc_id: str = edc_id
        super().__init__(f'{self.edc_id}_profiler')
        self.report_required = False
        self.edc_report: EdgeDataCenterReport | None = None
        self.edc_profile: EDCProfile = EDCProfile(edc_id, srv_profiling_windows)
        self.prev_reports: dict[tuple[str, str, str], EDCProfileReport] = dict()

        self.input_edc_report: Port[EnergyDemand] = Port(EnergyDemand, 'input_edc_report')
        self.input_srv: Port[SrvRelatedResponse] = Port(SrvRelatedResponse, 'input_srv')
        self.output_edc_report: Port[EdgeDataCenterReport] = Port(EdgeDataCenterReport, 'output_edc_report')
        self.output_profile_report: Port[EDCProfileReport] = Port(EDCProfileReport, 'output_profile_report')
        self.output_srv: Port[SrvRelatedResponse] = Port(SrvRelatedResponse, 'output_srv')
        self.add_in_port(self.input_edc_report)
        self.add_in_port(self.input_srv)
        self.add_out_port(self.output_edc_report)
        self.add_out_port(self.output_profile_report)
        self.add_out_port(self.output_srv)

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def deltint_extension(self):
        self.report_required |= self.edc_profile.clean(self._clock)
        if TransducersConfig.LOG_EDC_PROFILE and self.report_required:
            self.send_profile()
        self.report_required = False
        self.hold_in('passive', self.next_sigma())

    def deltext_extension(self, e):
        self.continuef(e)
        # First, we update the EDC report
        if self.input_edc_report:
            edc_report = self.input_edc_report.get()
            if isinstance(edc_report, EnergyConsumption):
                edc_report = edc_report.energy_demand
            if not isinstance(edc_report, EdgeDataCenterReport):
                raise ValueError('unexpected report type')
            self.edc_report = edc_report
            self.edc_report.edc_profile = self.edc_profile
            self.add_msg_to_queue(self.output_edc_report, self.edc_report)
        # Then, we update the EDC profile
        if self.input_srv:
            self.report_required = TransducersConfig.LOG_EDC_PROFILE
            for response in self.input_srv.values:
                self.edc_profile.push(self._clock, response)
                self.add_msg_to_queue(self.output_srv, response)
        self.deltint_extension()

    def lambdaf_extension(self):
        pass

    def send_profile(self):
        for srv_id, srv_profile in self.edc_profile.profiles.items():
            n_clients = srv_profile.n_clients
            for req_type, profile in srv_profile.profiles.items():
                for result, window in profile.profiles.items():
                    new_report = EDCProfileReport(self.edc_id, srv_id, n_clients, req_type, result, window.report())
                    prev_report = self.prev_reports.get((srv_id, req_type, result))
                    if prev_report is None or new_report != prev_report:
                        self.prev_reports[(srv_id, req_type, result)] = new_report
                        self.add_msg_to_queue(self.output_profile_report, new_report)

    def next_sigma(self):
        return self.edc_profile.t_next - self._clock if self.msg_queue_empty() else 0
