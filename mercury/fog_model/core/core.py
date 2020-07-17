from xdevs.models import Coupled, Port
from typing import Dict, Tuple, List

from .amf import AccessAndMobilityManagementFunction
from .sdnc import SoftwareDefinedNetworkController
from ..network import TransceiverConfiguration, NodeConfiguration, NodeLocation
from ..common.packet.apps.ran import RadioAccessNetworkConfiguration
from ..common.packet.apps.federation_management import FederationManagementConfiguration
from ..common.packet.packet import NetworkPacketConfiguration, PhysicalPacket


class CoreLayerConfiguration:
    def __init__(self, amf_id: str, sdnc_id: str, core_location: Tuple[float, ...],
                 crosshaul_trx: TransceiverConfiguration = None, sdn_strategy_name: str = 'closest',
                 sdn_strategy_config: Dict = None):
        """

        :param amf_id:
        :param sdnc_id:
        :param core_location:
        :param crosshaul_trx:
        :param sdn_strategy_name:
        :param sdn_strategy_config:
        """
        self.amf_id = amf_id
        self.sdnc_id = sdnc_id
        self.sdn_strategy_name = sdn_strategy_name
        if sdn_strategy_config is None:
            sdn_strategy_config = dict()
        self.sdn_strategy_config = sdn_strategy_config
        self.amf_node = NodeConfiguration(amf_id, crosshaul_trx, initial_position=core_location)
        self.sdn_node = NodeConfiguration(sdnc_id, crosshaul_trx, initial_position=core_location)
        self.core_nodes = {self.amf_id: self.amf_node, self.sdnc_id: self.sdn_node}


class Core(Coupled):
    def __init__(self, name: str, core_config: CoreLayerConfiguration, rac_config: RadioAccessNetworkConfiguration,
                 fed_mgmt_config: FederationManagementConfiguration, network_config: NetworkPacketConfiguration,
                 aps: Dict[str, Tuple[float, ...]], edcs: Dict[str, Tuple[float, ...]], services_id: List[str]):
        """
        Core Layer Module for Mercury Simulator
        :param name: Name of the Core layer XDEVS module
        :param core_config: Core Layer Configuration
        :param rac_config:
        :param fed_mgmt_config:
        :param network_config:
        :param aps: list of APs in the scenario
        :param edcs: list of EDCs in the scenario
        :param services_id:
        """
        super().__init__(name)

        self.input_node_location = Port(NodeLocation, 'input_node_location')
        self.output_crosshaul = Port(PhysicalPacket, 'output_crosshaul')
        self.add_in_port(self.input_node_location)
        self.add_out_port(self.output_crosshaul)
        self.inputs_crosshaul = dict()

        self.sdnc_id = core_config.sdnc_id
        sdn_strategy_name = core_config.sdn_strategy_name
        sdn_strategy_config = core_config.sdn_strategy_config

        self.core_functions = {self.sdnc_id: SoftwareDefinedNetworkController(name + '_sdn', self.sdnc_id,
                                                                              fed_mgmt_config, network_config, aps,
                                                                              edcs, services_id, sdn_strategy_name,
                                                                              **sdn_strategy_config)}
        self.add_component(self.core_functions[self.sdnc_id])
        self.add_coupling(self.input_node_location, self.core_functions[self.sdnc_id].input_node_location)

        if not rac_config.bypass_amf:
            self.amf_id = core_config.amf_id
            self.core_functions[self.amf_id] = AccessAndMobilityManagementFunction(name + '_amf', self.amf_id,
                                                                                   rac_config, network_config)

        for core_function_id, core_function in self.core_functions.items():
            self.add_component(core_function)
            self.inputs_crosshaul[core_function_id] = Port(PhysicalPacket, 'input_' + core_function_id)
            self.add_in_port(self.inputs_crosshaul[core_function_id])
            self.add_coupling(self.inputs_crosshaul[core_function_id], core_function.input_crosshaul)
            self.add_coupling(core_function.output_crosshaul, self.output_crosshaul)
