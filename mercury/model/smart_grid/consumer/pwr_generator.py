from __future__ import annotations
from mercury.config.smart_grid import PowerGeneratorConfig
from mercury.msg.smart_grid import PowerGeneration
from mercury.plugin import AbstractFactory, PowerGenerationGenerator
from xdevs.models import Port
from ...common import ExtendedAtomic


class PowerGenerator(ExtendedAtomic):
    def __init__(self, consumer_id: str, generator_id: str, gen_config: PowerGeneratorConfig):
        self.consumer_id: str = consumer_id
        self.generator_id: str = generator_id
        super().__init__(name=f'sg_consumer_{consumer_id}_pwr_generator_{self.generator_id}')
        gen_config = dict() if gen_config is None else gen_config
        self.pwr_generation: PowerGenerationGenerator = AbstractFactory.create_sg_pwr_generation(gen_config.gen_id,
                                                                                                 **gen_config.gen_config)
        self.output_pwr_generation: Port[PowerGeneration] = Port(PowerGeneration, 'output_pwr_generation')
        self.add_out_port(self.output_pwr_generation)

    def deltint_extension(self):
        if self.pwr_generation.next_t <= self._clock:
            self.pwr_generation.advance()
        self.sigma = max(self.pwr_generation.next_t - self._clock, 0)

    def deltext_extension(self, e):
        self.continuef(e)

    def lambdaf_extension(self):
        if self.pwr_generation.next_t <= self._clock + self.sigma:
            msg = PowerGeneration(self.consumer_id, self.generator_id, self.pwr_generation.next_power)
            self.output_pwr_generation.add(msg)

    def initialize(self):
        self.sigma = max(self.pwr_generation.next_t - self._clock, 0)

    def exit(self):
        pass
