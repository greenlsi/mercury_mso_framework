from __future__ import annotations
from mercury.config.client import ClientConfig, ClientsConfig
from ..common.fsm import ExtendedAtomic, Port


class ClientGeneratorModel(ExtendedAtomic):
    def __init__(self, clients_config: ClientsConfig):
        from mercury.plugin.factory import AbstractFactory, ClientGenerator
        super().__init__('client_generator')
        self.generators: list[ClientGenerator] = list()
        for generator_id, generator_config in clients_config.generators:
            self.generators.append(AbstractFactory.create_client_generator(generator_id, **generator_config))
        self.output_client_config: Port[ClientConfig] = Port(ClientConfig, 'output_client_config')
        self.add_out_port(self.output_client_config)

    def deltint_extension(self):
        for generator in self.generators:
            while generator.next_t() <= self._clock:
                for client_config in generator.generate_clients():
                    self.add_msg_to_queue(self.output_client_config, client_config)
        self.sigma = self.next_sigma()

    def deltext_extension(self, e):
        self.sigma = self.next_sigma()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.sigma = self.next_sigma()

    def exit(self):
        pass

    def next_sigma(self) -> float:
        return max(min(g.next_t() for g in self.generators) - self._clock, 0) if self.msg_queue_empty() else 0
