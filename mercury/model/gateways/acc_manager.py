from __future__ import annotations
from mercury.logger import logger as logging, logging_overhead
from mercury.msg.network import ChannelShare
from mercury.msg.packet import NetworkPacket
from mercury.msg.packet.app_packet.srv_packet import SrvRelatedRequest
from mercury.msg.packet.app_packet.acc_packet import *
from mercury.utils.amf import AccessManagementFunction
from xdevs.models import Port
from ..common import ExtendedAtomic


class AccessManager(ExtendedAtomic):

    CLIENT_LOGGING_OVERHEAD = ''
    GATEWAY_LOGGING_OVERHEAD = '    '

    def __init__(self, gateway_id: str, wired: bool, default_server: str, amf: AccessManagementFunction):
        """
        Gateway access manager. It implements all the logic corresponding to the gateway.
        :param gateway_id: ID of the gateway.
        :param wired: if True, gateway deals with wired clients (i.e., mobility, HO and shares are not necessary).
        :param default_server: ID of the default server that will handle unknown requests.
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        self.gateway_id: str = gateway_id
        self.wired: bool = wired
        self.default_server: str = default_server
        self.amf: AccessManagementFunction = amf
        self.clients: list[str] = list()
        super().__init__(f'gateway_{gateway_id}_manager')

        self.input_app: Port[AppPacket] = Port(AppPacket, 'input_app')
        self.input_net: Port[NetworkPacket] = Port(NetworkPacket, 'input_net')
        self.output_access_acc: Port[AppPacket] = Port(AppPacket, 'output_access_acc')
        self.output_access_srv: Port[AppPacket] = Port(AppPacket, 'output_access_srv')
        self.output_access_net: Port[NetworkPacket] = Port(NetworkPacket, 'output_access_net')
        self.output_xh_app: Port[AppPacket] = Port(AppPacket, 'output_xh_app')
        self.output_xh_net: Port[NetworkPacket] = Port(NetworkPacket, 'output_xh_net')
        self.add_in_port(self.input_app)
        self.add_in_port(self.input_net)
        for port in self.output_access_acc, self.output_access_srv, \
                    self.output_access_net, self.output_xh_app, self.output_xh_net:
            self.add_out_port(port)
        if not self.wired:
            self.clients_ho: dict[str, str] = dict()
            self.input_send_pss: Port[str] = Port(str, 'input_send_pss')
            self.output_channel_share = Port(ChannelShare, 'output_channel_share')
            self.add_in_port(self.input_send_pss)
            self.add_out_port(self.output_channel_share)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        access_overhead: str = logging_overhead(self._clock, self.CLIENT_LOGGING_OVERHEAD)
        xh_overhead: str = logging_overhead(self._clock, self.GATEWAY_LOGGING_OVERHEAD)
        change: bool = self.process_app(access_overhead, xh_overhead)
        self.process_net(access_overhead, xh_overhead)
        if not self.wired:
            for client_id in self.input_send_pss.values:
                msg = PSSMessage(self.gateway_id, client_id, self._clock)
                msg.send(self._clock)
                self.add_msg_to_queue(self.output_access_acc, msg)
            if change:
                share = ChannelShare(self.gateway_id, [client_id for client_id in self.clients])
                self.add_msg_to_queue(self.output_channel_share, share)
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def process_app(self, access_overhead: str, xh_overhead: str) -> bool:
        change: bool = False
        for msg in self.input_app.values:
            if isinstance(msg, AccessPacket):
                change |= self.process_app_access(msg, access_overhead, xh_overhead)
            elif isinstance(msg, SrvRelatedRequest):
                self.process_app_srv(msg, access_overhead)
        return change

    def process_net(self, access_overhead: str, xh_overhead: str):
        for msg in self.input_net.values:
            if msg.node_from in self.clients:
                logging.debug(f'{access_overhead}{msg.node_from}--->{self.gateway_id}: network message')
                self.add_msg_to_queue(self.output_xh_net, msg)
            elif msg.node_to in self.clients:
                logging.debug(f'{xh_overhead}{self.gateway_id}<---{msg.node_from}: network message')
                self.add_msg_to_queue(self.output_access_net, msg)
            else:
                logging.warning(f'{xh_overhead}{self.gateway_id}: network message from/to unknown node')

    def process_app_access(self, msg: AccessPacket, access_overhead: str, xh_overhead: str) -> bool:
        change: bool = False
        if isinstance(msg, ConnectRequest):
            change |= self.connect_client(msg, access_overhead)
        elif isinstance(msg, DisconnectRequest):
            change |= self.disconnect_client(msg, access_overhead)
        elif not self.wired:
            if isinstance(msg, RRCMessage) and msg.client_id in self.clients:
                self.client_rrc(msg, access_overhead)
            elif isinstance(msg, HandOverRequest):
                change |= self.start_client_ho(msg, access_overhead)
            elif isinstance(msg, HandOverFinished) and msg.client_id in self.clients_ho:
                change |= self.finish_client_ho(msg, access_overhead)
        return change

    def process_app_srv(self, msg: SrvRelatedRequest, access_overhead: str):
        log_msg = f'{access_overhead}{msg.node_from}--->{self.gateway_id}: service-related message'
        if msg.node_from not in self.clients:
            logging.warning(f'{log_msg}, but client is not connected to gateway. Dropping message')
        elif msg.server_id is not None:
            logging.warning(f'{log_msg}, but message was redirected to {msg.server_id}. Ignoring message')
        else:
            logging.info(f'{log_msg}. Redirecting to default server {self.default_server}')
            msg.set_node_to(self.default_server)
            self.add_msg_to_queue(self.output_xh_app, msg)

    def connect_client(self, req: ConnectRequest, access_overhead: str) -> bool:
        change: bool = False
        response = req.client_id in self.clients
        log_function = logging.info
        log_msg = f'{access_overhead}{req.client_id}--->{self.gateway_id}: connect request'
        if response:
            log_function = logging.warning
            log_msg = f'{log_msg} (already connected)'
        else:
            response = self.amf.connect_client(req.client_id, self.gateway_id)
            if response:
                change = True
                self.clients.append(req.client_id)
            else:
                log_function = logging.warning
                log_msg = f'{log_msg} (request failed)'
        log_function(log_msg)
        response = ConnectResponse(req, response, self._clock)
        response.send(self._clock)
        self.add_msg_to_queue(self.output_access_acc, response)
        return change

    def disconnect_client(self, req: DisconnectRequest, access_overhead: str) -> bool:
        change: bool = False
        response = req.client_id not in self.clients
        log_function = logging.info
        log_msg = f'{access_overhead}{req.client_id}--->{self.gateway_id}: disconnect request'
        if response:
            log_function = logging.warning
            log_msg = f'{log_msg} (already disconnected)'
        else:
            response = self.amf.disconnect_client(req.client_id, self.gateway_id)
            if response:
                change = True
                self.clients.remove(req.client_id)
            else:
                log_function = logging.warning
                log_msg = f'{log_msg} (request failed)'
        log_function(log_msg)
        response = DisconnectResponse(req, response, self._clock)
        response.send(self._clock)
        self.add_msg_to_queue(self.output_access_acc, response)
        return change

    def start_client_ho(self, req: HandOverRequest, access_overhead: str) -> bool:
        log_msg = f'{access_overhead}{req.client_id}--->{self.gateway_id}: HO from {req.gateway_from} request'
        change = self.amf.handover_client(req.client_id, req.gateway_from, self.gateway_id)
        if change:
            logging.info(log_msg)
            self.clients.append(req.client_id)
        else:
            logging.warning(f'{log_msg} (HO failed)')
        response = HandOverResponse(req, change, self._clock)
        response.send(self._clock)
        self.add_msg_to_queue(self.output_access_acc, response)
        return change

    def finish_client_ho(self, req: HandOverFinished, access_overhead: str) -> bool:
        logging.info(f'{access_overhead}{req.client_id}--->{self.gateway_id}: HO finished. Result: {req.response}')
        self.clients_ho.pop(req.client_id)
        if req.response:
            self.clients.remove(req.client_id)
        return req.response

    def client_rrc(self, rrc: RRCMessage, access_overhead: str):
        log_msg = f'{access_overhead}{rrc.client_id}--->{self.gateway_id}: RRC message'
        best_gateway = max(rrc.perceived_snr, key=rrc.perceived_snr.get)
        if best_gateway != self.gateway_id:
            log_msg = f'{log_msg} (new best gateway {best_gateway}). Starting HO process'
            self.clients_ho[rrc.client_id] = best_gateway
            ho_data = HandOverData(rrc.client_id, self.gateway_id, best_gateway)
            start_ho = StartHandOver(ho_data, self._clock)
            start_ho.send(self._clock)
            self.add_msg_to_queue(self.output_access_acc, start_ho)
        logging.info(log_msg)
