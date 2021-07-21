from mercury.logger import logger as logging, logging_overhead
from xdevs.models import Port
from typing import Set, Dict
from mercury.msg.network import EnableChannels, NetworkPacket
from ...common import ExtendedAtomic


class Transport(ExtendedAtomic):

    LOGGING_OVERHEAD = "    "

    def __init__(self, ap_id: str):
        super().__init__('aps_ap_{}_transport'.format(ap_id))
        self.ap_id: str = ap_id
        self.service_routing: Dict[str, str] = dict()
        self.ue_connected: Set[str] = set()

        self.input_connected_ue_list = Port(EnableChannels, 'input_connected_ue_list')
        self.input_radio = Port(NetworkPacket, 'input_radio')
        self.input_crosshaul = Port(NetworkPacket, 'input_crosshaul')
        self.output_crosshaul = Port(NetworkPacket, 'output_crosshaul')
        self.output_radio = Port(NetworkPacket, 'output_radio')
        self.add_in_port(self.input_connected_ue_list)
        self.add_in_port(self.input_radio)
        self.add_in_port(self.input_crosshaul)
        self.add_out_port(self.output_crosshaul)
        self.add_out_port(self.output_radio)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        self._process_new_connected_ue_list()
        self._process_radio_messages()
        self._process_crosshaul_messages()
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def _process_new_connected_ue_list(self):
        if self.input_connected_ue_list:
            ue_list = self.input_connected_ue_list.get().slave_nodes
            self.ue_connected = {ue for ue in ue_list}

    def _process_radio_messages(self):
        overhead = logging_overhead(self._clock, "")
        for msg in self.input_radio.values:
            logging.info(overhead + '{}--->{}: network message'.format(msg.node_from, self.ap_id))
            if msg.node_from not in self.ue_connected:
                logging.warning(overhead + '    message from disconnected UE %s. Ignoring request' % msg.node_from)
                continue
            self.add_msg_to_queue(self.output_crosshaul, msg)

    def _process_crosshaul_messages(self):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        for msg in self.input_crosshaul.values:
            logging.info(overhead + '{}<---{}: network message'.format(self.ap_id, msg.node_from))
            if msg.node_to not in self.ue_connected:
                logging.warning(overhead + '    message to disconnected UE {}. Ignoring request'.format(msg.node_to))
                continue
            self.add_msg_to_queue(self.output_radio, msg)
