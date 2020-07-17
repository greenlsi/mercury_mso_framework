from typing import Dict
from xdevs.models import Coupled, Port
from .rack import Rack
from .rack_mux import RackMultiplexer
from .r_manager import ResourceManager
from .edc_interface import EdgeDataCenterInterface
from ...common.packet.apps.service import ServiceConfiguration
from ...common.packet.apps.federation_management import FederationManagementConfiguration
from ...common.packet.packet import NetworkPacketConfiguration, PhysicalPacket, NetworkPacket
from ...common.edge_fed.edge_fed import EdgeDataCenterConfiguration, EdgeDataCenterReport


class EdgeDataCenter(Coupled):

    def __init__(self, name: str, edc_config: EdgeDataCenterConfiguration,
                 services_config: Dict[str, ServiceConfiguration], fed_mgmt_config: FederationManagementConfiguration,
                 network_config: NetworkPacketConfiguration, sdn_controller_id: str, lite=False):
        """
        Edge Data Center xDEVS module
        :param str name: xDEVS module name
        :param EdgeDataCenterConfiguration edc_config: Edge Data Center Configuration
        :param dict services_config: dictionary with all the services_config configurations
        :param FederationManagementConfiguration fed_mgmt_config: Federation Management Application configuration
        :param NetworkPacketConfiguration network_config: network layer packets configuration
        :param str sdn_controller_id: Federation Controller ID
        """
        super().__init__(name)
        # Unwrap EDC configuration values
        self.edc_id = edc_config.edc_id
        edc_location = edc_config.edc_location
        racks_config_list = edc_config.racks_configuration_list
        r_manager_config = edc_config.r_manager_config
        env_temp = edc_config.env_temp

        # Create and add submodules
        racks = [Rack(name + '_' + rack_id, racks_config_list[rack_id], services_config, env_temp)
                 for rack_id in racks_config_list]
        rack_mux = RackMultiplexer(name + '_rack_mux', list(racks_config_list.keys()))
        r_manager = ResourceManager(name + '_r_manager', self.edc_id, edc_location, r_manager_config, services_config,
                                    env_temp)
        edc_interface = EdgeDataCenterInterface(name + '_edc_interface', self.edc_id, fed_mgmt_config, network_config,
                                                sdn_controller_id, lite)
        [self.add_component(rack) for rack in racks]
        self.add_component(rack_mux)
        self.add_component(r_manager)
        self.add_component(edc_interface)

        # Define input/output_ports
        port_type = NetworkPacket if lite else PhysicalPacket
        self.input_crosshaul = Port(port_type, name + '_input_crosshaul')
        self.output_crosshaul = Port(port_type, name + '_output_crosshaul')
        self.output_edc_report = Port(EdgeDataCenterReport, name + '_output_edc_report')
        self.add_in_port(self.input_crosshaul)
        self.add_out_port(self.output_crosshaul)
        self.add_out_port(self.output_edc_report)

        self._interface_r_manager_internal_couplings_spec(edc_interface, r_manager)
        # External couplings for resource manager
        self._r_manager_external_couplings(r_manager)

        # External couplings for EDC interface
        self._interface_external_couplings(edc_interface)
        # Internal couplings for interface and resource manager
        self._interface_r_manager_internal_couplings_std(edc_interface, r_manager)
        # Internal couplings for resource manager and processing units multiplexer
        self._r_manager_rack_mux_internal_couplings(r_manager, rack_mux)
        for rack in racks:
            # Internal couplings for processing units multiplexer and processing units
            self._p_units_mux_i_rack_internal_couplings(rack_mux, rack)
            # Internal couplings for resource manager and processing units
            self._resource_manager_rack_internal_couplings(r_manager, rack)

    def _interface_external_couplings(self, edc_interface: EdgeDataCenterInterface):
        self.add_coupling(self.input_crosshaul, edc_interface.input_crosshaul)
        self.add_coupling(edc_interface.output_crosshaul, self.output_crosshaul)

    def _r_manager_external_couplings(self, r_manager: ResourceManager):
        self.add_coupling(r_manager.output_edc_report, self.output_edc_report)

    def _interface_r_manager_internal_couplings_std(self, edc_interface: EdgeDataCenterInterface,
                                                    r_manager: ResourceManager):
        self.add_coupling(edc_interface.output_create_session_request, r_manager.input_create_session)
        self.add_coupling(edc_interface.output_remove_session_request, r_manager.input_remove_session)
        self.add_coupling(edc_interface.output_ongoing_session_request, r_manager.input_ongoing_session_request)
        self.add_coupling(r_manager.output_create_session_response, edc_interface.input_create_session_response)
        self.add_coupling(r_manager.output_remove_session_response, edc_interface.input_remove_session_response)
        self.add_coupling(r_manager.output_ongoing_session_response, edc_interface.input_ongoing_session_response)

    def _interface_r_manager_internal_couplings_spec(self, edc_interface: EdgeDataCenterInterface,
                                                     r_manager: ResourceManager):
        self.add_coupling(r_manager.output_edc_report, edc_interface.input_edc_report)

    def _r_manager_rack_mux_internal_couplings(self, r_manager: ResourceManager, rack_mux: RackMultiplexer):
        self.add_coupling(r_manager.output_change_status, rack_mux.input_change_status)
        self.add_coupling(r_manager.output_set_dvfs_mode, rack_mux.input_set_dvfs_mode)
        self.add_coupling(r_manager.output_open_session, rack_mux.input_open_session)
        self.add_coupling(r_manager.output_ongoing_session, rack_mux.input_ongoing_session)
        self.add_coupling(r_manager.output_close_session, rack_mux.input_close_session)

    def _p_units_mux_i_rack_internal_couplings(self, rack_mux: RackMultiplexer, rack: Rack):
        rack_id = rack.rack_id
        self.add_coupling(rack_mux.outputs_change_status[rack_id], rack.input_change_status)
        self.add_coupling(rack_mux.outputs_set_dvfs_mode[rack_id], rack.input_set_dvfs_mode)
        self.add_coupling(rack_mux.outputs_open_session[rack_id], rack.input_open_session)
        self.add_coupling(rack_mux.outputs_ongoing_session[rack_id], rack.input_ongoing_session)
        self.add_coupling(rack_mux.outputs_close_session[rack_id], rack.input_close_session)

    def _resource_manager_rack_internal_couplings(self, r_manager: ResourceManager, rack: Rack):
        self.add_coupling(rack.output_change_status_response, r_manager.input_change_status_response)
        self.add_coupling(rack.output_set_dvfs_mode_response, r_manager.input_set_dvfs_mode_response)
        self.add_coupling(rack.output_open_session_response, r_manager.input_open_session_response)
        self.add_coupling(rack.output_ongoing_session_response, r_manager.input_ongoing_session_response)
        self.add_coupling(rack.output_close_session_response, r_manager.input_close_session_response)
        self.add_coupling(rack.output_rack_report, r_manager.input_racks_report)
