import pkg_resources
from typing import Dict, Generic, Type, TypeVar
from .client import ClientGenerator, SrvRequestGenerator, SrvActivityGenerator, SrvActivityWindowGenerator
from .cloud import CloudNetworkDelay, CloudProcTimeModel
from .edc import *
from .network import Attenuation, ChannelDivision, NodeMobility, Noise
from .smart_grid import EnergyCostGenerator, PowerGenerationGenerator, ConsumerManager
from .optimization import CostFunction, MoveFunction, Optimizer


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
            raise ValueError(f'Model name "{key}" not defined')
        return self._entities[key](**kwargs)

    @staticmethod
    def load_plugins(namespace: str) -> dict:
        res = dict()
        for ep in pkg_resources.iter_entry_points(group=namespace):
            try:
                res[ep.name] = ep.load(require=True)
            except pkg_resources.UnknownExtra as ue:
                raise ValueError(f'Plugin {ep} dependencies resolution failed: {ue}')
        return res


class AbstractFactory:
    base_plugins = {
        'sg_energy_cost': 'mercury.smart_grid.energy_cost.plugins',
        'sg_consumer_manager': 'mercury.smart_grid.consumer_manager.plugins',
        'sg_pwr_generation': 'mercury.smart_grid.pwr_generation.plugins',
        'cloud_network_delay': 'mercury.cloud.network_delay.plugins',
        'cloud_proc_t': 'mercury.cloud.proc_t.plugins',
        'edc_cooler_pwr': 'mercury.edc.cooler.power.plugins',
        'edc_dyn_demand': 'mercury.edc.dyn.demand.plugins',
        'edc_dyn_mapping': 'mercury.edc.dyn.mapping.plugins',
        'edc_dyn_slicing': 'mercury.edc.dyn.slicing.plugins',
        'edc_dyn_standby': 'mercury.edc.dyn.standby.plugins',
        'edc_pu_proc_t': 'mercury.edc.pu.proc_t.plugins',
        'edc_pu_pwr': 'mercury.edc.pu.power.plugins',
        'edc_pu_temp': 'mercury.edc.pu.temperature.plugins',
        'edc_pu_scheduler': 'mercury.edc.pu.scheduler.plugins',
        'edc_pu_mapping': 'mercury.edc.pu.mapping.plugins',
        'edc_server_mapping': 'mercury.edc.server.mapping.plugins',
        'edc_hot_standby': 'mercury.edc.hot_standby.plugins',
        'network_attenuation': 'mercury.network.attenuation.plugins',
        'network_noise': 'mercury.network.noise.plugins',
        'network_channel_division': 'mercury.network.channel_division.plugins',
        'mobility': 'mercury.mobility.plugins',
        'client_generator': 'mercury.client.client_generator.plugins',
        'srv_activity_generator': 'mercury.client.srv_activity_generator.plugins',
        'srv_activity_window': 'mercury.client.srv_activity_window.plugins',
        'srv_req_generator': 'mercury.client.srv_req_generator.plugins',
        'cost_function': 'mercury.optimization.cost_function.plugins',
        'move_function': 'mercury.optimization.move_function.plugins',
        'optimizer': 'mercury.optimization.optimizer.plugins',
    }
    factories: Dict[str, Factory] = {key: Factory(entry_point) for key, entry_point in base_plugins.items()}

    @staticmethod
    def register_sg_energy_cost(key: str, model: Type[EnergyCostGenerator]):
        AbstractFactory.factories['sg_energy_cost'].register(key, model)

    @staticmethod
    def create_sg_energy_cost(key: str, **kwargs) -> EnergyCostGenerator:
        return AbstractFactory.factories['sg_energy_cost'].create(key, **kwargs)

    @staticmethod
    def register_sg_consumer_manager(key: str, model: Type[ConsumerManager]):
        AbstractFactory.factories['sg_consumer_manager'].register(key, model)

    @staticmethod
    def create_sg_consumer_manager(key: str, **kwargs) -> ConsumerManager:
        return AbstractFactory.factories['sg_consumer_manager'].create(key, **kwargs)

    @staticmethod
    def register_sg_pwr_generation(key: str, model: Type[PowerGenerationGenerator]):
        AbstractFactory.factories['sg_pwr_generation'].register(key, model)

    @staticmethod
    def create_sg_pwr_generation(key: str, **kwargs) -> PowerGenerationGenerator:
        return AbstractFactory.factories['sg_pwr_generation'].create(key, **kwargs)

    @staticmethod
    def register_cloud_net_delay(key: str, model: Type[CloudNetworkDelay]):
        AbstractFactory.factories['cloud_network_delay'].register(key, model)

    @staticmethod
    def create_cloud_net_delay(key: str, **kwargs) -> CloudNetworkDelay:
        return AbstractFactory.factories['cloud_network_delay'].create(key, **kwargs)

    @staticmethod
    def register_cloud_proc_t(key: str, model: Type[CloudProcTimeModel]):
        AbstractFactory.factories['cloud_proc_t'].register(key, model)

    @staticmethod
    def create_cloud_proc_t(key: str, **kwargs) -> CloudProcTimeModel:
        return AbstractFactory.factories['cloud_proc_t'].create(key, **kwargs)

    @staticmethod
    def register_demand_estimation(key: str, model: Type[SrvDemandEstimator]):
        AbstractFactory.factories['edc_dyn_demand'].register(key, model)

    @staticmethod
    def create_demand_estimation(key: str, **kwargs) -> SrvDemandEstimator:
        return AbstractFactory.factories['edc_dyn_demand'].create(key, **kwargs)

    @staticmethod
    def register_edc_dyn_mapping(key: str, model: Type[DynamicEDCMapping]):
        AbstractFactory.factories['edc_dyn_mapping'].register(key, model)

    @staticmethod
    def create_edc_dyn_mapping(key: str, **kwargs) -> DynamicEDCMapping:
        return AbstractFactory.factories['edc_dyn_mapping'].create(key, **kwargs)

    @staticmethod
    def register_edc_dyn_slicing(key: str, model: Type[DynamicEDCSlicing]):
        AbstractFactory.factories['edc_dyn_slicing'].register(key, model)

    @staticmethod
    def create_edc_dyn_slicing(key: str, **kwargs) -> DynamicEDCSlicing:
        return AbstractFactory.factories['edc_dyn_slicing'].create(key, **kwargs)

    @staticmethod
    def register_edc_server_mapping(key: str, model: Type[ServerMappingStrategy]):
        AbstractFactory.factories['edc_server_mapping'].register(key, model)

    @staticmethod
    def create_edc_server_mapping(key: str, **kwargs) -> ServerMappingStrategy:
        return AbstractFactory.factories['edc_server_mapping'].create(key, **kwargs)

    @staticmethod
    def register_edc_pu_mapping(key: str, model: Type[PUMappingStrategy]):
        AbstractFactory.factories['edc_pu_mapping'].register(key, model)

    @staticmethod
    def create_edc_pu_mapping(key: str, **kwargs) -> PUMappingStrategy:
        return AbstractFactory.factories['edc_pu_mapping'].create(key, **kwargs)

    @staticmethod
    def register_edc_pu_scheduler(key: str, model: Type[ProcessingUnitScheduler]):
        AbstractFactory.factories['edc_pu_scheduler'].register(key, model)

    @staticmethod
    def create_edc_pu_scheduler(key: str, **kwargs) -> ProcessingUnitScheduler:
        return AbstractFactory.factories['edc_pu_scheduler'].create(key, **kwargs)

    @staticmethod
    def register_edc_pu_pwr(key: str, model: Type[ProcessingUnitPowerModel]):
        AbstractFactory.factories['edc_pu_pwr'].register(key, model)

    @staticmethod
    def create_edc_pu_pwr(key: str, **kwargs) -> ProcessingUnitPowerModel:
        return AbstractFactory.factories['edc_pu_pwr'].create(key, **kwargs)

    @staticmethod
    def register_edc_pu_proc_t(key: str, model: Type[ProcessingUnitProcTimeModel]):
        AbstractFactory.factories['edc_pu_proc_t'].register(key, model)

    @staticmethod
    def create_edc_pu_proc_t(key: str, **kwargs) -> ProcessingUnitProcTimeModel:
        return AbstractFactory.factories['edc_pu_proc_t'].create(key, **kwargs)

    @staticmethod
    def register_edc_pu_temp(key: str, model: Type[ProcessingUnitTemperatureModel]):
        AbstractFactory.factories['edc_pu_temp'].register(key, model)

    @staticmethod
    def create_edc_pu_temp(key: str, **kwargs) -> ProcessingUnitTemperatureModel:
        return AbstractFactory.factories['edc_pu_temp'].create(key, **kwargs)

    @staticmethod
    def register_edc_cooler_pwr(key: str, model: Type[CoolerPowerModel]):
        AbstractFactory.factories['edc_cooler_pwr'].register(key, model)

    @staticmethod
    def create_edc_cooler_pwr(key: str, **kwargs) -> CoolerPowerModel:
        return AbstractFactory.factories['edc_cooler_pwr'].create(key, **kwargs)

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
    def register_client_generator(key: str, model: Type[ClientGenerator]):
        AbstractFactory.factories['client_generator'].register(key, model)

    @staticmethod
    def create_client_generator(key: str, **kwargs) -> ClientGenerator:
        return AbstractFactory.factories['client_generator'].create(key, **kwargs)

    @staticmethod
    def register_srv_activity_generator(key: str, model: Type[SrvActivityGenerator]):
        AbstractFactory.factories['srv_activity_generator'].register(key, model)

    @staticmethod
    def create_srv_activity_generator(key: str, **kwargs) -> SrvActivityGenerator:
        return AbstractFactory.factories['srv_activity_generator'].create(key, **kwargs)

    @staticmethod
    def register_srv_activity_window(key: str, model: Type[SrvActivityWindowGenerator]):
        AbstractFactory.factories['srv_activity_window'].register(key, model)

    @staticmethod
    def create_srv_activity_window(key: str, **kwargs) -> SrvActivityWindowGenerator:
        return AbstractFactory.factories['srv_activity_window'].create(key, **kwargs)

    @staticmethod
    def register_srv_req_generator(key: str, model: Type[SrvRequestGenerator]):
        AbstractFactory.factories['srv_req_generator'].register(key, model)

    @staticmethod
    def create_srv_req_generator(key: str, **kwargs) -> SrvRequestGenerator:
        return AbstractFactory.factories['srv_req_generator'].create(key, **kwargs)

    @staticmethod
    def register_optimizer(key: str, model: Type[Optimizer]):
        AbstractFactory.factories['optimizer'].register(key, model)

    @staticmethod
    def create_optimizer(key: str, **kwargs) -> Optimizer:
        return AbstractFactory.factories['optimizer'].create(key, **kwargs)

    @staticmethod
    def register_cost_function(key: str, model: Type[CostFunction]):
        AbstractFactory.factories['cost_function'].register(key, model)

    @staticmethod
    def create_cost_function(key: str, **kwargs) -> CostFunction:
        return AbstractFactory.factories['cost_function'].create(key, **kwargs)

    @staticmethod
    def register_move_function(key: str, model: Type[MoveFunction]):
        AbstractFactory.factories['move_function'].register(key, model)

    @staticmethod
    def create_move_function(key: str, **kwargs) -> MoveFunction:
        return AbstractFactory.factories['move_function'].create(key, **kwargs)
