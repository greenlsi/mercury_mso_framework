from xdevs.models import Coupled, Port
from typing import Dict, Tuple, Optional
from mercury.config.core import CoreConfig
from mercury.config.network import NodeConfig
from mercury.config.smart_grid import ConsumerConfig
from mercury.config.edcs import EdgeFederationConfig
from mercury.config.iot_devices import ServiceConfig
from mercury.config.radio import RadioAccessNetworkConfig
from mercury.msg.network import NodeLocation
from mercury.msg.smart_grid import ElectricityOffer
from mercury.msg.network import PhysicalPacket, NetworkPacket
from .amf import AccessAndMobilityManagementFunction
from .cnfs import CoreNetworkFunctions
from .demand_estimator import DemandEstimator
from .efc import EdgeFederationController
from .sdnc import SoftwareDefinedNetworkController, SoftwareDefinedNetworkControllerLite


class Core(Coupled):
    def __init__(self, core_config: CoreConfig, edge_fed_config: Optional[EdgeFederationConfig],
                 aps: Dict[str, Tuple[float, ...]], services: Dict[str, ServiceConfig],
                 consumers: Dict[str, ConsumerConfig], lite: bool = False):
        """
        Core Layer Module for Mercury Simulator
        :param core_config: Core Layer Configuration.
        :param edge_fed_config: Edge federation configuration parameters.
        :param aps: dictionary containing the APs in the scenario and their location.
        :param services: list containing all the services defined in the scenario.
        :param consumers: Smart Grid consumers configurations.
        """
        super().__init__('core')

        edcs = edge_fed_config.edcs
        edc_locations = {edc_id: edc_config.edc_location for edc_id, edc_config in edcs.items()}
        service_ids = {service for service in services}

        port_type = PhysicalPacket if not lite else NetworkPacket

        self.input_electricity_offer = Port(ElectricityOffer, 'input_electricity_offer')
        self.input_data = Port(port_type, 'input_data')
        self.output_data = Port(port_type, 'output_data')
        self.add_in_port(self.input_electricity_offer)
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_data)

        # Core Network Functions: classifies all the messages etc. and encapsulate them for the network
        cnfs = CoreNetworkFunctions(lite)
        self.add_component(cnfs)
        self.add_coupling(self.input_data, cnfs.input_data)
        self.add_coupling(cnfs.output_data, self.output_data)

        congestion = edge_fed_config.congestion
        slicing = edge_fed_config.edc_slicing
        if lite:
            sdnc = SoftwareDefinedNetworkControllerLite(core_config, aps, edc_locations,
                                                        service_ids, congestion, slicing, consumers)
            self.add_component(sdnc)

            self.input_remove_node = Port(str, 'input_remove_node')
            self.input_node_location = Port(NodeLocation, 'input_node_location')
            self.input_create_node = Port(NodeConfig, 'input_create_node')
            self.add_in_port(self.input_remove_node)
            self.add_in_port(self.input_node_location)
            self.add_in_port(self.input_create_node)
            self.add_coupling(self.input_remove_node, sdnc.input_remove_node)
            self.add_coupling(self.input_node_location, sdnc.input_node_location)
            self.add_coupling(self.input_create_node, sdnc.input_create_node)
        else:
            sdnc = SoftwareDefinedNetworkController(core_config, aps, edc_locations,
                                                    service_ids, congestion, slicing, consumers)
            self.add_component(sdnc)

        self.add_coupling(self.input_electricity_offer, sdnc.input_electricity_offer)
        self.add_coupling(cnfs.output_power_consumption, sdnc.input_edc_report)
        self.add_coupling(cnfs.output_datacenter_request, sdnc.input_datacenter_request)
        self.add_coupling(sdnc.output_datacenter_response, cnfs.input_datacenter_response)

        if edge_fed_config is not None:
            edcs_controller = EdgeFederationController(edge_fed_config, service_ids)
            self.add_component(edcs_controller)
            self.add_coupling(self.input_electricity_offer, edcs_controller.input_electricity_offer)
            self.add_coupling(cnfs.output_power_consumption, edcs_controller.input_edc_report)
            self.add_coupling(edcs_controller.output_edc_slicing, sdnc.input_edc_slicing)
            self.add_coupling(edcs_controller.output_dispatching, cnfs.input_dispatching)
            self.add_coupling(edcs_controller.output_hot_standby, cnfs.input_hot_standby)

            for service, config in services.items():
                if config.estimator_name is not None:
                    estimator = DemandEstimator(service, config.estimator_name, **config.estimator_config)
                    self.add_component(estimator)
                    self.add_coupling(estimator.output_demand_estimation, edcs_controller.input_demand_estimation)

        if not RadioAccessNetworkConfig.bypass_amf:
            amf = AccessAndMobilityManagementFunction()
            self.add_component(amf)
            self.add_coupling(cnfs.output_amf_request, amf.input_request)
            self.add_coupling(amf.output_response, cnfs.input_amf_response)
