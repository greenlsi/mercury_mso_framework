from math import sqrt
from copy import deepcopy
from typing import Dict, List, Tuple
from abc import ABC, abstractmethod

from ..common.edge_fed.edge_fed import EdgeDataCenterReport
from ..common.plugin_loader import load_plugins


class SDNStrategy(ABC):
    """
    Software-Defined Network allocation strategy class.
    :param aps_location: Dictionary {AP ID: AP location}
    :param edcs_location: Dictionary {EDC ID: EDC location}
    :param services_id: list with the ID of all the services_config within the scenario
    :param float congestion: utilization factor to consider an EDC congested (from 0 to 100)
    :param Dict[str, Dict[str, float]] edc_slicing: {EDC ID: {Service ID: maximum allowed utilization factor}}
    :param kwargs: Any additional parameter
    """

    def __init__(self, aps: Dict[str, Tuple[float, ...]], edcs: Dict[str, Tuple[float, ...]],
                 services_id: List[str], **kwargs):
        self.aps_location = {ap: ap_location for ap, ap_location in aps.items()}
        self.edcs_location = {edc: edc_location for edc, edc_location in edcs.items()}
        self.services_id = services_id
        self.distances = self._precompute_distances()

        congestion = kwargs.get('congestion', 100)
        assert 0 <= congestion <= 100
        self.congestion = congestion

        edc_slicing = kwargs.get('edc_slicing', {edc_id: {service_id: 100 for service_id in self.services_id}
                                                 for edc_id in edcs})
        for services in edc_slicing.values():
            for service, max_u in services.items():
                assert service in services_id
                assert 0 <= max_u <= 100
            for service in services_id:
                assert service in services
        self.edc_slicing = edc_slicing

        self.edc_reports = {edc: None for edc in self.edcs_location.keys()}
        self.edcs_utilization = {edc: dict() for edc in self.edcs_location.keys()}
        self.available_edcs = {edc: False for edc in self.edcs_location.keys()}
        self.edcs_availability = {edc: dict() for edc in self.edcs_location.keys()}

    def update_locations(self, edcs_location: Dict[str, Tuple[float, ...]], aps_location: Dict[str, Tuple[float, ...]]):
        for edc, location in edcs_location.items():
            self.edcs_location[edc] = location
        for ap, location in aps_location.items():
            self.aps_location[ap] = location
        self._precompute_distances()

    def update_edc_report(self, edc_id: str, edc_report: EdgeDataCenterReport):
        self.edc_reports[edc_id] = deepcopy(edc_report)
        max_u = edc_report.max_std_u / 100
        utilization_dict = {service_id: u / max_u for service_id, u in edc_report.std_u_per_service.items()}
        overall_utilization = edc_report.overall_std_u / max_u
        self.update_edc_utilization(edc_id, utilization_dict, overall_utilization)

    def update_edc_utilization(self, edc_id: str, utilization_dict: Dict[str, float], overall_utilization: float):
        self.edcs_utilization[edc_id] = {service_id: service_u for service_id, service_u in utilization_dict.items()}
        self.available_edcs[edc_id] = overall_utilization < self.congestion
        for service_id, max_u in self.edc_slicing[edc_id].items():
            if service_id not in self.edcs_utilization[edc_id]:
                self.edcs_availability[edc_id][service_id] = max_u > 0
            else:
                service_u = self.edcs_utilization[edc_id][service_id]
                self.edcs_availability[edc_id][service_id] = service_u < self.edc_slicing[edc_id][service_id]

    @abstractmethod
    def assign_edc(self, ap_id: str) -> Dict[str, str]:
        """
        From a list of available Edge Data Centers, the optimal is chosen for a given Access Point
        :param ap_id: ID of the Access Point under study
        :return Best Edge Data Center ID per service
        """
        pass

    def _precompute_distances(self) -> Dict[str, List[Tuple[str, float]]]:
        """
        Pre-computes the distance between APs and EDCs of the scenario to reduce computation during simulation.
        :return: {ap_id: [(edc_id, distance(AP, EDC))]} (EDCs are sorted from less to greater distance)
        """
        res = dict()
        for ap_id, ap_location in self.aps_location.items():
            distances = list()
            for edc_id, edc_location in self.edcs_location.items():
                # Compute the Euclidian distance between AP and EDC
                distance = sqrt(sum([(ap_location[i] - edc_location[i]) ** 2 for i in range(len(ap_location))]))
                distances.append((edc_id, distance))
            res[ap_id] = sorted(distances, key=lambda x: x[1])  # Sort all the distances, from closest to furthest
        return res

    def is_available(self, edc_id: str, service_id: str) -> bool:
        """
        Checks whether or not a given EDC is able to host new sessions of a specific service
        :param edc_id: EDC ID
        :param service_id: Service ID
        """
        return self.available_edcs[edc_id] and self.edcs_availability[edc_id][service_id]


class SDNClosestStrategy(SDNStrategy):
    def assign_edc(self, ap_id: str) -> Dict[str, str]:
        """
        From a list of available Edge Data Centers, the closest to a given Access Point is chosen
        :return: dictionary {service_id: edc_id} with the most suitable EDC for each service
        """
        service_routing = {service_id: None for service_id in self.services_id}
        if ap_id in self.distances:
            for service_id in self.services_id:
                for edc_id, edc_distance in self.distances[ap_id]:
                    if self.is_available(edc_id, service_id):
                        service_routing[service_id] = edc_id
                        break
        return service_routing


class SDNStrategyFactory:
    def __init__(self):
        self._strategy = dict()
        for key, strategy in load_plugins('mercury.sdn_strategy.plugins').items():
            self.register_strategy(key, strategy)

    def register_strategy(self, key: str, strategy: SDNStrategy):
        self._strategy[key] = strategy

    def is_strategy_defined(self, key: str) -> bool:
        return key in self._strategy

    def create_strategy(self, key, aps_location, edcs_location, services_id, **kwargs) -> SDNStrategy:
        strategy = self._strategy.get(key)
        if not strategy:
            raise ValueError(key)
        return strategy(aps_location, edcs_location, services_id, **kwargs)
