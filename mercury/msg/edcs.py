from __future__ import annotations
from abc import ABC
from typing import Any
from .profile import EDCProfile, WindowReport
from .smart_grid import EnergyDemand


class ProcessingUnitReport:
    def __init__(self, edc_id: str, pu_id: str, pu_type_id: str, status: bool, service_id: str | None,
                 n_sessions: int | None, max_sessions: int | None, queue_time: float, power: float, temperature: float):
        """
        Processing Unit report message.
        :param edc_id: ID of the EDC that contains the PU.
        :param pu_id: ID of the PU.
        :param pu_type_id: ID of the PU model type.
        :param status: status of the Processing Unit (true if switched on).
        :param service_id: ID of the service reserved by the PU. If None, the PU accepts requests from any service.
        :param n_sessions: number of opened sessions of the reserved service. If service_id is None, n_sessions is None.
        :param max_sessions: maximum number of sessions allowed If service_id is None, max_sessions is None.
        :param queue_time: approximate delay overhead
        :param power: power consumption of PU (in Watts)
        :param temperature: temperature of PU (in Kelvin)
        """
        self.edc_id: str = edc_id
        self.pu_id: str = pu_id
        self.pu_type_id: str = pu_type_id
        self.status: bool = status
        self.service_id: str | None = service_id
        self.n_sessions: int | None = n_sessions
        self.max_sessions: int | None = max_sessions
        self.queue_time: float = queue_time
        self.power: float = power
        self.temperature: float = temperature

    @property
    def utilization(self) -> float | None:
        return None if self.service_id is None else self.n_sessions / self.max_sessions


class CoolerReport:
    def __init__(self, edc_id: str, cooler_type_id: str, temp: float, it_power: float, cooling_power: float):
        """
        :param edc_id: ID of the EDC that contains the cooler.
        :param cooler_type_id: ID of the cooler type.
        :param temp: EDC temperature (in Kelvin).
        :param it_power: Power consumption (in Watts) of all the PUs of the EDC.
        :param cooling_power: power (in Watts) required by the EDC for refrigerating the PUs.
        """
        self.edc_id: str = edc_id
        self.cooler_type_id: str = cooler_type_id
        self.temp: float = temp
        self.it_power: float = it_power
        self.cooling_power: float = cooling_power

    @property
    def total_power(self) -> float:
        return self.it_power + self.cooling_power


class SrvSlicingReport:
    def __init__(self, expected_size: int, slice_size: int, slize_available: int, free_size: int, free_available: int):
        """
        Service slicing report.
        :param expected_size: expected number of tasks by the edge data center.
        :param slice_size: number of tasks that the edge data center can actually handle. It depends on sliced PUs.
        :param slize_available: number of additional tasks that can be admitted by sliced PUs.
        :param free_size: number of tasks that can be processed using PUs that do not belong to any slice.
        :param free_available: number of tasks currently that can be admitted by unassigned PUs.
        """
        self.expected_size: int = expected_size
        self.slice_size: int = slice_size
        self.slize_available: int = slize_available
        self.free_size: int = free_size
        self.free_available: int = free_available

    @property
    def congested(self) -> bool:  # TODO rename?   me dice si una slice es más pequeña de lo que debería
        return self.slice_size < self.expected_size

    @property
    def slice_u(self) -> float:
        # TODO utilización de los recursos de la slice. Si una PU tiene tareas "incompatibles" cuenta como llena
        return self.utilization(self.slice_size, self.slize_available)

    @property
    def free_u(self) -> float:
        # TODO utilización de los recursos libres. Si una PU tiene tareas "incompatibles", cuenta como llena
        return self.utilization(self.free_size, self.free_available)

    @property
    def total_u(self) -> float | None:
        # TODO utilización de todos los recursos. Si una PU tiene tareas "incompatibles", cuenta como llena
        return self.utilization(self.slice_size + self.free_size, self.slize_available + self.free_available)

    @staticmethod
    def utilization(r_size: int, r_available: int) -> float:
        return 1 if r_size < 1 else 1 - r_available / r_size  # TODO


class EDCProfileReport:
    def __init__(self, edc_id: str, srv_id: str, n_clients: int, req_type: str, result: str, window: WindowReport):
        self.edc_id: str = edc_id
        self.srv_id: str = srv_id
        self.n_clients: int = n_clients
        self.req_type: str = req_type
        self.result: str = result
        self.window: WindowReport = window

    def __ne__(self, other):
        return self.n_clients != self.n_clients or self.window != other.window


class EdgeDataCenterReport(EnergyDemand):
    def __init__(self, edc_id: str, slicing: dict[str, SrvSlicingReport], it_power: float, cooling_power: float):
        """
        Edge data center report message.
        :param edc_id: ID of the EDC.
        :param slicing: report of the resources allocated to the EDC for each service
        :param it_power: IT power consumption (in Watts).
        :param cooling_power: Cooling power consumption (in Watts).
        """
        super().__init__()
        self.edc_id: str = edc_id
        self.slicing: dict[str, SrvSlicingReport] = slicing
        self.it_power: float = it_power
        self.cooling_power: float = cooling_power
        self.edc_profile: EDCProfile | None = None

    @property
    def consumer_id(self) -> str:
        return self.edc_id

    @property
    def power_demand(self) -> float:
        return self.it_power + self.cooling_power

    @property
    def pue(self) -> float:
        return self.power_demand / self.it_power if self.it_power > 0 else 0

    @property
    def congested(self) -> bool:  # TODO rename?
        return any(srv_slice.congested for srv_slice in self.slicing.values())

    def srv_congested(self, service_id: str) -> bool:  # TODO rename?
        return service_id in self.slicing and self.slicing[service_id].congested

    def srv_expected_size(self, service_id: str) -> int:
        return self.slicing[service_id].expected_size if service_id in self.slicing else 0

    def srv_slice_size(self, service_id: str) -> int:
        return self.slicing[service_id].slice_size if service_id in self.slicing else 0

    def srv_slice_available(self, service_id: str) -> int:
        return self.slicing[service_id].slize_available if service_id in self.slicing else 0

    def srv_slice_u(self, service_id: str) -> float:
        return self.slicing[service_id].slice_u if service_id in self.slicing else 1

    def srv_free_size(self, service_id: str) -> int:
        return self.slicing[service_id].free_size if service_id in self.slicing else 0

    def srv_free_available(self, service_id: str) -> int:
        return self.slicing[service_id].free_available if service_id in self.slicing else 0

    def srv_free_u(self, service_id: str) -> float:
        return self.slicing[service_id].free_u if service_id in self.slicing else 1

    def srv_total_u(self, service_id: str) -> float:
        return self.slicing[service_id].total_u if service_id in self.slicing else 1


class SrvDemandEstimationReport:
    def __init__(self, edc_id: str, edc_report: EdgeDataCenterReport | None, demand_estimation: dict[str, int]):
        """
        Service demand estimation message.
        :param edc_id: Edge Data Center ID.
        :param edc_report: Edge Data Center report.
        :param demand_estimation: number of clients that are expected to send requests within a given time window.
        """
        self.edc_id: str = edc_id
        self.edc_report: EdgeDataCenterReport | None = edc_report
        self.demand_estimation: dict[str, int] = demand_estimation


class NewEDCConfig(ABC):
    def __init__(self, edc_id: str):
        self.edc_id: str = edc_id


class NewEDCMapping(NewEDCConfig):
    def __init__(self, edc_id: str, mapping_id: str, mapping_config: dict[str, Any] | None = None):
        super().__init__(edc_id)
        self.mapping_id: str = mapping_id
        self.mapping_config: dict[str, Any] = dict() if mapping_config is None else mapping_config


class NewEDCSlicing(NewEDCConfig):
    def __init__(self, edc_id: str, slicing: dict[str, int]):
        super().__init__(edc_id)
        self.slicing: dict[str, int] = slicing
