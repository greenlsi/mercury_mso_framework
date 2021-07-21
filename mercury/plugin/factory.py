import pkg_resources
from typing import Dict, Generic, Type, TypeVar
from .cnfs import SDNStrategy, DemandEstimationGenerator
from .cnfs.efc import DemandShare, DynamicSlicing, DynamicMapping, DynamicHotStandby
from .edc import MappingStrategy, HotStandbyStrategy, SchedulingAlgorithm, ProcessingUnitPowerModel, \
    ProcessingUnitTemperatureModel, EdgeDataCenterCoolerPowerModel, EdgeDataCenterCoolerTemperatureModel
from .network import Attenuation, ChannelDivision, NodeMobility, Noise
from .service import ServiceRequestProfile, ServiceSessionProfile, ServiceSessionDuration
from .smart_grid import EnergyProvider, PowerSource, ConsumptionManager


T = TypeVar('T')


class Factory(Generic[T]):
    def __init__(self, entry_point: str):
        self._entities = {key: entity for key, entity in self.load_plugins(entry_point).items()}

    def register(self, key: str, entity: Type[T]):
        if self.defined(key):
            raise ValueError('There is an already defined entity with that name')
        self._entities[key] = entity

    def defined(self, key: str) -> bool:
        return key in self._entities

    def create(self, key: str, **kwargs) -> T:
        if not self.defined(key):
            raise ValueError('Model name "{}" not defined'.format(key))
        return self._entities[key](**kwargs)

    @staticmethod
    def load_plugins(namespace: str) -> dict:
        res = dict()
        for ep in pkg_resources.iter_entry_points(group=namespace):
            try:
                res[ep.name] = ep.load(require=True)
            except pkg_resources.UnknownExtra as ue:
                print("Plugin %r dependencies resolution failed: %s" % (ep, ue))
        return res


class AbstractFactory:

    base_plugins = {
        'cnf_sdn': 'mercury.cnfs.sdn_strategy.plugins',
        'cnf_demand': 'mercury.cnfs.demand_estimation.plugins',
        'smart_grid_provider': 'mercury.smart_grid.energy_provider.plugins',
        'smart_grid_manager': 'mercury.smart_grid.consumers_manager.plugins',
        'smart_grid_consumption_manager': 'mercury.smart_grid.consumption_manager.plugins',
        'smart_grid_source': 'mercury.smart_grid.pwr_source.plugins',
        'edc_demand_share': 'mercury.edc.demand_share.plugins',
        'edc_dyn_mapping': 'mercury.edc.dyn_mapping.plugins',
        'edc_dyn_hot_standby': 'mercury.edc.dyn_hot_standby.plugins',
        'edc_dyn_slicing': 'mercury.edc.dyn_slicing.plugins',
        'edc_mapping': 'mercury.edc.mapping.plugins',
        'edc_hot_standby': 'mercury.edc.hot_standby.plugins',
        'edc_scheduling': 'mercury.edc.scheduling.plugins',
        'edc_pu_pwr': 'mercury.edc.pu.pwr.plugins',
        'edc_pu_temp': 'mercury.edc.pu.temp.plugins',
        'edc_cooler_pwr': 'mercury.edc.rack.cooler_pwr.plugins',
        'edc_cooler_temp': 'mercury.edc.rack.cooler_temp.plugins',
        'network_attenuation': 'mercury.network.attenuation.plugins',
        'network_noise': 'mercury.network.noise.plugins',
        'network_channel_division': 'mercury.network.channel_division.plugins',
        'mobility': 'mercury.mobility.plugins',
        'srv_request_profile': 'mercury.service.request_profile.plugins',
        'srv_session_profile': 'mercury.service.session_profile.plugins',
        'srv_session_duration': 'mercury.service.session_duration.plugins',
    }
    factories: Dict[str, Factory] = {key: Factory(entry_point) for key, entry_point in base_plugins.items()}

    @staticmethod
    def register_sdn_strategy(key: str, model: Type[SDNStrategy]):
        AbstractFactory.factories['cnf_sdn'].register(key, model)

    @staticmethod
    def create_sdn_strategy(key: str, **kwargs) -> SDNStrategy:
        return AbstractFactory.factories['cnf_sdn'].create(key, **kwargs)

    @staticmethod
    def register_demand_estimator(key: str, model: Type[DemandEstimationGenerator]):
        AbstractFactory.factories['cnf_demand'].register(key, model)

    @staticmethod
    def create_demand_estimator(key: str, **kwargs) -> DemandEstimationGenerator:
        return AbstractFactory.factories['cnf_demand'].create(key, **kwargs)

    @staticmethod
    def register_smart_grid_provider(key: str, model: Type[EnergyProvider]):
        AbstractFactory.factories['smart_grid_provider'].register(key, model)

    @staticmethod
    def create_smart_grid_provider(key: str, **kwargs) -> EnergyProvider:
        return AbstractFactory.factories['smart_grid_provider'].create(key, **kwargs)

    @staticmethod
    def register_smart_grid_consumption_manager(key: str, model: Type[ConsumptionManager]):
        AbstractFactory.factories['smart_grid_consumption_manager'].register(key, model)

    @staticmethod
    def create_smart_grid_consumption_manager(key: str, **kwargs) -> ConsumptionManager:
        return AbstractFactory.factories['smart_grid_consumption_manager'].create(key, **kwargs)

    @staticmethod
    def register_smart_grid_source(key: str, model: Type[PowerSource]):
        AbstractFactory.factories['smart_grid_source'].register(key, model)

    @staticmethod
    def create_smart_grid_source(key: str, **kwargs) -> PowerSource:
        return AbstractFactory.factories['smart_grid_source'].create(key, **kwargs)

    @staticmethod
    def register_edc_demand_share(key: str, model: Type[DemandShare]):
        AbstractFactory.factories['edc_demand_share'].register(key, model)

    @staticmethod
    def create_edc_demand_share(key: str, **kwargs) -> DemandShare:
        return AbstractFactory.factories['edc_demand_share'].create(key, **kwargs)

    @staticmethod
    def register_edc_dyn_dispatching(key: str, model: Type[DynamicMapping]):
        AbstractFactory.factories['edc_dyn_dispatching'].register(key, model)

    @staticmethod
    def create_edc_dyn_dispatching(key: str, **kwargs) -> DynamicMapping:
        return AbstractFactory.factories['edc_dyn_dispatching'].create(key, **kwargs)

    @staticmethod
    def register_edc_dyn_hot_standby(key: str, model: Type[DynamicHotStandby]):
        AbstractFactory.factories['edc_dyn_hot_standby'].register(key, model)

    @staticmethod
    def create_edc_dyn_hot_standby(key: str, **kwargs) -> DynamicHotStandby:
        return AbstractFactory.factories['edc_dyn_hot_standby'].create(key, **kwargs)

    @staticmethod
    def register_edc_dyn_slicing(key: str, model: Type[DynamicSlicing]):
        AbstractFactory.factories['edc_dyn_slicing'].register(key, model)

    @staticmethod
    def create_edc_dyn_slicing(key: str, **kwargs) -> DynamicSlicing:
        return AbstractFactory.factories['edc_dyn_slicing'].create(key, **kwargs)

    @staticmethod
    def register_edc_mapping(key: str, model: Type[MappingStrategy]):
        AbstractFactory.factories['edc_mapping'].register(key, model)

    @staticmethod
    def create_edc_mapping(key: str, **kwargs) -> MappingStrategy:
        return AbstractFactory.factories['edc_mapping'].create(key, **kwargs)

    @staticmethod
    def register_edc_hot_standby(key: str, model: Type[HotStandbyStrategy]):
        AbstractFactory.factories['edc_hot_standby'].register(key, model)

    @staticmethod
    def create_edc_hot_standby(key: str, **kwargs) -> HotStandbyStrategy:
        return AbstractFactory.factories['edc_hot_standby'].create(key, **kwargs)

    @staticmethod
    def register_edc_scheduling_algorithm(key: str, model: Type[SchedulingAlgorithm]):
        AbstractFactory.factories['edc_scheduling'].register(key, model)

    @staticmethod
    def create_scheduling_algorithm(key: str, **kwargs) -> SchedulingAlgorithm:
        return AbstractFactory.factories['edc_scheduling'].create(key, **kwargs)

    @staticmethod
    def register_edc_pu_pwr(key: str, model: Type[ProcessingUnitPowerModel]):
        AbstractFactory.factories['edc_pu_pwr'].register(key, model)

    @staticmethod
    def create_edc_pu_pwr(key: str, **kwargs) -> ProcessingUnitPowerModel:
        return AbstractFactory.factories['edc_pu_pwr'].create(key, **kwargs)

    @staticmethod
    def register_edc_pu_temp(key: str, model: Type[ProcessingUnitTemperatureModel]):
        AbstractFactory.factories['edc_pu_temp'].register(key, model)

    @staticmethod
    def create_edc_pu_temp(key: str, **kwargs) -> ProcessingUnitTemperatureModel:
        return AbstractFactory.factories['edc_pu_temp'].create(key, **kwargs)

    @staticmethod
    def register_edc_cooler_pwr(key: str, model: Type[EdgeDataCenterCoolerPowerModel]):
        AbstractFactory.factories['edc_cooler_pwr'].register(key, model)

    @staticmethod
    def create_edc_cooler_pwr(key: str, **kwargs) -> EdgeDataCenterCoolerPowerModel:
        return AbstractFactory.factories['edc_cooler_pwr'].create(key, **kwargs)

    @staticmethod
    def register_edc_cooler_temp(key: str, model: Type[EdgeDataCenterCoolerTemperatureModel]):
        AbstractFactory.factories['edc_cooler_temp'].register(key, model)

    @staticmethod
    def create_edc_cooler_temp(key: str, **kwargs) -> EdgeDataCenterCoolerTemperatureModel:
        return AbstractFactory.factories['edc_cooler_temp'].create(key, **kwargs)

    @staticmethod
    def register_network_attenuation(key: str, model: Type[Attenuation]):
        AbstractFactory.factories['network_attenuation'].register(key, model)

    @staticmethod
    def create_network_attenuation(key: str, **kwargs) -> Attenuation:
        return AbstractFactory.factories['network_attenuation'].create(key, **kwargs)

    @staticmethod
    def register_network_noise(key: str, model: Type[Noise]):
        AbstractFactory.factories['network_noise'].register(key, model)

    @staticmethod
    def create_network_noise(key: str, **kwargs) -> Noise:
        return AbstractFactory.factories['network_noise'].create(key, **kwargs)

    @staticmethod
    def register_network_channel_division(key: str, model: Type[ChannelDivision]):
        AbstractFactory.factories['network_channel_division'].register(key, model)

    @staticmethod
    def create_network_channel_division(key: str, **kwargs) -> ChannelDivision:
        return AbstractFactory.factories['network_channel_division'].create(key, **kwargs)

    @staticmethod
    def register_mobility(key: str, model: Type[NodeMobility]):
        AbstractFactory.factories['mobility'].register(key, model)

    @staticmethod
    def create_mobility(key: str, **kwargs) -> NodeMobility:
        return AbstractFactory.factories['mobility'].create(key, **kwargs)

    @staticmethod
    def register_srv_request_profile(key: str, model: Type[ServiceRequestProfile]):
        AbstractFactory.factories['srv_request_profile'].register(key, model)

    @staticmethod
    def create_srv_request_profile(key: str, **kwargs) -> ServiceRequestProfile:
        return AbstractFactory.factories['srv_request_profile'].create(key, **kwargs)

    @staticmethod
    def register_srv_session_profile(key: str, model: Type[ServiceSessionProfile]):
        AbstractFactory.factories['srv_session_profile'].register(key, model)

    @staticmethod
    def create_srv_session_profile(key: str, **kwargs) -> ServiceSessionProfile:
        return AbstractFactory.factories['srv_session_profile'].create(key, **kwargs)

    @staticmethod
    def register_srv_session_duration(key: str, model: Type[ServiceSessionDuration]):
        AbstractFactory.factories['srv_session_duration'].register(key, model)

    @staticmethod
    def create_srv_session_duration(key: str, **kwargs) -> ServiceSessionDuration:
        return AbstractFactory.factories['srv_session_duration'].create(key, **kwargs)
