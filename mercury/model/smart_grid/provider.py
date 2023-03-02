from __future__ import annotations
from mercury.config.smart_grid import EnergyProviderConfig
from mercury.msg.smart_grid import EnergyOffer
from mercury.plugin import AbstractFactory, EnergyCostGenerator
from xdevs.models import Port
from ..common import ExtendedAtomic


class EnergyProvider(ExtendedAtomic):
    def __init__(self, provider_config: EnergyProviderConfig):
        self.provider_id: str = provider_config.provider_id
        super().__init__(name=f'sg_energy_provider_{self.provider_id}')
        self.cost_generator: EnergyCostGenerator = AbstractFactory.create_sg_energy_cost(provider_config.cost_id,
                                                                                         **provider_config.cost_config)
        self.output_energy_cost: Port[EnergyOffer] = Port(EnergyOffer, 'output_energy_cost')
        self.add_out_port(self.output_energy_cost)

    def deltint_extension(self):
        if self.cost_generator.next_t <= self._clock:
            self.cost_generator.advance()
        self.sigma = max(self.cost_generator.next_t - self._clock, 0)

    def deltext_extension(self, e):
        self.continuef(e)

    def lambdaf_extension(self):
        if self.cost_generator.next_t <= self._clock + self.sigma:
            self.output_energy_cost.add(EnergyOffer(self.provider_id, self.cost_generator.next_cost))

    def initialize(self):
        self.sigma = max(self.cost_generator.next_t - self._clock, 0)

    def exit(self):
        pass
