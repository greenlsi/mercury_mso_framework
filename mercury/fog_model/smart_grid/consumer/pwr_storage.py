from xdevs.models import Port, Atomic, INFINITY, PHASE_PASSIVE
from mercury.plugin import AbstractFactory
from mercury.config.smart_grid import ConsumerConfig
from mercury.msg.smart_grid import PowerDemandReport, PowerConsumptionReport, PowerSourceReport, ElectricityOffer


class PowerStorageAndControl(Atomic):

    PHASE_PASSIVE = PHASE_PASSIVE
    PHASE_CHARGING = 'charging'
    PHASE_DISCHARGING = 'discharging'

    def __init__(self, consumer_config: ConsumerConfig):
        """
        Power Storage and Control system of a smart grid consumer
        :param consumer_config: Smart Grid consumer configuration parameters.
        """
        # Unwrap configuration parameters
        consumer_id = consumer_config.consumer_id
        provider_id = consumer_config.provider_id
        pwr_storage_config = consumer_config.storage_config
        consumption_manager_name = consumer_config.consumption_manager_name
        consumption_manager_config = consumer_config.consumption_manager_config

        super().__init__(name=consumer_id + '_pwr_storage_and_control')
        self.consumer_id = consumer_id
        self.provider_id = provider_id
        self.electricity_offer = None

        self.capacity = pwr_storage_config.capacity
        self.max_charge_rate = pwr_storage_config.max_charge_rate
        self.max_discharge_rate = pwr_storage_config.max_discharge_rate
        self.actual_charge = pwr_storage_config.initial_charge

        self.consumption_manager = AbstractFactory.create_smart_grid_consumption_manager(consumption_manager_name,
                                                                                         **consumption_manager_config)

        self.pwr_demand = 0  # power demand (in Watts)
        self.report = None
        self.pwr_generation = dict()  # {source_id: power generation (in Watts)}
        self.actual_rate = 0  # Power used for charging the battery
        self.eventual_rate = self.compute_new_rate()  # Next power used for charging the battery
        self.eventual_charge = self.actual_charge   # Next battery capacity

        self.input_electricity_offer = Port(ElectricityOffer, 'input_electricity_offer')
        self.input_power_demand = Port(PowerDemandReport, 'input_power_demand')
        self.input_power_generation = Port(PowerSourceReport, 'input_power_generation')
        self.output_power_consumption = Port(PowerConsumptionReport, 'output_power_consumption')

        self.add_in_port(self.input_electricity_offer)
        self.add_in_port(self.input_power_demand)
        self.add_in_port(self.input_power_generation)
        self.add_out_port(self.output_power_consumption)

    @property
    def total_generation(self) -> float:
        return sum((power for power in self.pwr_generation.values()))

    @property
    def pwr_consumption(self) -> float:
        return self.pwr_demand - self.total_generation + self.actual_rate

    def initialize(self):
        self.hold_in(self.next_phase(), INFINITY)

    def deltint(self):
        self.actual_charge = self.eventual_charge
        self.actual_rate = self.compute_new_rate()
        next_phase = self.next_phase()
        next_timeout = INFINITY
        if next_phase == self.PHASE_CHARGING:  # Battery is charging
            next_timeout = 3600 * (self.capacity - self.actual_charge) / self.actual_rate
        elif next_phase == self.PHASE_DISCHARGING:  # Battery is discharging
            next_timeout = 3600 * (-self.actual_charge) / self.actual_rate
        self.eventual_charge = self.next_charge(next_timeout)
        self.eventual_rate = 0  # internal transitions wake up when the battery is charged, discharged, or unused
        self.hold_in(next_phase, next_timeout)

    def deltext(self, e):
        self.eventual_charge = self.next_charge(e)
        self.actual_charge = self.eventual_charge
        # Update the controller configuration

        if self.input_electricity_offer:
            self.electricity_offer = self.input_electricity_offer.get().cost
            self.consumption_manager.refresh_consumption_config(self.electricity_offer)
        # Get the latest node demand report
        if self.input_power_demand:
            msg = self.input_power_demand.get()
            self.pwr_demand = msg.power
            self.report = msg.report
        # Update the power generation rate of the different energy sources
        for msg in self.input_power_generation.values:
            self.pwr_generation[msg.source_id] = msg.power
        self.actual_rate = self.compute_new_rate()
        self.eventual_rate = self.actual_rate  # external transitions are instantaneous
        self.hold_in(self.next_phase(), 0)

    def lambdaf(self):
        if self.report is not None:
            msg = PowerConsumptionReport(self.consumer_id, self.provider_id, self.electricity_offer, self.pwr_demand,
                                         self.total_generation, self.consumption_manager.charge_from_grid,
                                         self.consumption_manager.allow_discharge, self.eventual_rate,
                                         self.eventual_charge, self.capacity, self.report)
            self.output_power_consumption.add(msg)

    def compute_new_rate(self) -> float:
        rate = 0
        if self.consumption_manager.charge_from_grid:
            if self.actual_charge < self.capacity:
                rate = self.max_charge_rate
        else:
            power_surplus = self.total_generation - self.pwr_demand
            if power_surplus < 0:
                if self.consumption_manager.allow_discharge and self.actual_charge > 0:
                    rate = max(self.max_discharge_rate, power_surplus)  # discharging is enabled and there is energy
            elif self.actual_charge < self.capacity:
                rate = min(self.max_charge_rate, power_surplus)
        return rate

    def next_charge(self, ta) -> float:
        if ta == INFINITY:
            return self.actual_charge
        return min(self.capacity, max(0, self.actual_charge + self.actual_rate * ta / 3600))  # Update charge

    def next_phase(self) -> str:
        if self.actual_rate == 0:
            return self.PHASE_PASSIVE
        elif self.actual_rate > 0:
            return self.PHASE_CHARGING
        else:
            return self.PHASE_DISCHARGING

    def exit(self):
        pass
