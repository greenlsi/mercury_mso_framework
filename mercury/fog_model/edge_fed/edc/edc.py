from xdevs.models import Coupled, Port
from .p_unit import ProcessingUnit
from .p_unit_mux import ProcessingUnitMultiplexer
from .r_manager import ResourceManager
from .edc_interface import EdgeDataCenterInterface
from ...common.packet.application.federation_management import FederationManagementConfiguration
from ...common.packet.network import NetworkPacketConfiguration
from ...common.packet.physical import PhysicalPacket
from ...common.edge_fed import EdgeDataCenterConfiguration, EdgeDataCenterReport
from ...common.crosshaul import CrosshaulConfiguration


class EdgeDataCenter(Coupled):
    """
    Edge Data Center XDEVS module
    :param str name: XDEVS module name
    :param EdgeDataCenterConfiguration edc_config: Edge Data Center Configuration
    :param dict services_config: dictionary with all the services_config configurations
    :param FederationManagementConfiguration fed_mgmt_config: Federation Management Application configuration
    :param NetworkPacketConfiguration network_config: network layer packets configuration
    :param CrosshaulConfiguration crosshaul_config: Crosshaul physical packets configuration
    :param str fed_controller_id: Federation Controller ID
    """
    def __init__(self, name, edc_config, services_config, fed_mgmt_config, network_config, crosshaul_config,
                 fed_controller_id):
        super().__init__(name)

        # Unwrap EDC configuration values
        self.edc_id = edc_config.edc_id
        p_units_configuration_list = edc_config.p_units_configuration_list
        crosshaul_transceiver_config = edc_config.crosshaul_transceiver_config
        resource_manager_config = edc_config.r_manager_config
        base_temp = edc_config.base_temp
        self.n_pu = len(p_units_configuration_list)
        p_units_char = [(p_unit.p_unit_id, p_unit.std_to_spec_u) for p_unit in p_units_configuration_list]

        # Create and add sub-modules
        p_units = [ProcessingUnit(name + '_p_unit_' + str(i), p_units_configuration_list[i], i, base_temp)
                   for i in range(self.n_pu)]
        p_unit_mux = ProcessingUnitMultiplexer(name + '_p_unit_mux', self.n_pu)
        r_manager = ResourceManager(name + '_r_manager', resource_manager_config, p_units_char, base_temp)
        edc_interface = EdgeDataCenterInterface(name + '_edc_interface', self.edc_id, crosshaul_transceiver_config,
                                                services_config, fed_mgmt_config, network_config, crosshaul_config,
                                                fed_controller_id)
        [self.add_component(p_unit) for p_unit in p_units]
        self.add_component(p_unit_mux)
        self.add_component(r_manager)
        self.add_component(edc_interface)

        # Define input/output_ports
        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.output_crosshaul_dl = Port(PhysicalPacket, name + '_output_crosshaul_dl')
        self.output_crosshaul_ul = Port(PhysicalPacket, name + '_output_crosshaul_ul')
        self.output_edc_report = Port(EdgeDataCenterReport, name + '_output_edc_report')
        self.add_in_port(self.input_crosshaul_ul)
        self.add_out_port(self.output_crosshaul_dl)
        self.add_out_port(self.output_crosshaul_ul)
        self.add_out_port(self.output_edc_report)

        # External couplings for EDC interface
        self._interface_external_couplings(edc_interface)
        # Internal couplings for interface and resource manager
        self._interface_resource_manager_internal_couplings(edc_interface, r_manager)
        # Internal couplings for resource manager and processing units multiplexer
        self._r_manager_p_units_mux_internal_couplings(r_manager, p_unit_mux)
        # Internal couplings for processing units multiplexer and processing units
        self._p_units_mux_i_p_units_internal_couplings(p_unit_mux, p_units)
        # Internal couplings for resource manager and processing units
        self._resource_manager_p_units_internal_couplings(r_manager, p_units)

    def _interface_external_couplings(self, edc_interface):
        """
        External couplings for Edge Data Center Interface
        :param EdgeDataCenterInterface edc_interface: Edge Data Center Interface
        """
        self.add_coupling(self.input_crosshaul_ul, edc_interface.input_crosshaul_ul)
        self.add_coupling(edc_interface.output_crosshaul_dl, self.output_crosshaul_dl)
        self.add_coupling(edc_interface.output_crosshaul_ul, self.output_crosshaul_ul)
        self.add_coupling(edc_interface.output_edc_report, self.output_edc_report)

    def _interface_resource_manager_internal_couplings(self, edc_interface, r_manager):
        """
        Internal couplings between Edge Data Center Interface and Resource Manager
        :param EdgeDataCenterInterface edc_interface: Edge Data Center Interface
        :param ResourceManager r_manager: Resource Manager
        """
        self.add_coupling(edc_interface.output_create_session, r_manager.input_create_session)
        self.add_coupling(edc_interface.output_remove_session, r_manager.input_remove_session)
        self.add_coupling(r_manager.output_create_session_response, edc_interface.input_create_session_response)
        self.add_coupling(r_manager.output_remove_session_response, edc_interface.input_remove_session_response)
        self.add_coupling(r_manager.output_overall_report, edc_interface.input_overall_report)

    def _r_manager_p_units_mux_internal_couplings(self, r_manager, p_unit_mux):
        """
        Internal couplings between resource manager and processing unit multiplexer
        :param ResourceManager r_manager: resource manager
        :param ProcessingUnitMultiplexer p_unit_mux: processing unit multiplexer
        """
        self.add_coupling(r_manager.output_change_status, p_unit_mux.input_change_status)
        self.add_coupling(r_manager.output_set_dvfs_mode, p_unit_mux.input_set_dvfs_mode)
        self.add_coupling(r_manager.output_open_session, p_unit_mux.input_open_session)
        self.add_coupling(r_manager.output_close_session, p_unit_mux.input_close_session)

    def _p_units_mux_i_p_units_internal_couplings(self, p_unit_mux, p_units):
        """
        Internal couplings between processing unit multiplexer and processing units
        :param ProcessingUnitMultiplexer p_unit_mux:
        :param list p_units: list of processing units
        """
        for i in range(self.n_pu):
            self.add_coupling(p_unit_mux.outputs_change_status[i], p_units[i].input_change_status)
            self.add_coupling(p_unit_mux.outputs_set_dvfs_mode[i], p_units[i].input_set_dvfs_mode)
            self.add_coupling(p_unit_mux.outputs_open_session[i], p_units[i].input_open_session)
            self.add_coupling(p_unit_mux.outputs_close_session[i], p_units[i].input_close_session)

    def _resource_manager_p_units_internal_couplings(self, r_manager, p_units):
        """
        Internal couplings between Resource Manager and Processing Units
        :param ResourceManager r_manager: resource manager
        :param list p_units: list of Processing Units
        """
        for i in range(self.n_pu):
            self.add_coupling(p_units[i].output_change_status_response, r_manager.input_change_status_response)
            self.add_coupling(p_units[i].output_set_dvfs_mode_response, r_manager.input_set_dvfs_mode_response)
            self.add_coupling(p_units[i].output_open_session_response, r_manager.input_open_session_response)
            self.add_coupling(p_units[i].output_close_session_response, r_manager.input_close_session_response)
