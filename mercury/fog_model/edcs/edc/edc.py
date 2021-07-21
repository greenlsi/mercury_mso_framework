from typing import Set
from xdevs.models import Coupled, Port
from mercury.config.edcs import EdgeDataCenterConfig
from mercury.msg.edcs import EdgeDataCenterReport
from mercury.msg.network import PhysicalPacket, NetworkPacket
from mercury.msg.smart_grid import PowerConsumptionReport, PowerDemandReport
from .pu import ProcessingUnit
from .r_manager import ResourceManager
from .edc_interface import EdgeDataCenterInterface


class EdgeDataCenter(Coupled):
    def __init__(self, edc_config: EdgeDataCenterConfig, services: Set[str], smart_grid: bool, lite: bool = False):
        """
        Edge Data Center xDEVS module

        :param edc_config: Edge Data Center Configuration
        :param services: set with all the service IDs of the scenario
        :param smart_grid: it indicates if the smart grid layer is activated or not
        :param lite: it indicates if the Lite model is activated or not
        """
        self.edc_id: str = edc_config.edc_id
        super().__init__('edge_fed_{}'.format(self.edc_id))
        # Unwrap EDC configuration values
        env_temp: float = edc_config.env_temp

        # Create and add submodules
        r_manager = ResourceManager(edc_config, services, smart_grid)
        edc_interface = EdgeDataCenterInterface(self.edc_id, lite)
        pus = [ProcessingUnit(self.edc_id, pu, config, env_temp) for pu, config in edc_config.pus_config.items()]

        self.add_component(r_manager)
        self.add_component(edc_interface)
        for pu in pus:
            self.add_component(pu)

        # Define input/output_ports
        port_type = NetworkPacket if lite else PhysicalPacket
        self.input_data = Port(port_type, 'input_data')
        self.output_data = Port(port_type, 'output_data')
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_data)

        # Smart grid stuff
        self.input_pwr_consumption = Port(PowerConsumptionReport, 'input_pwr_consumption')
        self.output_pwr_demand = Port(PowerDemandReport, 'output_pwr_demand')
        self.add_in_port(self.input_pwr_consumption)
        self.add_out_port(self.output_pwr_demand)

        self.output_edc_report = Port(EdgeDataCenterReport, 'output_edc_report')
        self.add_out_port(self.output_edc_report)

        # External couplings for EDC interface
        self._interface_external_couplings(edc_interface, smart_grid)
        # External couplings for interface and resource manager
        if smart_grid:
            self._r_manager_external_couplings(r_manager)
        # Internal couplings for interface and resource manager
        self._interface_r_manager_internal_couplings(edc_interface, r_manager, smart_grid)
        for pu in pus:
            # Internal couplings for resource manager and processing units
            self._resource_manager_pu_internal_couplings(r_manager, pu)

    def _interface_external_couplings(self, interface: EdgeDataCenterInterface, smart_grid: bool):
        self.add_coupling(self.input_data, interface.input_data)
        self.add_coupling(interface.output_data, self.output_data)
        self.add_coupling(interface.output_edc_report, self.output_edc_report)
        if smart_grid:
            self.add_coupling(self.input_pwr_consumption, interface.input_edc_consumption)

    def _r_manager_external_couplings(self, r_manager: ResourceManager):
        self.add_coupling(r_manager.output_power_demand, self.output_pwr_demand)

    def _interface_r_manager_internal_couplings(self, interface: EdgeDataCenterInterface,
                                                r_manager: ResourceManager, smart_grid: bool):
        self.add_coupling(interface.output_start_session_request, r_manager.input_start_session_request)
        self.add_coupling(interface.output_service_request, r_manager.input_service_request)
        self.add_coupling(interface.output_stop_session_request, r_manager.input_stop_session_request)
        self.add_coupling(interface.output_new_dispatching, r_manager.input_new_dispatching)
        self.add_coupling(interface.output_new_hot_standby, r_manager.input_new_hot_standby)
        self.add_coupling(r_manager.output_service_response, interface.input_service_response)
        if not smart_grid:
            self.add_coupling(r_manager.output_power_consumption, interface.input_edc_consumption)

    def _resource_manager_pu_internal_couplings(self, r_manager: ResourceManager, pu: ProcessingUnit):
        self.add_coupling(r_manager.outputs_hot_standby[pu.pu_id], pu.input_hot_standby)
        self.add_coupling(r_manager.outputs_start_session_request[pu.pu_id], pu.input_start_session_request)
        self.add_coupling(r_manager.outputs_service_request[pu.pu_id], pu.input_service_request)
        self.add_coupling(r_manager.outputs_stop_session_request[pu.pu_id], pu.input_stop_session_request)
        self.add_coupling(pu.output_start_session_response, r_manager.input_start_session_response)
        self.add_coupling(pu.output_service_response, r_manager.input_service_response)
        self.add_coupling(pu.output_stop_session_response, r_manager.input_stop_session_response)
        self.add_coupling(pu.output_pu_report, r_manager.input_pu_report)
