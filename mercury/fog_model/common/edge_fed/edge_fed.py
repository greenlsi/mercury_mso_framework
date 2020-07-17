from typing import Tuple, Dict
from .r_manager import ResourceManagerConfiguration
from .rack import RackConfiguration, RackReport
from ...network import NodeConfiguration, TransceiverConfiguration


class EdgeDataCenterConfiguration:
    def __init__(self, edc_id: str, edc_location: Tuple[float, ...],
                 edc_trx: TransceiverConfiguration, r_manager_config: ResourceManagerConfiguration,
                 racks_configuration: Dict[str, RackConfiguration], env_temp: float = 298):
        """
        Edge Data Center Configuration
        :param edc_id: ID of the Edge Data Center
        :param edc_location: Location of the EDC (coordinates in meters)
        :param edc_trx: Crosshaul transceiver configuration
        :param r_manager_config: Resource Manager Configuration
        :param racks_configuration: Configuration of racks that compose the EDC
        :param env_temp: Edge Data Center base temperature (in Kelvin)
        """
        self.edc_id = edc_id
        self.edc_location = edc_location
        self.r_manager_config = r_manager_config
        self.racks_configuration_list = racks_configuration
        self.env_temp = env_temp
        self.crosshaul_node = NodeConfiguration(self.edc_id, edc_trx, initial_position=edc_location)


class EdgeDataCenterReport:
    """
    Status of an Edge Data Center.
    :param edc_id: ID of the Edge Data Center
    :param edc_location: Location of the Edge Data Center
    :param overall_std_u: Overall utilized standard std_u factor
    :param max_std_u: Maximum available standard std_u factor
    :param power_demand: Overall power consumption by IT and
    :param env_temp: Environment temperature of the EDC
    :param rack_reports: list of reports of all the racks within the EDC
    """
    def __init__(self, edc_id: str, edc_location: Tuple[float, ...], overall_std_u: float, max_std_u: float,
                 power_demand: float, env_temp: float, rack_reports: Dict[str, RackReport]):
        self.edc_id = edc_id
        self.edc_location = edc_location
        self.overall_std_u = overall_std_u
        self.max_std_u = max_std_u
        self.power_demand = power_demand
        self.cooling_power = 0
        self.it_power = 0
        self.env_temp = env_temp
        self.rack_reports = rack_reports
        self.std_u_per_service = dict()
        for rack_id, rack_report in rack_reports.items():
            self.cooling_power += rack_report.cooling_power
            for service_id, std_u in rack_report.u_per_service.items():
                if service_id not in self.std_u_per_service:
                    self.std_u_per_service[service_id] = 0
                self.std_u_per_service[service_id] += std_u
        self.it_power = self.power_demand - self.cooling_power
        self.pue = 0
        if self.it_power > 0:
            self.pue = power_demand / self.it_power
