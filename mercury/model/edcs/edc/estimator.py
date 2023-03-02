from __future__ import annotations
from math import inf
from mercury.config.edcs import SrvEstimatorConfig
from mercury.msg.edcs import EdgeDataCenterReport, SrvDemandEstimationReport
from xdevs.models import Port
from ...common import ExtendedAtomic


class EDCDemandEstimator(ExtendedAtomic):
    def __init__(self, edc_id: str, service_estimators: dict[str, SrvEstimatorConfig]):
        from mercury.plugin import AbstractFactory, SrvDemandEstimator
        self.edc_id: str = edc_id
        super().__init__(f'{self.edc_id}_estimator')
        self.input_edc_report: Port[EdgeDataCenterReport] = Port(EdgeDataCenterReport, 'input_edc_report')
        self.output_srv_estimation: Port[SrvDemandEstimationReport] = Port(SrvDemandEstimationReport, 'output_estimation')
        self.add_in_port(self.input_edc_report)
        self.add_out_port(self.output_srv_estimation)

        self.edc_report: EdgeDataCenterReport | None = None
        self.srv_estimators: dict[str, SrvDemandEstimator] = dict()
        for srv_id, config in service_estimators.items():
            self.srv_estimators[srv_id] = AbstractFactory.create_demand_estimation(config.estimator_id,
                                                                                   **config.estimator_config,
                                                                                   service_id=srv_id)

    @property
    def next_t(self) -> float:
        return min((estimator.get_next_t() for estimator in self.srv_estimators.values()), default=inf)

    def initialize(self):
        self.deltint_extension()

    def exit(self):
        pass

    def deltint_extension(self):
        if self.next_t <= self._clock:
            self.send_estimation()
        self.hold_in('passive', self.next_t - self._clock) if self.msg_queue_empty() else self.activate()

    def deltext_extension(self, e):
        if self.input_edc_report:
            self.edc_report = self.input_edc_report.get()
            self.send_estimation()
        self.continuef(e) if self.msg_queue_empty() else self.activate()

    def send_estimation(self):
        msg = {srv_id: estim.estimation(self._clock, self.edc_report) for srv_id, estim in self.srv_estimators.items()}
        self.add_msg_to_queue(self.output_srv_estimation, SrvDemandEstimationReport(self.edc_id, self.edc_report, msg))

    def lambdaf_extension(self):
        pass
