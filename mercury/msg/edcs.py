from abc import ABC
from typing import Any, Dict, Optional, Set, Tuple
from .network.packet.app_layer.service import ServiceRequest, ServiceResponse


class ProcessingUnitMessage:
    def __init__(self, edc_id: str, pu_id: str):
        self.edc_id: str = edc_id
        self.pu_id: str = pu_id


class ProcessingUnitHotStandBy(ProcessingUnitMessage):
    def __init__(self, edc_id: str, pu_id: str, hot_standby: bool, instantaneous: bool = False):
        super().__init__(edc_id, pu_id)
        self.hot_standby: bool = hot_standby
        self.instantaneous: bool = instantaneous


class ProcessingUnitServiceRequest(ProcessingUnitMessage):
    def __init__(self, edc_id: str, pu_id: str, request: ServiceRequest):
        super().__init__(edc_id, pu_id)
        self.request: ServiceRequest = request


class ProcessingUnitServiceResponse(ProcessingUnitMessage):
    def __init__(self, edc_id: str, pu_id: str, response: ServiceResponse):
        super().__init__(edc_id, pu_id)
        self.response: ServiceResponse = response


class ProcessingUnitReport(ProcessingUnitMessage):
    def __init__(self, edc_id: str, pu_id: str, pu_type: str,
                 status: bool, dvfs_u: float, utilization: float, reserved_u: float, power: float, temp: float,
                 starting: Dict[str, Set[str]], started: Dict[str, Set[str]], stopping: Dict[str, Set[str]],
                 request_share: Dict[str, Dict[ServiceRequest, Tuple[float, float]]]):
        """
        Processing Unit report message.
        :param edc_id; ID of the EDC that contains the PU.
        :param pu_id: ID of the PU.
        :param pu_type: ID of the PU model type.
        :param status: Status of the Processing Unit (true if switched on).
        :param dvfs_u: Maximum utilization of PU (in %) allowed by the current DVFS configuration.
        :param utilization: current utilization of resources in PU (in %).
        :param reserved_u: utilization of resources in PU (in %) reserved for service sessions.
        :param power: power consumption of PU (in Watts)
        :param temp: temperature of PU (in Kelvin)
        :param starting: dictionary {service_id: {client_id, ...}} of starting sessions in PU.
        :param started: dictionary {service_id: {client_id, ...}} of started sessions in PU.
        :param stopping: dictionary {service_id: {client_id, ...}} of stopping sessions in PU.
        :param request_share: nested dictionary {service_id: {request: (utilization, progress)}} of requests in the PU.
        """
        super().__init__(edc_id, pu_id)
        self.pu_type: str = pu_type
        self.status: bool = status
        self.dvfs_u: float = dvfs_u
        self.utilization: float = utilization
        self.reserved_u: float = reserved_u
        self.power: float = power
        self.temp: float = temp
        self.starting: Dict[str, Set[str]] = starting
        self.started: Dict[str, Set[str]] = started
        self.stopping: Dict[str, Set[str]] = stopping
        self.request_share: Dict[str, Dict[ServiceRequest, Tuple[float, float]]] = request_share


class CoolerReport:
    def __init__(self, edc_id: str, cooler_type: str, temp: float, it_power: float, cooling_power: float):
        """
        :param edc_id: ID of the EDC that contains the cooler.
        :param cooler_type: ID of the cooler type.
        :param temp: EDC temperature (in Kelvin).
        :param it_power: Power consumption (in Watts) of all the PUs of the EDC.
        :param cooling_power: power (in Watts) required by the EDC for refrigerating the PUs.
        """
        self.edc_id: str = edc_id
        self.cooler_type: str = cooler_type
        self.temp: float = temp
        self.it_power: float = it_power
        self.cooling_power: float = cooling_power

    @property
    def total_power(self) -> float:
        return self.it_power + self.cooling_power


class EdgeDataCenterReport:  # TODO think of something for max_sessions with overlapping resources
    def __init__(self, edc_id: str, edc_location: Tuple[float, ...], utilization: float, max_sessions: Dict[str, int],
                 it_power: float, cooling_power: float, temp: float, ongoing_sessions: Dict[str, Set[str]],
                 tasks_progress: Dict[str, Dict[ServiceRequest, float]]):
        """
        Status of an Edge Data Center.
        :param edc_id: ID of the EDC.
        :param edc_location: ID of the EDC.
        :param utilization: mean utilization factor (in %) of all the PUs in the EDC.
        :param max_sessions: Maximum number of sessions that can be hosted in EDC: {service_id: N}
        :param it_power: IT power consumption (in Watts).
        :param cooling_power: Cooling power consumption (in Watts).
        :param temp: Temperature of the EDC (in Kelvin).
        :param ongoing_sessions: dictionary {service_id: {client_id, ...}} of ongoing sessions in EDC.
        :param tasks_progress: nested dictionary {service_id: {request: progress}} of tasks in the EDC.
        """
        self.edc_id: str = edc_id
        self.edc_location: Tuple[float, ...] = edc_location
        self.utilization: float = utilization
        self.max_sessions: Dict[str, int] = max_sessions
        self.it_power: float = it_power
        self.cooling_power: float = cooling_power
        self.temp: float = temp
        self.ongoing_sessions: Dict[str, Set[str]] = ongoing_sessions
        self.tasks_progress: Dict[str, Dict[ServiceRequest, float]] = tasks_progress

    @property
    def power_demand(self) -> float:
        return self.it_power + self.cooling_power

    @property
    def pue(self) -> float:
        return self.power_demand / self.it_power if self.it_power > 0 else 0

    def n_service_tasks(self, service_id: str) -> int:
        return len(self.tasks_progress.get(service_id, dict()))

    def n_tasks(self) -> int:
        return sum(self.n_service_tasks(service_id) for service_id in self.tasks_progress)

    def n_service_sessions(self, service_id: str) -> int:
        return len(self.ongoing_sessions.get(service_id, set()))

    def n_sessions(self) -> int:
        return sum(self.n_service_sessions(service_id) for service_id in self.tasks_progress)

    def service_utilization(self, service_id: str) -> float:  # TODO careful with overlapping resources!
        max_sessions = self.max_sessions.get(service_id, 0)
        return 100 if max_sessions <= 0 else 100 * self.n_service_sessions(service_id) / max_sessions


class EdgeDataCenterFunction(ABC):
    def __init__(self, edc_id: str, function_id: Optional[str], function_config: Optional[Dict[str, Any]] = None):
        self.edc_id: str = edc_id
        self.function_id: Optional[str] = function_id
        self.function_config: Dict[str, Any] = {} if function_config is None else function_config


class DispatchingFunction(EdgeDataCenterFunction):
    def __init__(self, edc_id: str, function_id: str, function_config: Optional[Dict[str, Any]] = None):
        super().__init__(edc_id, function_id, function_config)


class HotStandbyFunction(EdgeDataCenterFunction):
    pass
