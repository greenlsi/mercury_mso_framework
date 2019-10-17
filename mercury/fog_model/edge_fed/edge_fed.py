from xdevs.models import Coupled, Port
from ..common.packet.application.federation_management import FederationManagementConfiguration
from ..common.packet.network import NetworkPacketConfiguration
from ..common.packet.physical import PhysicalPacket
from ..common.crosshaul import CrosshaulConfiguration
from .edc import EdgeDataCenter, EdgeDataCenterReport
from .fed_controller import FederationController, EdgeFederationControllerConfiguration
from .edc_mux import EdgeDataCenterMultiplexer


class EdgeFederation(Coupled):

    def __init__(self, name, edcs_config, controller_config, services_config, fed_mgmt_config, network_config,
                 crosshaul_config, sdn_controller_id):
        """
        Edge Federation xDEVS model
        :param str name: xDEVS module name
        :param dict edcs_config: Edge Data Centers configuration dict {EDC ID: EDC configuration}
        :param EdgeFederationControllerConfiguration controller_config: Edge Federation Controller Configuration
        :param dict services_config: dictionary with all the services_config configurations
        :param FederationManagementConfiguration fed_mgmt_config: Federation Management Application configuration
        :param NetworkPacketConfiguration network_config: network layer packets configuration
        :param CrosshaulConfiguration crosshaul_config: Crosshaul physical packets configuration
        :param str sdn_controller_id: ID of the SDN controller
        """
        super().__init__(name)
        # Unwrap configuration parameters
        fed_controller_id = controller_config.controller_id
        self.n_edc = len(edcs_config)

        # Define sub-modules and add them to coupled module
        edcs = [EdgeDataCenter(name + '_' + edc_id, edc_config, services_config, fed_mgmt_config,
                               network_config, crosshaul_config, fed_controller_id)
                for edc_id, edc_config in edcs_config.items()]
        edc_ids = [edc_id for edc_id in edcs_config]
        edc_mux = EdgeDataCenterMultiplexer(name + '_edc_mux', edc_ids)
        controller = FederationController(name + '_fed_controller', controller_config, fed_mgmt_config, network_config,
                                          crosshaul_config, sdn_controller_id, edc_ids)
        [self.add_component(edc) for edc in edcs]
        self.add_component(edc_mux)
        self.add_component(controller)

        # Define input/output ports
        self.input_edc_crosshaul_ul = Port(PhysicalPacket, name + '_input_edc_crosshaul_ul')
        self.input_fed_controller_crosshaul_ul = Port(PhysicalPacket, name + '_input_fed_controller_crosshaul_ul')
        self.output_crosshaul_dl = Port(PhysicalPacket, name + '_output_crosshaul_dl')
        self.output_crosshaul_ul = Port(PhysicalPacket, name + '_output_crosshaul_ul')
        self.output_edc_report = Port(EdgeDataCenterReport, name + '_output_edc_report')
        self.add_in_port(self.input_edc_crosshaul_ul)
        self.add_in_port(self.input_fed_controller_crosshaul_ul)
        self.add_out_port(self.output_crosshaul_dl)
        self.add_out_port(self.output_crosshaul_ul)
        self.add_out_port(self.output_edc_report)

        # External Couplings for EDC Mux
        self._edc_mux_external_couplings(edc_mux)
        # External Couplings for Federation Controller
        self._controller_external_couplings(controller)
        for edc in edcs:
            # External Couplings for EDCs
            self._edcs_external_couplings(edc)
            # Internal Couplings between EDC Mux and EDCs
            self._edc_mux_edcs_internal_couplings(edc_mux, edc)

    def _edc_mux_external_couplings(self, edc_mux):
        """
        EDC Multiplexer external couplings
        :param EdgeDataCenterMultiplexer edc_mux: EDC multiplexer
        """
        self.add_coupling(self.input_edc_crosshaul_ul, edc_mux.input_crosshaul_ul)

    def _controller_external_couplings(self, controller):
        """
        Federation Controller External couplings
        :param FederationController controller: Federation Controller
        """
        self.add_coupling(self.input_fed_controller_crosshaul_ul, controller.input_crosshaul_ul)
        self.add_coupling(controller.output_crosshaul_ul, self.output_crosshaul_ul)

    def _edcs_external_couplings(self, edc):
        """
        Data Centers external couplings
        :param EdgeDataCenter edc: Edge Data Center that compose the Edge Federation
        """
        self.add_coupling(edc.output_crosshaul_dl, self.output_crosshaul_dl)
        self.add_coupling(edc.output_crosshaul_ul, self.output_crosshaul_ul)
        self.add_coupling(edc.output_edc_report, self.output_edc_report)

    def _edc_mux_edcs_internal_couplings(self, edc_mux, datacenter):
        """
        Internal couplings between EDC multiplexer and Edge Data Centers
        :param EdgeDataCenterMultiplexer edc_mux: EDC Multiplexer
        :param EdgeDataCenter datacenter: List of Edge Data Centers that compose the Edge Federation
        """
        self.add_coupling(edc_mux.outputs_crosshaul_ul[datacenter.edc_id], datacenter.input_crosshaul_ul)
