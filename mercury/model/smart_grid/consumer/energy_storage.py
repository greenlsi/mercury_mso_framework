from __future__ import annotations
from math import inf
from mercury.config.smart_grid import ConsumerConfig
from mercury.msg.smart_grid import EnergyConsumption, EnergyDemand, PowerGeneration, EnergyOffer, EnergyStorage
from mercury.plugin import AbstractFactory, ConsumerManager
from xdevs.models import Atomic, Port


class EnergyStorageAndControl(Atomic):

    PHASE_PASSIVE = 'passive'
    PHASE_CHARGING = 'charging'
    PHASE_DISCHARGING = 'discharging'

    def __init__(self, consumer_config: ConsumerConfig):
        """
        Energy Storage and Control system of a smart grid consumer
        :param consumer_config: Smart Grid consumer configuration parameters.
        """

        self.consumer_id: str = consumer_config.consumer_id
        self.energy_offer: EnergyOffer | None = None  # Coste de la electricidad
        super().__init__(f'pwr_storage_and_control_{self.consumer_id}')

        pwr_storage_config = consumer_config.storage_config
        self.capacity: float = pwr_storage_config.capacity
        self.max_charge_rate: float = pwr_storage_config.max_charge_rate
        self.max_discharge_rate: float = pwr_storage_config.max_discharge_rate
        self.actual_charge: float = pwr_storage_config.initial_charge

        self.acc_energy_consumption: float = 0  # TODO energy consumida en toda la simulación
        self.acc_energy_returned: float = 0  # TODO energy consumida en toda la simulación
        self.acc_cost: float = 0  # TODO coste acumulado en toda la simulación

        manager_id = consumer_config.manager_id
        manager_config = consumer_config.manager_config
        self.manager: ConsumerManager = AbstractFactory.create_sg_consumer_manager(manager_id, **manager_config)
        self.energy_demand: EnergyDemand | None = None  # Electricidad que demanda el EDC
        self.pwr_generation: dict[str, float] = dict()  # {source_id: power generation (in Watts)}
        self.actual_rate: float = 0  # Power used for charging the battery
        self.eventual_rate: float = self.compute_new_rate()  # Next power used for charging the battery
        self.eventual_charge: float = self.actual_charge   # Next battery capacity

        self.input_energy_cost: Port[EnergyOffer] = Port(EnergyOffer, 'input_energy_cost')
        self.input_energy_demand: Port[EnergyDemand] = Port(EnergyDemand, 'input_energy_demand')
        self.input_pwr_generation: Port[PowerGeneration] = Port(PowerGeneration, 'input_power_generation')
        self.output_energy_consumption: Port[EnergyConsumption] = Port(EnergyConsumption, 'output_energy_consumption')
        self.add_in_port(self.input_energy_cost)
        self.add_in_port(self.input_energy_demand)
        self.add_in_port(self.input_pwr_generation)
        self.add_out_port(self.output_energy_consumption)

    @property
    def power_demand(self) -> float:
        return 0 if self.energy_demand is None else self.energy_demand.power_demand

    @property
    def power_generation(self) -> float:
        return sum(self.pwr_generation.values())

    @property
    def power_consumption(self) -> float:
        """
        :return: potencia consumida
        """
        return self.power_demand - self.power_generation + self.actual_rate

    @property
    def energy_cost(self) -> float:
        return self.energy_offer.cost

    def initialize(self):
        self.passivate(self.next_phase())

    def deltint(self):
        energy = self.power_consumption * self.sigma / 3600  # TODO bug -> hay que pasar a Wh
        if energy > 0:           
            cost = energy * self.energy_offer.cost
            self.acc_energy_consumption += energy
            self.acc_cost += cost
        else:
            self.acc_energy_returned += energy

        self.actual_charge = self.eventual_charge
        self.actual_rate = self.compute_new_rate()
        self.update_manager()
        next_phase = self.next_phase()
        next_timeout = inf
        if next_phase == self.PHASE_CHARGING:  # Battery is charging
            next_timeout = 3600 * (self.capacity - self.actual_charge) / self.actual_rate
        elif next_phase == self.PHASE_DISCHARGING:  # Battery is discharging
            next_timeout = 3600 * (-self.actual_charge) / self.actual_rate
        self.eventual_charge = self.next_charge(next_timeout)
        self.eventual_rate = 0  # internal transitions wake up when the battery is charged, discharged, or unused
        self.hold_in(next_phase, next_timeout)

    def deltext(self, e):
        energy = self.power_consumption * e / 3600  # TODO bug -> hay que pasar a Wh
        if energy > 0:           
            cost = 0 if self.energy_offer is None else energy * self.energy_offer.cost
            self.acc_energy_consumption += energy
            self.acc_cost += cost
        else:
            self.acc_energy_returned += energy

        self.eventual_charge = self.next_charge(e)
        self.actual_charge = self.eventual_charge
        # Update the controller configuration

        if self.input_energy_cost:
            self.energy_offer = self.input_energy_cost.get()
        # Get the latest node demand report
        if self.input_energy_demand:
            self.energy_demand = self.input_energy_demand.get()
        # Update the power generation rate of the different energy sources
        for msg in self.input_pwr_generation.values:
            self.pwr_generation[msg.generator_id] = msg.power
        self.actual_rate = self.compute_new_rate()
        self.eventual_rate = self.actual_rate  # external transitions are instantaneous
        self.update_manager()
        self.hold_in(self.next_phase(), 0)

    def update_manager(self):
        if self.energy_demand is not None:
            energy_storage = EnergyStorage(self.manager.allow_charge, self.manager.allow_discharge,
                                           self.actual_rate, self.actual_charge, self.capacity)
            report = EnergyConsumption(self.energy_demand, self.power_generation, energy_storage, self.energy_offer,
                                       self.acc_energy_consumption, self.acc_energy_returned, self.acc_cost)
            self.manager.update(report)

    def lambdaf(self):
        if self.energy_demand is not None:
            energy_storage = EnergyStorage(self.manager.allow_charge, self.manager.allow_discharge,
                                           self.eventual_rate, self.eventual_charge, self.capacity)
            msg = EnergyConsumption(self.energy_demand, self.power_generation, energy_storage, self.energy_offer,
                                    self.acc_energy_consumption, self.acc_energy_returned, self.acc_cost)
            self.output_energy_consumption.add(msg)

    def compute_new_rate(self) -> float:
        rate = 0
        if self.manager.allow_charge:
            if self.actual_charge < self.capacity:
                rate = self.max_charge_rate
        else:
            power_surplus = self.power_generation - self.power_demand
            if power_surplus < 0:
                if self.manager.allow_discharge and self.actual_charge > 0:
                    rate = max(self.max_discharge_rate, power_surplus)  # discharging is enabled and there is energy
            elif self.actual_charge < self.capacity:
                rate = min(self.max_charge_rate, power_surplus)
        return rate

    def next_charge(self, ta: float) -> float:
        if ta == inf:
            return self.actual_charge
        return min(self.capacity, max(self.actual_charge + self.actual_rate * ta / 3600, 0))  # Update charge

    def next_phase(self) -> str:
        if self.actual_rate == 0:
            return self.PHASE_PASSIVE
        elif self.actual_rate > 0:
            return self.PHASE_CHARGING
        else:
            return self.PHASE_DISCHARGING

    def exit(self):
        pass
