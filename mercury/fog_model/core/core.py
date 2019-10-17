from xdevs.models import Coupled, Port
from .amf import AccessAndMobilityManagementFunction
from .sdn_controller import SDNController
from ..common.packet.application.ran import RadioAccessNetworkConfiguration
from ..common.packet.application.federation_management import FederationManagementConfiguration
from ..common.packet.network import NetworkPacketConfiguration
from ..common.packet.physical import PhysicalPacket
from ..common.core import CoreLayerConfiguration
from ..common.crosshaul import CrosshaulConfiguration


class Core(Coupled):
    def __init__(self, name, core_config, rac_config, fed_mgmt_config, network_config, crosshaul_config,
                 aps_location, edcs_location, fed_controller_id, services_id):
        """
        Core Layer Module for Mercury Simulator
        :param str name: Name of the Core layer XDEVS module
        :param CoreLayerConfiguration core_config: Core Layer Configuration
        :param RadioAccessNetworkConfiguration rac_config:
        :param FederationManagementConfiguration fed_mgmt_config:
        :param NetworkPacketConfiguration network_config:
        :param CrosshaulConfiguration crosshaul_config:
        :param dict aps_location: dictionary {AP ID: AP location}
        :param dict edcs_location: dictionary {EDC ID: EDC location}
        :param str fed_controller_id:
        :param list services_id:
        """
        super().__init__(name)

        # Unwrap configuration data
        amf_id = core_config.amf_id
        sdn_controller_id = core_config.sdn_controller_id
        crosshaul_transceiver = core_config.crosshaul_transceiver
        edc_slicing = core_config.edc_slicing
        congestion = core_config.congestion
        sdn_strategy = core_config.sdn_strategy(aps_location, edcs_location, congestion, services_id, edc_slicing)

        # Create submodules and add them to the coupled model
        amf = AccessAndMobilityManagementFunction(name + '_amf', amf_id, rac_config, network_config,
                                                  crosshaul_config, crosshaul_transceiver)
        sdn = SDNController(name + '_sdn', sdn_controller_id, fed_mgmt_config, network_config, crosshaul_config,
                            crosshaul_transceiver, fed_controller_id, aps_location, edcs_location, sdn_strategy)
        self.add_component(amf)
        self.add_component(sdn)

        # External couplings for AMF
        self.input_amf_ul = Port(PhysicalPacket, name + '_input_amf_ul')
        self.input_sdn_controller_ul = Port(PhysicalPacket, name + '_input_sdn_controller_ul')
        self.output_crosshaul_dl = Port(PhysicalPacket, name + '_output_crosshaul_dl')
        self.add_in_port(self.input_amf_ul)
        self.add_in_port(self.input_sdn_controller_ul)
        self.add_out_port(self.output_crosshaul_dl)

        # External couplings for AMF
        self._amf_external_couplings(amf)
        # External couplings for SDN controller
        self._sdn_external_couplings(sdn)

    def _amf_external_couplings(self, amf):
        """
        Add external couplings for Access and Mobility Management Function
        :param AccessAndMobilityManagementFunction amf: Access and Mobility Management Function module
        """
        self.add_coupling(self.input_amf_ul, amf.input_crosshaul_ul)
        self.add_coupling(amf.output_crosshaul_dl, self.output_crosshaul_dl)

    def _sdn_external_couplings(self, sdn):
        """
        Add external couplings for SDN controller
        :param SDNController sdn: SDN Controller module
        """
        self.add_coupling(self.input_sdn_controller_ul, sdn.input_crosshaul_ul)
        self.add_coupling(sdn.output_crosshaul_dl, self.output_crosshaul_dl)
