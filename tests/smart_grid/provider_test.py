import unittest
import pandas as pd
from math import inf
from mercury.model.smart_grid.provider import EnergyProvider, EnergyProviderConfig


class TestEnergyProviders(unittest.TestCase):
    def test_energy_provider_static(self):
        provider_id = 'iberdrola'
        cost = 100
        provider_config = EnergyProviderConfig(provider_id, 'constant', {'cost': cost})
        provider = EnergyProvider(provider_config)
        provider.initialize()
        self.assertEqual(provider.sigma, 0)
        self.assertEqual(cost, provider.cost_generator.next_cost)
        self.assertEqual(len(provider.output_energy_cost), 0)
        provider.lambdaf()
        provider.deltint()
        self.assertEqual(provider.sigma, inf)
        self.assertEqual(cost, provider.cost_generator.next_cost)
        self.assertEqual(cost, provider.cost_generator.last_val)
        self.assertEqual(len(provider.output_energy_cost), 1)
        msg = provider.output_energy_cost.get()
        self.assertEqual(msg.provider_id, provider_id)
        self.assertEqual(msg.cost, cost)
        provider.output_energy_cost.clear()

    def test_energy_provider_history(self):
        provider_id = 'iberdrola'
        offers = pd.DataFrame({'time': [-1, 0, 0, 2, 2.1],
                               'cost': [4,  1, 2, 5, 5]})
        provider_config = EnergyProviderConfig(provider_id, 'history', {'t_start': 0, 'history': offers})
        provider = EnergyProvider(provider_config)

        provider.initialize()
        self.assertEqual(provider.sigma, 0)
        self.assertEqual(2, provider.cost_generator.next_cost)
        self.assertEqual(2, provider.cost_generator.last_val)
        self.assertEqual(len(provider.output_energy_cost), 0)

        provider.lambdaf()
        provider.deltint()
        self.assertEqual(provider.sigma, 2)
        self.assertEqual(5, provider.cost_generator.next_cost)
        self.assertEqual(len(provider.output_energy_cost), 1)
        msg = provider.output_energy_cost.get()
        self.assertEqual(msg.provider_id, provider_id)
        self.assertEqual(msg.cost, 2)
        provider.output_energy_cost.clear()

        provider.lambdaf()
        provider.deltint()
        self.assertAlmostEqual(provider.sigma, 0.1)
        self.assertEqual(5, provider.cost_generator.next_cost)
        self.assertEqual(len(provider.output_energy_cost), 1)
        msg = provider.output_energy_cost.get()
        self.assertEqual(msg.provider_id, provider_id)
        self.assertEqual(msg.cost, 5)
        provider.output_energy_cost.clear()

        provider.lambdaf()
        provider.deltint()
        self.assertEqual(provider.sigma, inf)
        self.assertEqual(5, provider.cost_generator.next_cost)
        self.assertEqual(len(provider.output_energy_cost), 1)
        msg = provider.output_energy_cost.get()
        self.assertEqual(msg.provider_id, provider_id)
        self.assertEqual(msg.cost, 5)
        provider.output_energy_cost.clear()
