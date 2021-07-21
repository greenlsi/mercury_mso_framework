from xdevs.models import Port, Coupled
from typing import Dict
from mercury.config.smart_grid import SmartGridConfig
from mercury.plugin import AbstractFactory, EnergyProvider
from mercury.msg.smart_grid import PowerDemandReport, PowerConsumptionReport, ElectricityOffer
from .consumer import SmartGridConsumer


class SmartGrid(Coupled):
    def __init__(self, smart_grid_config: SmartGridConfig):
        super().__init__('smart_grid')

        self.output_new_offer = Port(ElectricityOffer, 'output_electricity_offer')
        self.add_out_port(self.output_new_offer)

        self.providers: Dict[str, EnergyProvider] = dict()
        for provider_id, provider_config in smart_grid_config.providers_config.items():
            provider = AbstractFactory.create_smart_grid_provider(provider_config.provider_type,
                                                                  provider_id=provider_id,
                                                                  **provider_config.provider_config)
            self.providers[provider_id] = provider
            self.add_component(provider)
            self.add_coupling(provider.out_electricity_offer, self.output_new_offer)

        self.consumers = list()
        self.inputs_demand = dict()
        self.outputs_consumption = dict()
        for consumer_id, consumer_config in smart_grid_config.consumers_config.items():
            self.consumers.append(consumer_id)
            self.inputs_demand[consumer_id] = Port(PowerDemandReport, 'input_pwr_demand_' + consumer_id)
            self.outputs_consumption[consumer_id] = Port(PowerConsumptionReport, 'output_consumption_' + consumer_id)

            self.add_in_port(self.inputs_demand[consumer_id])
            self.add_out_port(self.outputs_consumption[consumer_id])

            consumer = SmartGridConsumer(consumer_id, consumer_config)
            self.add_component(consumer)
            self.add_coupling(self.inputs_demand[consumer_id], consumer.input_pwr_demand)
            self.add_coupling(self.providers[consumer_config.provider_id].out_electricity_offer, consumer.input_offer)
            self.add_coupling(consumer.output_pwr_consumption, self.outputs_consumption[consumer_id])
