from __future__ import annotations
from typing import Any


class EnergyProviderConfig:
    def __init__(self, provider_id: str, cost_id: str, cost_config: dict[str, Any] = None):
        """
        Energy provider configuration parameters.
        :param provider_id: ID of the energy provider.
        :param cost_id: ID of the energy cost generator model.
        :param cost_config: any additional configuration parameter for the energy cost generator model.
        """
        self.provider_id: str = provider_id
        self.cost_id: str = cost_id
        self.cost_config: dict[str, Any] = dict() if cost_config is None else cost_config


class PowerGeneratorConfig:
    def __init__(self, gen_id: str, gen_config: dict[str, Any] = None):
        """
        Power source configuration parameters.
        :param gen_id: ID of the power generator model.
        :param gen_config: any additional configuration parameter for the power generator model.
        """
        self.gen_id: str = gen_id
        self.gen_config: dict[str, Any] = dict() if gen_config is None else gen_config


class EnergyStorageConfig:
    def __init__(self, capacity: float = 0, max_charge_rate: float = 0,
                 max_discharge_rate: float = 0, initial_charge: float = 0):
        """
        Energy storage configuration parameters.
        :param capacity: Maximum amount of energy (in W·h) that the Energy storage unit can hold.
        :param max_charge_rate: Maximum power (in Watts) that the energy storage unit can provide.
        :param max_discharge_rate: Maximum power (in Watts) that the energy storage unit can use to charge itself.
        :param initial_charge: initial capacity (in W·h) of the energy storage unit.
        """
        if capacity < 0:
            raise ValueError('Battery capacity must be greater equal to or greater than 0 W·h')
        self.capacity: float = capacity
        if initial_charge < 0 or initial_charge > capacity:
            raise ValueError('Initial charge must be within the valid boundaries')
        self.initial_charge: float = initial_charge
        if max_charge_rate < 0:
            raise ValueError('Maximum charge rate must be greater than or equal to 0')
        self.max_charge_rate: float = max_charge_rate
        if max_discharge_rate > 0:
            raise ValueError('Maximum discharge charge rate must be less than or equal to 0')
        self.max_discharge_rate: float = max_discharge_rate


class ConsumerConfig:
    def __init__(self, consumer_id: str, provider_id: str, storage_config: EnergyStorageConfig | None = None,
                 manager_id: str = 'static', manager_config: dict[str, Any] | None = None,
                 sources_config: dict[str, PowerGeneratorConfig] | None = None):
        """
        Smart Grid consumer configuration parameters.
        :param consumer_id: ID of the smart grid consumer.
        :param provider_id: ID of the energy provider that offers electricity to the smart grid consumer.
        :param storage_config: storage configuration of the consumer. By default, the consumer has no storage unit.
        :param manager_id: ID of the consumption manager model. By default, it is set to static (i.e., no change)
        :param manager_config: Any additional configuration parameter for the consumption manager model.
        :param sources_config: Dictionary containing the configuration of all the power sources of the consumer.
        """
        self.consumer_id: str = consumer_id
        self.provider_id: str = provider_id
        self.storage_config: EnergyStorageConfig = EnergyStorageConfig() if storage_config is None else storage_config
        self.manager_id: str = manager_id
        self.manager_config: dict[str, Any] = dict() if manager_config is None else manager_config
        self.sources_config: dict[str, PowerGeneratorConfig] = dict() if sources_config is None else sources_config


class SmartGridConfig:
    def __init__(self):
        """Smart Grid configuration parameters."""
        self.providers_config: dict[str, EnergyProviderConfig] = dict()
        self.consumers_config: dict[str, ConsumerConfig] = dict()

    def add_provider(self, provider_id: str, provider_type: str, provider_config: dict[str, Any] | None = None):
        self.providers_config[provider_id] = EnergyProviderConfig(provider_id, provider_type, provider_config)

    def add_consumer(self, consumer_id: str, provider_id: str, storage_config: EnergyStorageConfig | None = None,
                     manager_id: str = 'static', manager_config: dict[str, Any] | None = None,
                     sources: dict[str, PowerGeneratorConfig] | None = None) -> ConsumerConfig:
        if consumer_id in self.consumers_config:
            raise ValueError(f'Smart grid consumer {consumer_id} already defined')
        if provider_id not in self.providers_config:
            raise ValueError(f'Smart grid energy provider {provider_id} not defined')
        consumer_config = ConsumerConfig(consumer_id, provider_id, storage_config, manager_id, manager_config, sources)
        self.consumers_config[consumer_id] = consumer_config
        return consumer_config
