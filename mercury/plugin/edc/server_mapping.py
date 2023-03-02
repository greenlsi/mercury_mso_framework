from __future__ import annotations
from abc import ABC, abstractmethod
from functools import lru_cache
from mercury.config.edcs import EdgeFederationConfig, EdgeDataCenterConfig
from mercury.config.gateway import GatewaysConfig
from mercury.msg.edcs import EdgeDataCenterReport
from mercury.msg.packet.app_packet.srv_packet import SrvRelatedRequest
from mercury.utils.amf import AccessManagementFunction
from mercury.utils.maths import euclidean_distance
from typing import Generic, Tuple, TypeVar


T = TypeVar('T')


class ServerMappingStrategy(ABC, Generic[T]):
    def __init__(self, **kwargs):
        """
        Software-Defined Network allocation strategy class.
        :param GatewaysConfig gws_config: Dictionary {AP ID: AP location}.
        :param EdgeFederationConfig edge_fed_config: Dictionary {EDC ID: EDC location}.
        :param kwargs: Any additional configuration parameter.
        """
        self.edc_id: str = kwargs['edc_id']
        self.amf: AccessManagementFunction = kwargs['amf']
        self.gws_config: GatewaysConfig = kwargs['gws_config']
        self.edge_fed_config: EdgeFederationConfig = kwargs['edge_fed_config']
        self.edc_reports: dict[str, EdgeDataCenterReport | None] = {edc: None for edc in self.edge_fed_config.edcs_config}

    @property
    def congestion(self) -> float:
        return self.edge_fed_config.congestion

    @property
    def parent_server(self) -> str | None:
        return self.edge_fed_config.cloud_id

    @property
    def edcs_config(self) -> dict[str, EdgeDataCenterConfig]:
        return self.edge_fed_config.edcs_config

    @property
    def edc_config(self) -> EdgeDataCenterConfig:
        return self.edcs_config[self.edc_id]

    @property
    def edc_report(self) -> EdgeDataCenterReport | None:
        return self.edc_reports[self.edc_id]

    def update_edc_report(self, edc_report: EdgeDataCenterReport):
        self.edc_reports[edc_report.edc_id] = edc_report

    def edc_available(self, edc_id: str, service_id: str) -> bool:
        if self.edc_reports[edc_id] is None:
            return False
        return self.slice_u(edc_id, service_id) < self.congestion or self.free_u(edc_id, service_id) < self.congestion

    def slice_u(self, edc_id: str, service_id: str) -> float:
        return self.edc_reports[edc_id].srv_slice_u(service_id)

    def free_u(self, edc_id: str, service_id: str) -> float:
        return self.edc_reports[edc_id].srv_free_u(service_id)

    def negative_consumption(self, edc_id: str) -> float:
        return min(self.edc_reports[edc_id].consumption.power_consumption, 0)

    def positive_consumption(self, edc_id: str) -> float:
        return max(self.edc_reports[edc_id].consumption.power_consumption, 0)

    @lru_cache(maxsize=None)
    def distance(self, gw_id: str, edc_id: str) -> float:
        """
        Computes the distance between a gateway and an EDC. This function is cached to speed up the performance.
        :param gw_id: Gateway ID
        :param edc_id: EDC ID
        :return: distance between gateway and EDC
        """
        gw_location = self.gws_config.gateways[gw_id].location
        edc_location = self.edge_fed_config.edcs_config[edc_id].location
        return euclidean_distance(gw_location, edc_location)

    def map_server(self, srv_request: SrvRelatedRequest) -> str | None:
        """
        From a list of available Edge Data Centers, the optimal is chosen for a given Access Point.
        :param srv_request: Service-related request.
        :return Best Edge Data Center ID for the service.
        """
        best_edc, best_cost = None, None
        for edc_id in self.edc_reports:
            if self.edc_available(edc_id, srv_request.service_id):
                edc_cost = self.cost(edc_id, srv_request)
                if best_edc is None or edc_cost < best_cost:
                    best_edc, best_cost = edc_id, edc_cost
        return best_edc

    @abstractmethod
    def cost(self, edc_id: str, srv_request: SrvRelatedRequest) -> T:
        pass


class ClosestEDCStrategy(ServerMappingStrategy[float]):
    def cost(self, edc_id: str, srv_request: SrvRelatedRequest) -> float:
        """ Selects the closest EDC to the AP """
        return self.distance(self.amf.get_client_gateway(srv_request.client_id), edc_id)


class EmptiestEDCStrategy(ServerMappingStrategy[Tuple[float, float]]):
    def cost(self, edc_id: str, srv_request: SrvRelatedRequest) -> tuple[float, float]:
        """ Selects the EDC with the lowest service utilization factor"""
        return self.slice_u(edc_id, srv_request.service_id), self.free_u(edc_id, srv_request.service_id)


class FullestEDCStrategy(EmptiestEDCStrategy):
    def cost(self, edc_id: str, srv_request: SrvRelatedRequest) -> tuple[float, float]:
        """ Selects the EDC with the greatest service utilization factor"""
        slice_u, free_u = super().cost(edc_id, srv_request)
        return -slice_u, -free_u


class PowerBalanceStrategy(ServerMappingStrategy[Tuple[float, float]]):
    def cost(self, edc_id: str, srv_request: SrvRelatedRequest) -> tuple[float, float]:
        """
        Selects the EDC with the lowest power consumption to balance the power consumption among all the EDCs.
        NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
              this EDC will be selected.
        """
        return self.negative_consumption(edc_id), self.positive_consumption(edc_id)


class HighestPowerStrategy(PowerBalanceStrategy):
    def cost(self, edc_id: str, srv_request: SrvRelatedRequest) -> tuple[float, float]:
        """
        Selects the EDC with the greatest power consumption.
        NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
              this EDC will be selected.
        """
        negative_consumption, positive_consumption = super().cost(edc_id, srv_request)
        return negative_consumption, -positive_consumption


class SmartGridClosestEDCStrategy(ServerMappingStrategy[Tuple[float, float]]):
    def cost(self, edc_id: str, srv_request: SrvRelatedRequest) -> tuple[float, float]:
        """
        Selects the closest EDC to the AP.
        NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
              this EDC will be selected.
        """
        gw_id = self.amf.get_client_gateway(srv_request.client_id)
        return self.negative_consumption(edc_id), self.distance(gw_id, edc_id)


class SmartGridEmptiestEDCStrategy(ServerMappingStrategy[Tuple[float, float, float]]):
    """
    Selects the EDC with the lowest service utilization factor
    NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
          this EDC will be selected.
    """
    def cost(self, edc_id: str, srv_request: SrvRelatedRequest) -> tuple[float, float, float]:
        service_id = srv_request.service_id
        return self.negative_consumption(edc_id), self.slice_u(edc_id, service_id), self.free_u(edc_id, service_id)


class SmartGridFullestEDCStrategy(SmartGridEmptiestEDCStrategy):
    """
    Selects the EDC with the greatest service utilization factor
    NOTE: If the power consumption of a given EDC is negative (i.e., it is giving energy to the grid),
          this EDC will be selected.
    """
    def cost(self, edc_id: str, srv_request: SrvRelatedRequest) -> tuple[float, float, float]:
        negative_consumption, slice_u, free_u = super().cost(edc_id, srv_request)
        return negative_consumption, -slice_u, -free_u
