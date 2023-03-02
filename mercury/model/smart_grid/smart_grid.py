from __future__ import annotations
from mercury.config.smart_grid import SmartGridConfig
from mercury.msg.smart_grid import EnergyDemand, EnergyConsumption
from xdevs.models import Port, Coupled
from .consumer import SmartGridConsumer
from .provider import EnergyProvider


class SmartGrid(Coupled):
    def __init__(self, smart_grid_config: SmartGridConfig):
        super().__init__('smart_grid')
        self.providers: dict[str, EnergyProvider] = dict()
        for provider_id, provider_config in smart_grid_config.providers_config.items():
            provider = EnergyProvider(provider_config)
            self.providers[provider_id] = provider
            self.add_component(provider)

        self.consumers: dict[str, SmartGridConsumer] = dict()
        self.inputs_demand: dict[str, Port[EnergyDemand]] = dict()
        self.outputs_consumption: dict[str, Port[EnergyConsumption]] = dict()
        for consumer_id, consumer_config in smart_grid_config.consumers_config.items():
            consumer = SmartGridConsumer(consumer_config)
            self.consumers[consumer_id] = consumer
            self.add_component(consumer)

            self.inputs_demand[consumer_id] = Port(EnergyDemand, f'input_pwr_demand_{consumer_id}')
            self.outputs_consumption[consumer_id] = Port(EnergyConsumption, f'output_consumption_{consumer_id}')
            self.add_in_port(self.inputs_demand[consumer_id])
            self.add_out_port(self.outputs_consumption[consumer_id])

            self.add_coupling(self.inputs_demand[consumer_id], consumer.input_energy_demand)
            self.add_coupling(consumer.output_energy_consumption, self.outputs_consumption[consumer_id])
            provider_id = consumer_config.provider_id
            if provider_id is not None:
                self.add_coupling(self.providers[provider_id].output_energy_cost, consumer.input_offer)
