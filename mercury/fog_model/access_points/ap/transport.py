import logging
from xdevs.models import Port
from ...network import EnableChannels
from ...common import Stateless, logging_overhead
from ...common.packet.packet import NetworkPacket
from ...common.packet.apps.federation_management import NewSDNPath
from ...common.packet.apps.service import GetDataCenterRequest, GetDataCenterResponse


LOGGING_OVERHEAD = "    "


class Transport(Stateless):
    def __init__(self, name, ap_id):
        super().__init__(name=name)
        self.ap_id = ap_id
        self.service_routing = dict()
        self.ue_connected = list()

        self.input_new_sdn_path = Port(NewSDNPath, name + '_input_new_sdn_path')
        self.input_connected_ue_list = Port(EnableChannels, name + '_input_connected_ue_list')
        self.input_service_routing_request = Port(GetDataCenterRequest, name + '_input_service_routing_request')
        self.input_radio = Port(NetworkPacket, name + '_input_radio')
        self.input_crosshaul = Port(NetworkPacket, name + '_input_crosshaul')
        self.output_service_routing_response = Port(GetDataCenterResponse, name + '_output_service_routing_response')
        self.output_crosshaul = Port(NetworkPacket, name + '_output_crosshaul')
        self.output_radio = Port(NetworkPacket, name + '_output_radio')
        self.add_in_port(self.input_new_sdn_path)
        self.add_in_port(self.input_connected_ue_list)
        self.add_in_port(self.input_service_routing_request)
        self.add_in_port(self.input_radio)
        self.add_in_port(self.input_crosshaul)
        self.add_out_port(self.output_service_routing_response)
        self.add_out_port(self.output_crosshaul)
        self.add_out_port(self.output_radio)

    def check_in_ports(self):
        self._process_new_connected_ue_list()
        self._process_new_sdn_path()
        self._process_service_routing()
        self._process_radio_messages()
        self._process_crosshaul_messages()

    def process_internal_messages(self):
        pass

    def _process_new_connected_ue_list(self):
        if self.input_connected_ue_list:
            ue_list = self.input_connected_ue_list.get().nodes_to
            self.ue_connected = [ue for ue in ue_list]

    def _process_new_sdn_path(self):
        if self.input_new_sdn_path:
            sdn_path = self.input_new_sdn_path.get()
            overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
            logging.info(overhead + '%s<---SDN Controller: new SDN path' % self.ap_id)
            self.service_routing = {service_id: dc for service_id, dc in sdn_path.service_route.items()}

    def _process_service_routing(self):
        overhead = logging_overhead(self._clock, "")
        for msg in self.input_service_routing_request.values:
            ue_id = msg.ue_id
            service_id = msg.service_id
            logging.info(overhead + '%s-->%s: service %s routing request' % (ue_id, self.ap_id, service_id))
            if ue_id not in self.ue_connected:
                logging.warning(overhead + '    message from disconnected UE %s. Ignoring request' % ue_id)
                continue
            dc_id = self.service_routing.get(service_id, None)
            if dc_id is None:
                logging.warning(overhead + '    no service routing for %s. Ignoring request' % service_id)
            else:
                app_msg = GetDataCenterResponse(ue_id, service_id, dc_id, msg.header)
                self.add_msg_to_queue(self.output_service_routing_response, app_msg)

    def _process_radio_messages(self):
        overhead = logging_overhead(self._clock, "")
        for msg in self.input_radio.values:
            ue_id = msg.node_from
            service_id = msg.data.service_id
            logging.info(overhead + '%s--->%s: %s-related message' % (ue_id, self.ap_id, service_id))
            if ue_id not in self.ue_connected:
                logging.warning(overhead + '    message from disconnected UE %s. Ignoring request' % ue_id)
                continue
            self.add_msg_to_queue(self.output_crosshaul, msg)

    def _process_crosshaul_messages(self):
        overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
        for msg in self.input_crosshaul.values:
            ue_id = msg.node_to
            dc_id = msg.node_from
            service_id = msg.data.service_id
            logging.info(overhead + '%s<---%s: %s-related message' % (self.ap_id, dc_id, service_id))
            if ue_id not in self.ue_connected:
                logging.warning(overhead + '    message to disconnected UE %s. Ignoring request' % ue_id)
                continue
            self.add_msg_to_queue(self.output_radio, msg)
