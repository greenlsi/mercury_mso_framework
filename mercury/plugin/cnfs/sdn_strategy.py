from math import sqrt, inf
from functools import lru_cache
from abc import ABC, abstractmethod
from typing import Dict, Set, Tuple, Optional
from mercury.config.smart_grid import ConsumerConfig
from mercury.msg.smart_grid import PowerConsumptionReport


class SDNStrategy(ABC):
    def __init__(self, **kwargs):
        """
        Software-Defined Network allocation strategy class.
        :param aps: Dictionary {AP ID: AP location}
        :param edc: Dictionary {EDC ID: EDC location}
        :param services: list with the ID of all the services_config within the scenario
        :param consumers: smart grid consumer configuration for EDCs
        :param float congestion: utilization factor to consider an EDC congested (from 0 to 100)
        :param Dict[str, Dict[str, float]] edc_slicing: {EDC ID: {Service ID: maximum allowed utilization factor}}
        :param kwargs: Any additional parameter
        """
        self.aps: Dict[str, Tuple[float, ...]] = kwargs.get('aps')
        self.edcs: Dict[str, Tuple[float, ...]] = kwargs.get('edcs')
        self.services: Set[str] = kwargs.get('services')

        consumers: Dict[str, ConsumerConfig] = kwargs.get('consumers', dict())
        self.consumers: Dict[str, str] = {consumer: config.provider_id for consumer, config in consumers.items()}
        self.subscriptions: Dict[str, Set[str]] = dict()
        for consumer_id, provider_id in self.consumers.items():
            if provider_id not in self.subscriptions:
                self.subscriptions[provider_id] = set()
            self.subscriptions[provider_id].add(consumer_id)
        self.offers: Dict[str, float] = {provider_id: inf for provider_id in self.subscriptions}

        self.congestion: float = kwargs.get('edc_congestion', 100)
        self.edc_slicing: Dict[str, Dict[str, float]] = dict()
        edc_slicing: Dict[str, Dict[str, float]] = kwargs.get('edc_slicing', dict())
        for edc_id, services in edc_slicing.items():
            self.update_edc_slicing(edc_id, services)

        self.edc_reports: Dict[str, Optional[PowerConsumptionReport]] = {edc: None for edc in self.edcs.keys()}
        self.edcs_availability: Dict[str, Dict[str, bool]] = {edc: {service_id: False for service_id in self.services}
                                                              for edc in self.edcs.keys()}

    def update_edc_report(self, edc_id: str, consumption_report: PowerConsumptionReport):
        self.edc_reports[edc_id] = consumption_report
        if consumption_report.report is not None:
            service_slicing = self.edc_slicing.get(edc_id, dict())
            for service_id in self.services:
                service_u = self.edc_reports[edc_id].report.service_utilization(service_id)
                availability = service_u < self.congestion and service_u < service_slicing.get(service_id, 100)
                self.edcs_availability[edc_id][service_id] = availability

    def update_electricity_offer(self, provider_id: str, offer: float):
        self.offers[provider_id] = offer

    def update_edc_slicing(self, edc_id: str, services: Dict[str, float]):
        for service, max_u in services.items():
            assert service in self.services
            assert 0 <= max_u <= 100
        self.edc_slicing[edc_id] = services

    def edc_available(self, edc_id: str, service_id: str) -> bool:
        """
        Checks whether or not a given EDC is able to host new sessions of a specific service
        :param edc_id: EDC ID
        :param service_id: Service ID
        :return edc_availability: whether or not a given EDC is able to host new sessions of a specific service
        """
        return self.edcs_availability[edc_id][service_id]

    def edc_utilization(self, edc_id: str, service_id: str) -> float:
        """
        Returns percentage of resources
        :param edc_id: EDC ID
        :param service_id: Service ID
        :return: resource utilization
        """
        return self.edc_reports[edc_id].report.service_utilization(service_id)

    def electricity_cost(self, edc_id: str) -> float:
        """
        Returns electricity cost for a given EDC.
        :param edc_id: identifier of the EDC
        :return: cost if provider is found. Otherwise, it returns None
        """
        edc_report = self.edc_reports.get(edc_id, None)
        return inf if edc_report is None else self.offers.get(edc_report.provider_id, inf)

    @lru_cache(maxsize=None)
    def distance(self, ap_id: str, edc_id: str) -> float:
        """
        Computes the distance between an AP and an EDC. This function is cached to speed up the performance.
        :param ap_id: AP ID
        :param edc_id: EDC ID
        :return: distance between AP and EDC
        """
        ap_location = self.aps[ap_id]
        edc_location = self.edcs[edc_id]
        return sqrt(sum([(ap_location[i] - edc_location[i]) ** 2 for i in range(len(ap_location))]))

    @abstractmethod
    def assign_edc(self, ap_id: str, service_id: str) -> Optional[str]:
        """
        From a list of available Edge Data Centers, the optimal is chosen for a given Access Point.
        :param ap_id: ID of the Access Point under study
        :param service_id: ID of the service under study
        :return Best Edge Data Center ID for the service
        """
        pass


class SDNMinimumCostStrategy(SDNStrategy, ABC):
    """ This version adapts the SDN assignation strategy to a cost-driven approach """
    @property
    def max_cost(self):
        return inf

    def assign_edc(self, ap_id: str, service_id: str) -> Optional[str]:
        best_edc, best_cost = None, self.max_cost
        for edc_id in self.edcs:
            if self.edc_available(edc_id, service_id):
                edc_cost = self.compute_cost(ap_id, edc_id, service_id)
                if edc_cost < best_cost:
                    best_edc, best_cost = edc_id, edc_cost
        return best_edc

    @abstractmethod
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        pass


class ClosestEDCStrategy(SDNMinimumCostStrategy):
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """ Selects the closest EDC to the AP """
        return self.distance(ap_id, edc_id)


class EmptiestEDCStrategy(SDNMinimumCostStrategy):
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """ Selects the EDC with the lowest service utilization factor"""
        return self.edc_utilization(edc_id, service_id)


class FullestEDCStrategy(EmptiestEDCStrategy):
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """ Selects the EDC with the greatest service utilization factor"""
        return -super().compute_cost(ap_id, edc_id, service_id)


class EmptiestEDCSliceStrategy(EmptiestEDCStrategy):
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """ Selects the EDC with the lowest service slice utilization factor"""
        edc_slice = self.edc_slicing.get(edc_id, dict()).get(service_id, 100)
        return 100 * super().compute_cost(ap_id, edc_id, service_id) / edc_slice


class FullestEDCSliceStrategy(EmptiestEDCSliceStrategy):
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """ Selects the EDC with the greatest service slice utilization factor"""
        return -super().compute_cost(ap_id, edc_id, service_id)


class PowerBalanceConsumptionStrategy(SDNMinimumCostStrategy):
    @property
    def max_cost(self):
        return inf, inf

    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """
        Selects the EDC with the lowest power consumption to balance the power consumption among all the EDCs.
        NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
              this EDC will be selected.
        """
        edc_report = self.edc_reports[edc_id]
        # We must return the negative value of power consumption
        negative_cost, positive_cost = self.max_cost
        if edc_report is not None:
            negative_cost = min(edc_report.power_consumption, 0)
            positive_cost = max(edc_report.power_consumption, 0)
        return negative_cost, positive_cost


class HighestPowerConsumptionStrategy(PowerBalanceConsumptionStrategy):
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """
        Selects the EDC with the greatest power consumption.
        NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
              this EDC will be selected.
        """
        negative_cost, positive_cost = super().compute_cost(ap_id, edc_id, service_id)
        return negative_cost, -positive_cost


class BestElectricityOfferStrategy(PowerBalanceConsumptionStrategy):
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """
        Selects the EDC whose electricity provider offers the lowest cost.
        NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
              this EDC will be selected.
        """
        negative_cost, _ = super().compute_cost(ap_id, edc_id, service_id)
        return negative_cost, self.electricity_cost(edc_id)


class SmartGridClosestEDCStrategy(PowerBalanceConsumptionStrategy):
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """
        Selects the closest EDC to the AP.
        NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
              this EDC will be selected.
        """
        negative_cost, _ = super().compute_cost(ap_id, edc_id, service_id)
        return negative_cost, self.distance(ap_id, edc_id)


class SmartGridEmptiestEDCStrategy(PowerBalanceConsumptionStrategy):
    """
    Selects the EDC with the lowest service utilization factor
    NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
          this EDC will be selected.
    """
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        negative_cost, _ = super().compute_cost(ap_id, edc_id, service_id)
        return negative_cost, self.edc_utilization(edc_id, service_id)


class SmartGridFullestEDCStrategy(SmartGridEmptiestEDCStrategy):
    """
    Selects the EDC with the greatest service utilization factor
    NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
          this EDC will be selected.
    """
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        negative_cost, utilization_cost = super().compute_cost(ap_id, edc_id, service_id)
        return negative_cost, - utilization_cost


class SmartGridEmptiestEDCSliceStrategy(SmartGridEmptiestEDCStrategy):
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """
        Selects the EDC with the lowest service slice utilization factor
        NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
          this EDC will be selected.
        """
        negative_cost, utilization_cost = super().compute_cost(ap_id, edc_id, service_id)
        edc_slice = self.edc_slicing.get(edc_id, dict()).get(service_id, 100)
        return negative_cost, 100 * utilization_cost / edc_slice


class SmartGridFullestEDCSliceStrategy(SmartGridEmptiestEDCSliceStrategy):
    def compute_cost(self, ap_id: str, edc_id: str, service_id: str):
        """
        Selects the EDC with the greatest service slice utilization factor
        NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
          this EDC will be selected.
        """
        negative_cost, slice_cost = super().compute_cost(ap_id, edc_id, service_id)
        return negative_cost, - slice_cost
