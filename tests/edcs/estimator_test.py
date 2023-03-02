import pandas as pd
import unittest
from math import inf
from mercury.config.edcs import SrvEstimatorConfig
from mercury.model.edcs.edc.estimator import SrvDemandEstimationReport, EDCDemandEstimator, EdgeDataCenterReport


def internal_advance(model):
    for port in model.out_ports:
        port.clear()
    model.lambdaf()
    model.deltint()


def external_advance(model, e):
    for port in model.out_ports:
        port.clear()
    model.deltext(e)
    for port in model.in_ports:
        port.clear()


class EDCDemandEstimatorTestCase(unittest.TestCase):
    def test_static(self):
        edc_id: str = 'edc'
        service_estimators = {'service_1': SrvEstimatorConfig('service_1', 'constant', {'demand': 1}),
                              'service_2': SrvEstimatorConfig('service_2', 'constant', {'demand': 2})}
        estimator = EDCDemandEstimator(edc_id, service_estimators)
        estimator.initialize()
        self.assertEqual(0, estimator.sigma)

        internal_advance(estimator)
        self.assertEqual(1, len(estimator.output_srv_estimation))
        self.assertEqual(inf, estimator.sigma)
        msg = estimator.output_srv_estimation.get()
        self.assertEqual(2, len(msg.demand_estimation))
        self.assertEqual(1, msg.demand_estimation['service_1'])
        self.assertEqual(2, msg.demand_estimation['service_2'])

        estimator.input_edc_report.add(EdgeDataCenterReport('edc', {}, 0, 0))
        external_advance(estimator, 3)
        self.assertEqual(0, estimator.sigma)
        internal_advance(estimator)
        self.assertEqual(1, len(estimator.output_srv_estimation))
        self.assertEqual(inf, estimator.sigma)
        msg = estimator.output_srv_estimation.get()
        self.assertEqual(2, len(msg.demand_estimation))
        self.assertEqual(1, msg.demand_estimation['service_1'])
        self.assertEqual(2, msg.demand_estimation['service_2'])

    def test_history(self):
        edc_id: str = 'edc'
        service_estimators = {
            'service_1': SrvEstimatorConfig('service_1', 'history', {'history': pd.DataFrame({'time': [-1, 0, 0, 2],
                                                                                       'demand': [4, 1, 2, 4.1]})}),
            'service_2': SrvEstimatorConfig('service_2', 'constant', {'demand': 2})
        }
        estimator = EDCDemandEstimator(edc_id, service_estimators)
        estimator.initialize()
        self.assertEqual(0, estimator.sigma)

        internal_advance(estimator)
        self.assertEqual(1, len(estimator.output_srv_estimation))
        msg: SrvDemandEstimationReport = estimator.output_srv_estimation.get()
        self.assertEqual(2, len(msg.demand_estimation))
        self.assertEqual(2, msg.demand_estimation['service_1'])
        self.assertEqual(2, msg.demand_estimation['service_2'])
        self.assertEqual(2, estimator.sigma)

        estimator.input_edc_report.add(EdgeDataCenterReport('edc', {}, 0, 0))
        external_advance(estimator, 1)
        self.assertEqual(0, estimator.sigma)
        internal_advance(estimator)
        self.assertEqual(1, len(estimator.output_srv_estimation))
        msg: SrvDemandEstimationReport = estimator.output_srv_estimation.get()
        self.assertEqual(2, len(msg.demand_estimation))
        self.assertEqual(2, msg.demand_estimation['service_1'])
        self.assertEqual(2, msg.demand_estimation['service_2'])
        self.assertEqual(1, estimator.sigma)

        internal_advance(estimator)
        self.assertEqual(0, len(estimator.output_srv_estimation))
        self.assertEqual(0, estimator.sigma)
        internal_advance(estimator)
        self.assertEqual(1, len(estimator.output_srv_estimation))
        msg: SrvDemandEstimationReport = estimator.output_srv_estimation.get()
        self.assertEqual(2, len(msg.demand_estimation))
        self.assertEqual(5, msg.demand_estimation['service_1'])
        self.assertEqual(2, msg.demand_estimation['service_2'])
        self.assertAlmostEqual(inf, estimator.sigma)

        estimator.input_edc_report.add(EdgeDataCenterReport('edc', {}, 0, 0))
        external_advance(estimator, 3)
        self.assertEqual(0, estimator.sigma)
        internal_advance(estimator)
        self.assertEqual(1, len(estimator.output_srv_estimation))
        msg: SrvDemandEstimationReport = estimator.output_srv_estimation.get()
        self.assertEqual(2, len(msg.demand_estimation))
        self.assertEqual(5, msg.demand_estimation['service_1'])
        self.assertEqual(2, msg.demand_estimation['service_2'])
        self.assertAlmostEqual(inf, estimator.sigma)


if __name__ == '__main__':
    unittest.main()
