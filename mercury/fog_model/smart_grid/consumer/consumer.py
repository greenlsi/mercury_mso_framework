from xdevs.models import Port, Coupled
from mercury.plugin import AbstractFactory
from mercury.config.smart_grid import ConsumerConfig
from mercury.msg.smart_grid import PowerDemandReport, PowerConsumptionReport, ElectricityOffer
from .pwr_storage import PowerStorageAndControl


class SmartGridConsumer(Coupled):
    def __init__(self, consumer_id: str, consumer_config: ConsumerConfig):
        super().__init__('smart_grid_consumer_{}'.format(consumer_id))

        self.consumer_id = consumer_id

        self.input_offer = Port(ElectricityOffer, 'input_offer')
        self.input_pwr_demand = Port(PowerDemandReport, 'input_pwr_demand')
        self.output_pwr_consumption = Port(PowerConsumptionReport, 'output_pwr_consumption')

        self.add_in_port(self.input_offer)
        self.add_in_port(self.input_pwr_demand)
        self.add_out_port(self.output_pwr_consumption)

        power_storage = PowerStorageAndControl(consumer_config)
        self.add_component(power_storage)
        self.add_coupling(self.input_offer, power_storage.input_electricity_offer)
        self.add_coupling(self.input_pwr_demand, power_storage.input_power_demand)
        self.add_coupling(power_storage.output_power_consumption, self.output_pwr_consumption)

        for source_id, source_config in consumer_config.sources_config.items():
            power_source = AbstractFactory.create_smart_grid_source(source_config.source_type, consumer_id=consumer_id,
                                                                    source_id=source_id, **source_config.source_config)
            self.add_component(power_source)
            self.add_coupling(power_source.output_power_report, power_storage.input_power_generation)
