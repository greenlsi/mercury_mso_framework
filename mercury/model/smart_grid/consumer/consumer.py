from mercury.config.smart_grid import ConsumerConfig
from mercury.msg.smart_grid import EnergyDemand, EnergyConsumption, EnergyOffer
from xdevs.models import Coupled, Port
from .energy_storage import EnergyStorageAndControl
from .pwr_generator import PowerGenerator


class SmartGridConsumer(Coupled):
    def __init__(self, consumer_config: ConsumerConfig):
        self.consumer_id = consumer_config.consumer_id
        super().__init__(f'smart_grid_consumer_{self.consumer_id}')

        self.input_offer = Port(EnergyOffer, 'input_offer')
        self.input_energy_demand = Port(EnergyDemand, 'input_energy_demand')
        self.output_energy_consumption = Port(EnergyConsumption, 'output_energy_consumption')
        self.add_in_port(self.input_offer)
        self.add_in_port(self.input_energy_demand)
        self.add_out_port(self.output_energy_consumption)

        power_storage = EnergyStorageAndControl(consumer_config)
        self.add_component(power_storage)
        self.add_coupling(self.input_offer, power_storage.input_energy_cost)
        self.add_coupling(self.input_energy_demand, power_storage.input_energy_demand)
        self.add_coupling(power_storage.output_energy_consumption, self.output_energy_consumption)

        for generator_id, generator_config in consumer_config.sources_config.items():
            pwr_generator = PowerGenerator(self.consumer_id, generator_id, generator_config)
            self.add_component(pwr_generator)
            self.add_coupling(pwr_generator.output_pwr_generation, power_storage.input_pwr_generation)
