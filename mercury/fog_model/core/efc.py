from xdevs.models import Port
from typing import Dict, Set, Optional, Any
from mercury.plugin.factory import AbstractFactory
from mercury.fog_model.common import ExtendedAtomic
from mercury.config.edcs import EdgeFederationConfig
from mercury.msg.cnfs import DemandEstimation, EdgeDataCenterSlicing
from mercury.msg.edcs import DispatchingFunction, HotStandbyFunction
from mercury.msg.smart_grid import ElectricityOffer, PowerConsumptionReport


class EdgeFederationController(ExtendedAtomic):

    def __init__(self, edge_fed_config: EdgeFederationConfig, services: Set[str]):

        super().__init__("edcs_controller")

        self.input_demand_estimation = Port(DemandEstimation, 'input_demand_estimation')
        self.input_electricity_offer = Port(ElectricityOffer, 'input_electricity_offer')
        self.input_edc_report = Port(PowerConsumptionReport, 'input_edc_report')
        self.output_edc_slicing = Port(EdgeDataCenterSlicing, 'output_edc_slicing')
        self.output_dispatching = Port(DispatchingFunction, 'output_dispatching')
        self.output_hot_standby = Port(HotStandbyFunction, 'output_hot_standby')

        self.add_in_port(self.input_demand_estimation)
        self.add_in_port(self.input_electricity_offer)
        self.add_in_port(self.input_edc_report)
        self.add_out_port(self.output_edc_slicing)
        self.add_out_port(self.output_dispatching)
        self.add_out_port(self.output_hot_standby)

        self.services: Dict[str, Optional[float]] = {service: None for service in services}
        self.edcs: Dict[str, Optional[PowerConsumptionReport]] = {edc: None for edc in edge_fed_config.edcs}
        self.electricity_offers: Dict[str, Optional[float]] = dict()

        efc_config = edge_fed_config.efc

        name: str = efc_config.demand_share_name
        config: Dict[str, Any] = efc_config.demand_share_config
        self.demand_share = AbstractFactory.create_edc_demand_share(name, **config)

        self.dyn_dispatching = None
        if efc_config.dyn_dispatching_name is not None:
            name = efc_config.dyn_dispatching_name
            config = efc_config.dyn_dispatching_config
            config['edcs_config'] = edge_fed_config.edcs
            self.dyn_dispatching = AbstractFactory.create_edc_dyn_dispatching(name, **config)

        self.dyn_hot_standby = None
        if efc_config.dyn_hot_standby_name is not None:
            name = efc_config.dyn_hot_standby_name
            config = efc_config.dyn_hot_standby_config
            config['edcs_config'] = edge_fed_config.edcs
            self.dyn_hot_standby = AbstractFactory.create_edc_dyn_hot_standby(name, **config)

        self.dyn_slicing = None
        if efc_config.dyn_slicing_name is not None:
            name = efc_config.dyn_slicing_name
            config = efc_config.dyn_slicing_config
            self.dyn_slicing = AbstractFactory.create_edc_dyn_slicing(name, **config)

        self.cool_down = efc_config.cool_down
        self.next_timeout = 0
        self.waiting = False

    def deltint_extension(self):
        if self.waiting:  # If controller was cooling down, it triggers a new configuration exploration
            self.explore_configurations()
        self.passivate() if self.msg_queue_empty() else self.activate()

    def deltext_extension(self, e):
        self.get_new_data()
        if self._clock < self.next_timeout:  # If controller is cooling down, it waits before doing anything else
            self.hold_in(self.phase, self.next_timeout - self._clock)
        else:  # Otherwise, we explore new configurations
            self.explore_configurations()
            self.passivate() if self.msg_queue_empty() else self.activate()

    def get_new_data(self) -> None:
        self.waiting = True
        for msg in self.input_demand_estimation.values:
            self.services[msg.service_id] = msg.demand_estimation
        for msg in self.input_electricity_offer.values:
            self.electricity_offers[msg.provider_id] = msg.cost
        for msg in self.input_edc_report.values:
            self.edcs[msg.consumer_id] = msg

    def explore_configurations(self) -> None:
        if any((edc_report is not None for edc_report in self.edcs.values())):
            self.waiting = False
            self.next_timeout = self._clock + self.cool_down
            self.demand_share.demand_share(self.edcs, self.electricity_offers, self.services)
            self.explore_slicing()
            for edc_id, edc_report in self.edcs.items():
                if edc_report is not None:
                    electricity_offer = self.electricity_offers.get(edc_report.provider_id, None)
                    demand_estimation = self.demand_share.share[edc_id]
                    self.explore_dispatching(edc_id, electricity_offer, demand_estimation)
                    self.explore_hot_standby(edc_id, electricity_offer, demand_estimation)

    def explore_slicing(self):
        if self.dyn_slicing is not None:
            new_slicing = self.dyn_slicing.slicing(self.edcs, self.electricity_offers, self.demand_share.share)
            for slicing in new_slicing.values():
                self.add_msg_to_queue(self.output_edc_slicing, slicing)

    def explore_dispatching(self, edc: str, electricity_cost: Optional[float], services: Dict[str, Optional[float]]):
        if self.dyn_dispatching is not None:
            new_dispatching = self.dyn_dispatching.mapping(edc, electricity_cost, services)
            if new_dispatching is not None:
                self.add_msg_to_queue(self.output_dispatching, new_dispatching)

    def explore_hot_standby(self, edc: str, electricity_cost: Optional[float], services: Dict[str, Optional[float]]):
        if self.dyn_hot_standby is not None:
            new_hot_standby = self.dyn_hot_standby.hot_standby(edc, electricity_cost, services)
            if new_hot_standby is not None:
                self.add_msg_to_queue(self.output_hot_standby, new_hot_standby)

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
