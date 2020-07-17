from xdevs.models import Coupled, Port
from typing import Dict

from ..common.packet.apps.service import ServiceConfiguration
from ..common.packet.apps.federation_management import FederationManagementConfiguration
from ..common.packet.packet import NetworkPacketConfiguration, PhysicalPacket, NetworkPacket
from ..common.edge_fed.edge_fed import EdgeDataCenterReport, EdgeDataCenterConfiguration
from .edc import EdgeDataCenter


class EdgeFederation(Coupled):
    def __init__(self, name: str, edcs_config: Dict[str, EdgeDataCenterConfiguration],
                 services_config: Dict[str, ServiceConfiguration], fed_mgmt_config: FederationManagementConfiguration,
                 network_config: NetworkPacketConfiguration, sdn_controller_id: str, lite=False):
        """
        Edge Federation xDEVS model
        :param name: xDEVS module name
        :param edcs_config: Edge Data Centers configuration dict {EDC ID: EDC configuration}
        :param services_config: dictionary with all the services_config configurations
        :param fed_mgmt_config: Federation Management Application configuration
        :param network_config: network layer packets configuration
        :param sdn_controller_id: ID of the SDN controller
        """

        super().__init__(name)
        # Unwrap configuration parameters
        self.n_edc = len(edcs_config)

        # Define sub-modules and add them to coupled module
        self.edcs = {edc_id: EdgeDataCenter(name + '_' + edc_id, edc_config, services_config, fed_mgmt_config,
                                            network_config, sdn_controller_id, lite)
                     for edc_id, edc_config in edcs_config.items()}
        [self.add_component(edc) for edc in self.edcs.values()]

        port_type = NetworkPacket if lite else PhysicalPacket

        # Define input/output ports
        self.output_edc_report = Port(EdgeDataCenterReport, 'output_edc_report')
        self.output_crosshaul = Port(port_type, 'output_crosshaul')
        self.add_out_port(self.output_edc_report)
        self.add_out_port(self.output_crosshaul)

        self.inputs_crosshaul = dict()
        for edc_id, edc in self.edcs.items():
            self.add_coupling(edc.output_edc_report, self.output_edc_report)
            self.add_coupling(edc.output_crosshaul, self.output_crosshaul)

            self.inputs_crosshaul[edc_id] = Port(port_type, 'input_crosshaul_' + edc_id)
            self.add_in_port(self.inputs_crosshaul[edc_id])
            self.add_coupling(self.inputs_crosshaul[edc_id], edc.input_crosshaul)
