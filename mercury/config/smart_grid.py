from typing import Any, Dict, Optional


class EnergyProviderConfig:
    def __init__(self, provider_id: str, provider_type: str, provider_config: Optional[Dict[str, Any]] = None):
        """
        Energy provider configuration parameters.
        :param provider_id: ID of the energy provider.
        :param provider_type: type of energy provider model.
        :param provider_config: any additional configuration parameter for the energy provider model.
        """
        self.provider_id: str = provider_id
        self.provider_type: str = provider_type
        self.provider_config: Dict[str, Any] = dict() if provider_config is None else provider_config


class PowerSourceConfig:
    def __init__(self, source_type: str, source_config: Optional[Dict[str, Any]] = None):
        """
        Power source configuration parameters.
        :param source_type: type of the power source model.
        :param source_config: any additional configuration parameter for the power source model.
        """
        self.source_type: str = source_type
        self.source_config: Dict[str, Any] = dict() if source_config is None else source_config


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
    def __init__(self, consumer_id: str, provider_id: str, storage_config: Optional[EnergyStorageConfig] = None,
                 consumption_manager_name: str = 'static', consumption_manager_config: Optional[Dict[str, Any]] = None,
                 sources_config: Optional[Dict[str, PowerSourceConfig]] = None):
        """
        Smart Grid consumer configuration parameters.
        :param consumer_id: ID of the smart grid consumer.
        :param provider_id: ID of the energy provider that offers electricity to the smart grid consumer.
        :param storage_config: storage configuration of the consumer. By default, the consumer has no storage unit.
        :param consumption_manager_name: name of the consumption manager model.
                                         By default, it is set to static (i.e., it doesn't change during the simulation)
        :param consumption_manager_config: Any additional configuration parameter for the consumption manager model.
        :param sources_config: Dictionary containing the configuration of all the power sources of the consumer.
                               By default, a consumer doesn't have any power source.
        """
        self.consumer_id: str = consumer_id
        self.provider_id: str = provider_id
        self.storage_config: EnergyStorageConfig = EnergyStorageConfig() if storage_config is None else storage_config
        self.consumption_manager_name: str = consumption_manager_name
        self.consumption_manager_config: Dict[str, Any] = dict() if consumption_manager_config is None \
            else consumption_manager_config
        self.sources_config: Dict[str, PowerSourceConfig] = dict() if sources_config is None else sources_config


class SmartGridConfig:
    def __init__(self, providers_config: Dict[str, EnergyProviderConfig], consumers_config: Dict[str, ConsumerConfig]):
        """
        Smart Grid configuration parameters.
        :param providers_config: dictionary with the configuration of all the energy providers
        :param consumers_config: dictionary with the configuration of all the smart grid consumers.
        """
        self.providers_config: Dict[str, EnergyProviderConfig] = providers_config
        self.consumers_config: Dict[str, ConsumerConfig] = consumers_config
