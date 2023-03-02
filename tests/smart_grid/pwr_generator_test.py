import unittest
import pandas as pd
from math import inf
from mercury.model.smart_grid.consumer.pwr_generator import PowerGenerator, PowerGeneratorConfig


class TestPowerSources(unittest.TestCase):
    def test_power_source_static(self):
        consumer_id = 'consumer'
        generator_id = 'solar'
        power = 100
        source = PowerGenerator(consumer_id, generator_id, PowerGeneratorConfig('constant', {'power': power}))
        source.initialize()
        self.assertEqual(source.sigma, 0)
        self.assertEqual(power, source.pwr_generation.next_power)
        self.assertEqual(power, source.pwr_generation.next_power)
        self.assertEqual(len(source.output_pwr_generation), 0)

        source.lambdaf()
        source.deltint()
        self.assertEqual(source.sigma, inf)
        self.assertEqual(power, source.pwr_generation.next_power)
        self.assertEqual(power, source.pwr_generation.next_power)
        self.assertEqual(len(source.output_pwr_generation), 1)
        msg = source.output_pwr_generation.get()
        self.assertEqual(msg.consumer_id, consumer_id)
        self.assertEqual(msg.generator_id, generator_id)
        self.assertEqual(msg.power, power)
        source.output_pwr_generation.clear()

    def test_power_source_history(self):
        consumer_id = 'consumer'
        generator_id = 'solar'

        history = {'time': [-1, 0, 0, 2, 2.1], 'power': [4, 1, 2, 5, 5]}
        source = PowerGenerator(consumer_id, generator_id,
                                PowerGeneratorConfig('history', {'t_start': 0, 'history': pd.DataFrame(history)}))

        source.initialize()
        self.assertEqual(source.sigma, 0)
        self.assertEqual(2, source.pwr_generation.next_power)
        self.assertEqual(2, source.pwr_generation.last_val)
        self.assertEqual(len(source.output_pwr_generation), 0)

        source.lambdaf()
        source.deltint()
        self.assertEqual(source.sigma, 2)
        self.assertEqual(5, source.pwr_generation.next_power)
        self.assertEqual(2, source.pwr_generation.last_val)
        self.assertEqual(len(source.output_pwr_generation), 1)
        msg = source.output_pwr_generation.get()
        self.assertEqual(msg.consumer_id, consumer_id)
        self.assertEqual(msg.generator_id, generator_id)
        self.assertEqual(msg.power, 2)
        source.output_pwr_generation.clear()

        source.lambdaf()
        source.deltint()
        self.assertAlmostEqual(source.sigma, 0.1)
        self.assertEqual(5, source.pwr_generation.next_power)
        self.assertEqual(5, source.pwr_generation.last_val)
        self.assertEqual(len(source.output_pwr_generation), 1)
        msg = source.output_pwr_generation.get()
        self.assertEqual(msg.consumer_id, consumer_id)
        self.assertEqual(msg.generator_id, generator_id)
        self.assertEqual(msg.power, 5)
        source.output_pwr_generation.clear()

        source.lambdaf()
        source.deltint()
        self.assertEqual(source.sigma, inf)
        self.assertEqual(5, source.pwr_generation.next_power)
        self.assertEqual(5, source.pwr_generation.last_val)
        self.assertEqual(len(source.output_pwr_generation), 1)
        msg = source.output_pwr_generation.get()
        self.assertEqual(msg.consumer_id, consumer_id)
        self.assertEqual(msg.generator_id, generator_id)
        self.assertEqual(msg.power, 5)
        source.output_pwr_generation.clear()
