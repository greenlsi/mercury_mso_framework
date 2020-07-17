import logging
from xdevs.models import Port
from typing import Tuple, Dict, List
from ..common import logging_overhead, Stateless
from ..network.node import NodeLocation
from ..network.link import euclidean_distance
from ..common.packet.apps.federation_management import FederationManagementPacket, FederationManagementConfiguration
from ..common.packet.apps.federation_management import EdgeDataCenterReportPacket, NewSDNPath
from ..common.packet.packet import NetworkPacketConfiguration, NetworkPacket, PhysicalPacket
from ..common.packet.apps.service import GetDataCenterRequest, GetDataCenterResponse
from .sdn_strategy import SDNStrategyFactory


class SoftwareDefinedNetworkController(Stateless):

    LOGGING_OVERHEAD = "        "
    sdn_strategy_factory = SDNStrategyFactory()

    def __init__(self, name: str, sdn_controller_id: str, fed_mgmt_config: FederationManagementConfiguration,
                 network_config: NetworkPacketConfiguration, aps: Dict[str, Tuple[float, ...]],
                 edcs: Dict[str, Tuple[float, ...]], services_id: List[str], sdn_strategy_name: str, **kwargs):
        """
        xDEVS model of a Software-Defined Network Controller for interconnecting Acess Points and Edge Data Centers
        :param name: Name of the XDEVS SDN Controller module
        :param sdn_controller_id: ID of the SDN controller
        :param fed_mgmt_config: fed_controller_config management application configuration
        :param network_config: network packets configuration
        :param aps: list of APs in the scenario
        :param edcs: list of EDCs in the scenario
        :param services_id: ID of all the services defined in the scenario
        :param sdn_strategy_name: Software-Defined Network linking strategy name
        :param kwargs: SDN linking strategy configuration parameters
        """
        super().__init__(name=name)

        self.sdn_controller_id = sdn_controller_id
        self.fed_mgmt_config = fed_mgmt_config
        self.network_config = network_config
        self.aps = aps
        self.edcs = edcs

        self.sdn_strategy = self.sdn_strategy_factory.create_strategy(sdn_strategy_name, aps, edcs,
                                                                      services_id, **kwargs)

        self.designated_edcs = {ap_id: {service_id: None for service_id in services_id} for ap_id in aps}

        self.input_node_location = Port(NodeLocation, 'input_node_location')
        self.input_crosshaul = Port(PhysicalPacket, 'input_crosshaul')
        self.output_crosshaul = Port(PhysicalPacket, 'output_crosshaul')
        self.add_in_port(self.input_node_location)
        self.add_in_port(self.input_crosshaul)
        self.add_out_port(self.output_crosshaul)

    def check_in_ports(self):
        if self.input_node_location:
            edcs_location = dict()
            aps_location = dict()
            for job in self.input_node_location.values:
                node_id = job.node_id
                location = job.location
                if node_id in self.edcs:
                    edcs_location[node_id] = location
                elif node_id in self.aps:
                    aps_location[node_id] = location
            self.sdn_strategy.update_locations(edcs_location, aps_location)
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        for job in self.input_crosshaul.values:
            phys_node_from, net_msg = self._expand_physical_message(job)
            net_node_from, app_msg = self._expand_network_message(net_msg)
            if isinstance(app_msg, FederationManagementPacket):
                if isinstance(app_msg, EdgeDataCenterReportPacket):
                    logging.info(overhead + "SDNController: received EDC status")
                    edc_id = app_msg.edc_report.edc_id
                    self.sdn_strategy.update_edc_report(edc_id, app_msg.edc_report)
                else:
                    raise Exception("Packet type was not identified by SDN controller")
            else:
                raise Exception("Message type was not identified by SDN controller")
        self._select_edc_bindings(overhead)

    def _select_edc_bindings(self, overhead):
        """Select paths APs and EDCs. If a change is detected, the SDN Controller sends a message to the AP."""
        for ap_id in self.aps:
            edcs_per_service = self.sdn_strategy.assign_edc(ap_id)
            flag = False
            for service_id, edc_id in edcs_per_service.items():
                if edc_id != self.designated_edcs[ap_id][service_id]:
                    flag = True
                    self.designated_edcs[ap_id][service_id] = edc_id
                    if edc_id is None:
                        logging.warning(overhead + "    SDN controller could not find any available EDC for service %s"
                                        % service_id)
                    else:
                        logging.info(overhead + "    SDN found new EDC %s for AP %s and service %s"
                                     % (edc_id, ap_id, service_id))
            if flag:
                msg = NewSDNPath(self.designated_edcs[ap_id], self.fed_mgmt_config.header)
                self._add_msg_to_crosshaul_dl(msg, ap_id, ap_id)

    def _encapsulate_network_packet(self, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(self.sdn_controller_id, node_to, header, application_message)

    def _encapsulate_physical_packet(self, node_to: str, network_message: NetworkPacket):
        return PhysicalPacket(node_from=self.sdn_controller_id, node_to=node_to, data=network_message)

    def _expand_physical_message(self, physical_message):
        assert self.sdn_controller_id == physical_message.node_to
        return physical_message.node_from, physical_message.data

    def _expand_network_message(self, network_message: NetworkPacket):
        assert self.sdn_controller_id == network_message.node_to
        return network_message.node_from, network_message.data

    def _add_msg_to_crosshaul_dl(self, msg, network_to, physical_to):
        network = self._encapsulate_network_packet(network_to, msg)
        msg = self._encapsulate_physical_packet(physical_to, network)
        self.add_msg_to_queue(self.output_crosshaul, msg)

    def process_internal_messages(self):
        pass


class CoreLite(Stateless):
    LOGGING_OVERHEAD = "        "

    def __init__(self, name: str, core_config, fed_mgmt_config: FederationManagementConfiguration,
                 network_config: NetworkPacketConfiguration, ues: Dict[str, Tuple[float, ...]],
                 aps: Dict[str, Tuple[float, ...]], edcs: Dict[str, Tuple[float, ...]], services_id: List[str]):
        super().__init__(name=name)

        self.sdn_controller_id = core_config.sdnc_id
        self.fed_mgmt_config = fed_mgmt_config
        self.network_config = network_config
        self.ues = ues
        self.aps = aps
        self.edcs = edcs

        sdn_strategy_name = core_config.sdn_strategy_name
        sdn_strategy_config = core_config.sdn_strategy_config
        self.sdn_strategy = SoftwareDefinedNetworkController.sdn_strategy_factory.create_strategy(sdn_strategy_name, aps, edcs,
                                                                                                  services_id, **sdn_strategy_config)

        self.designated_edcs = {ap_id: {service_id: None for service_id in services_id} for ap_id in aps}
        self.designated_aps = self._select_ue_bindings()

        self.input_node_location = Port(NodeLocation, 'input_node_location')
        self.input_network = Port(NetworkPacket, 'input_network')
        self.output_network = Port(NetworkPacket, 'output_network')
        self.add_in_port(self.input_node_location)
        self.add_in_port(self.input_network)
        self.add_out_port(self.output_network)

    def check_in_ports(self):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        self.check_new_ue_locations(overhead)
        self.check_incoming_messages(overhead)
        self._select_edc_bindings(overhead)

    def check_new_ue_locations(self, overhead):
        if self.input_node_location:
            ues_location = list()
            for job in self.input_node_location.values:
                ue_id = job.node_id
                location = job.location
                self.ues[ue_id] = location
                ues_location.append(ue_id)
            res = self._select_ue_bindings(ues_location)
            for ue, ap in res.items():
                if ap != self.designated_aps[ue]:
                    logging.info(overhead + "UE {} is now connected to AP {}".format(ue, ap))
                    self.designated_aps[ue] = ap

    def check_incoming_messages(self, overhead):
        # Check new network messages
        for job in self.input_network.values:
            net_node_from, app_msg = self._expand_network_message(job)
            # Case 1: UE requesting EDC for a given service
            if isinstance(app_msg, GetDataCenterRequest):
                ue_id = net_node_from
                service_id = app_msg.service_id
                ap_id = self.designated_aps[ue_id]
                edc_id = self.designated_edcs[ap_id][service_id]
                if edc_id is not None:
                    response = GetDataCenterResponse(ue_id, service_id, edc_id, app_msg.header)
                    msg = self._encapsulate_network_packet(ue_id, response)
                    self.add_msg_to_queue(self.output_network, msg)
            # Case 2: EDC sending new status report
            elif isinstance(app_msg, EdgeDataCenterReportPacket):
                logging.info(overhead + "SDNC: received EDC status")
                edc_id = app_msg.edc_report.edc_id
                self.sdn_strategy.update_edc_report(edc_id, app_msg.edc_report)
            else:
                raise Exception("Message type was not identified by SDN controller")

    def _select_ue_bindings(self, ues: List[str] = None):
        if ues is None:
            ues = self.ues
        distances = {ue_id: {ap_id: euclidean_distance(self.ues[ue_id], ap_location)
                             for ap_id, ap_location in self.aps.items()} for ue_id in ues}
        designated_aps = dict()
        for ue_id, aps in distances.items():
            min_ap, min_distance = None, None
            for ap, distance in aps.items():
                if min_distance is None or distance < min_distance:
                    min_ap, min_distance = ap, distance
            designated_aps[ue_id] = min_ap
        return designated_aps

    def _select_edc_bindings(self, overhead):
        """Select paths APs and EDCs. If a change is detected, the SDN Controller sends a message to the AP."""
        for ap_id in self.aps:
            edcs_per_service = self.sdn_strategy.assign_edc(ap_id)
            for service_id, edc_id in edcs_per_service.items():
                if edc_id != self.designated_edcs[ap_id][service_id]:
                    self.designated_edcs[ap_id][service_id] = edc_id
                    if edc_id is None:
                        logging.warning(
                            overhead + "    SDN controller could not find any available EDC for service %s"
                            % service_id)
                    else:
                        logging.info(overhead + "    SDN found new EDC %s for AP %s and service %s"
                                     % (edc_id, ap_id, service_id))

    def _encapsulate_network_packet(self, node_to, application_message):
        header = self.network_config.header
        return NetworkPacket(self.sdn_controller_id, node_to, header, application_message)

    def _expand_network_message(self, network_message: NetworkPacket):
        assert self.sdn_controller_id == network_message.node_to
        return network_message.node_from, network_message.data

    def process_internal_messages(self):
        pass
