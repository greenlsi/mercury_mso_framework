from mercury.logger import logger as logging, logging_overhead
import mercury.plugin as f
from xdevs.models import Port
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Set, Optional
from mercury.config.core import CoreConfig
from mercury.config.network import NodeConfig
from mercury.config.smart_grid import ConsumerConfig
from mercury.msg.network import NodeLocation
from mercury.msg.cnfs import EdgeDataCenterSlicing
from mercury.msg.smart_grid import ElectricityOffer, PowerConsumptionReport
from mercury.msg.network.packet.app_layer.service import GetDataCenterRequest, GetDataCenterResponse
from mercury.utils.maths import euclidean_distance
from ..common import ExtendedAtomic


class AbstractSDNC(ExtendedAtomic, ABC):

    LOGGING_OVERHEAD = "        "

    def __init__(self, core_config: CoreConfig, aps: Dict[str, Tuple[float, ...]], edcs: Dict[str, Tuple[float, ...]],
                 services: Set[str], edc_congestion: float = 100,
                 edc_slicing: Optional[Dict[str, Dict[str, float]]] = None,
                 consumers: Optional[Dict[str, ConsumerConfig]] = None):
        """
        xDEVS model of a Software-Defined Network Controller for interconnecting Acess Points and Edge Data Centers

        :param core_config: Core network configuration
        :param aps: list of APs in the scenario
        :param edcs: list of EDCs in the scenario
        :param services: ID of all the services defined in the scenario
        :param edc_congestion: Maximum utilization allowed for an EDC.
        :param edc_slicing: Initial Edge Federation slicing
        :param consumers: Smart Grid consumers configurations
        """
        super().__init__(name='core_sdnc')

        self.aps: Dict[str, Tuple[float, ...]] = aps
        self.edcs: Dict[str, Tuple[float, ...]] = edcs
        self.services: Set[str] = services

        sdn_strategy_name = core_config.sdnc_name
        sdn_strategy_config = core_config.sdnc_config
        self.sdn_strategy = f.AbstractFactory.create_sdn_strategy(sdn_strategy_name, aps=aps, edcs=edcs,
                                                                  services=services, consumers=consumers,
                                                                  edc_congestion=edc_congestion,
                                                                  edc_slicing=edc_slicing, **sdn_strategy_config)

        self.designated_edcs = {ap_id: {service_id: None for service_id in services} for ap_id in aps}

        self.input_electricity_offer = Port(ElectricityOffer, 'input_electricity_offer')
        self.input_edc_slicing = Port(EdgeDataCenterSlicing, 'input_edc_slicing')
        self.input_edc_report = Port(PowerConsumptionReport, 'input_edc_report')
        self.input_datacenter_request = Port(GetDataCenterRequest, 'input_datacenter_request')
        self.output_datacenter_response = Port(GetDataCenterResponse, 'output_datacenter_response')

        self.add_in_port(self.input_electricity_offer)
        self.add_in_port(self.input_edc_slicing)
        self.add_in_port(self.input_edc_report)
        self.add_in_port(self.input_datacenter_request)
        self.add_out_port(self.output_datacenter_response)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        self.check_additional_in_ports(overhead)
        self.check_base_in_ports(overhead)
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def check_base_in_ports(self, overhead):
        res = False
        # 1. Update new electricity offers
        for job in self.input_electricity_offer.values:
            res = True
            provider_id = job.provider_id
            offer = job.cost
            logging.info(overhead + "SDNC: received new electricity offer: {},{}".format(provider_id, offer))
            self.sdn_strategy.update_electricity_offer(provider_id, offer)
        # 2. Update new EDC reports
        for job in self.input_edc_report.values:
            res = True
            edc_id = job.consumer_id
            logging.info(overhead + "SDNC: received new EDC {} power consumption report".format(edc_id))
            self.sdn_strategy.update_edc_report(edc_id, job)
        # 3. Updata new EDC slicing
        for job in self.input_edc_slicing.values:
            self.sdn_strategy.update_edc_slicing(job.edc_id, job.slicing)
        if res:
            self.select_edc_bindings(overhead)
        for job in self.input_datacenter_request.values:
            self.deduce_datacenter(job)

    def select_edc_bindings(self, overhead):
        """Select paths APs and EDCs. If a change is detected, the SDN Controller sends a message to the AP."""
        for ap in self.aps:
            for service in self.services:
                edc = self.sdn_strategy.assign_edc(ap, service)
                if edc != self.designated_edcs[ap][service]:
                    self.designated_edcs[ap][service] = edc
                    log = logging.warning if edc is None else logging.info
                    log(overhead + "    New EDC binding ({}.{}->{})".format(ap, service, edc))

    def check_additional_in_ports(self, overhead):
        """Overwrite this function if SDNC model has more than the standard ports"""
        pass

    @abstractmethod
    def deduce_datacenter(self, request: GetDataCenterRequest):
        pass


class SoftwareDefinedNetworkController(AbstractSDNC):
    def deduce_datacenter(self, request: GetDataCenterRequest):
        edc_id: Optional[str] = self.designated_edcs[request.ap_id][request.service_id]
        if edc_id is not None:
            self.add_msg_to_queue(self.output_datacenter_response, GetDataCenterResponse(request, edc_id))


class SoftwareDefinedNetworkControllerLite(AbstractSDNC):

    def __init__(self, core_config, aps: Dict[str, Tuple[float, ...]], edcs: Dict[str, Tuple[float, ...]],
                 services: Set[str], edc_congestion: float = 100,
                 edc_slicing: Optional[Dict[str, Dict[str, float]]] = None,
                 consumers: Optional[Dict[str, ConsumerConfig]] = None):
        super().__init__(core_config, aps, edcs, services, edc_congestion, edc_slicing, consumers)

        self.ues = dict()
        self.designated_aps = dict()

        self.input_remove_node = Port(str, 'input_remove_node')
        self.input_node_location = Port(NodeLocation, 'input_node_location')
        self.input_create_node = Port(NodeConfig, 'input_create_node')
        self.add_in_port(self.input_remove_node)
        self.add_in_port(self.input_node_location)
        self.add_in_port(self.input_create_node)

    def check_additional_in_ports(self, overhead):
        # 1. Remove UEs
        for ue_id in self.input_remove_node.values:
            self.ues.pop(ue_id, None)
            self.designated_aps.pop(ue_id, None)
        # 2. Create UEs
        new_ue_location = set()
        for node_config in self.input_create_node.values:
            ue_id = node_config.node_id
            self.ues[ue_id] = node_config.initial_location
            self.designated_aps[ue_id] = None
            new_ue_location.add(ue_id)
        # 3. Check if any UE has changed its position
        for job in self.input_node_location.values:
            ue_id = job.node_id
            self.ues[ue_id] = job.location
            new_ue_location.add(ue_id)
        # 4. Check potential new UE-AP bindings
        for ue, ap in self.select_ue_bindings(new_ue_location).items():
            if ap != self.designated_aps[ue]:
                logging.info(overhead + "UE {} is now connected to AP {}".format(ue, ap))
                self.designated_aps[ue] = ap

    def select_ue_bindings(self, ues: Set[str]) -> Dict[str, str]:
        aps = {ue_id: sorted([(euclidean_distance(self.ues[ue_id], ap_location), ap_id)
                              for ap_id, ap_location in self.aps.items()]) for ue_id in ues}
        return {ue_id: distance[0][1] for ue_id, distance in aps.items()}

    def deduce_datacenter(self, request: GetDataCenterRequest):
        ap_id: str = self.designated_aps[request.ue_id]
        edc: Optional[str] = self.designated_edcs[ap_id][request.service_id]
        if edc is not None:
            self.add_msg_to_queue(self.output_datacenter_response, GetDataCenterResponse(request, edc))
