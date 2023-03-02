import unittest
from mercury.config.edcs import CoolerConfig
from mercury.model.edcs.edc.r_manager.cooler import Cooler


class TestCooler(unittest.TestCase):
    def test_cooler(self):
        cooler_config = CoolerConfig('cooler', 'constant', {'power': 100})
        cooler = Cooler('edc', cooler_config, 298)
        self.assertEqual(0, cooler.it_power)
        self.assertEqual(100, cooler.cooling_power)
        self.assertEqual(100, cooler.total_power)
        self.assertEqual(0, cooler.pue)
        self.assertEqual(298, cooler.edc_temp)

        self.assertEqual(100, cooler.compute_power(200))
        self.assertEqual(0, cooler.it_power)
        self.assertEqual(100, cooler.cooling_power)
        self.assertEqual(100, cooler.total_power)
        self.assertEqual(0, cooler.pue)
        self.assertEqual(298, cooler.edc_temp)
        cooler.update_cooler(200)
        self.assertEqual(200, cooler.it_power)
        self.assertEqual(100, cooler.cooling_power)
        self.assertEqual(300, cooler.total_power)
        self.assertEqual(3 / 2, cooler.pue)
        self.assertEqual(298, cooler.edc_temp)


if __name__ == '__main__':
    unittest.main()
