from mercury.msg.cnfs import DemandEstimation
from mercury.plugin import AbstractFactory, DemandEstimationGenerator
from xdevs.models import Atomic, Port, PHASE_PASSIVE


class DemandEstimator(Atomic):
    def __init__(self, service_id: str, estimator_id: str, **kwargs):
        super().__init__('cnfs_demand_estimator_{}'.format(service_id))
        self.service_id: str = service_id
        self.estimator: DemandEstimationGenerator = AbstractFactory.create_demand_estimator(estimator_id, **kwargs)
        self.output_demand_estimation = Port(DemandEstimation, 'output_demand_estimation')
        self.add_out_port(self.output_demand_estimation)

    def deltint(self):
        self.estimator.advance()
        self.hold_in(PHASE_PASSIVE, self.estimator.ta)

    def deltext(self, e):
        self.hold_in(PHASE_PASSIVE, self.sigma - e)

    def lambdaf(self):
        self.output_demand_estimation.add(DemandEstimation(self.service_id, self.estimator.next_val))

    def initialize(self):
        self.hold_in(PHASE_PASSIVE, self.estimator.ta)

    def exit(self):
        pass
