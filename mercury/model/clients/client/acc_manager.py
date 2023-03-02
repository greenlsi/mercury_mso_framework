from __future__ import annotations
from math import inf
from mercury.config.gateway import GatewaysConfig
from mercury.config.network import DynamicNodeConfig, WiredNodeConfig
from mercury.logger import logger as logging, logging_overhead
from mercury.msg.client import SendPSS, ServiceActive, GatewayConnection
from mercury.msg.network import NewNodeLocation
from mercury.msg.packet.app_packet.acc_packet import *
from typing import Iterable
from xdevs.models import Port
from ...common import ExtendedAtomic


class AccessManager(ExtendedAtomic):
    LOGGING_OVERHEAD = ''
    PHASE_DISCONNECTED = 'disconnected'
    PHASE_AWAIT_CONNECTION = 'await_connection'
    PHASE_CONNECTED = 'connected'
    PHASE_AWAIT_HO = 'await_ho'
    PHASE_AWAIT_DISCONNECTION = 'disconnect_request'

    def __init__(self, client_config: DynamicNodeConfig):
        """
        Client access network manager model.
        :param client_config: configuration related to the client.
        """
        self.client_id: str = client_config.node_id
        super().__init__(f'{self.client_id}_acc_manager')
        self._clock = client_config.t_start
        self.t_start: float = client_config.t_start
        self.t_end: float = client_config.t_end
        self.t_pss_window: float = self.t_start
        self.next_gw: str | None = None
        self.wired: bool = False
        self.aux_req: AccessPacket | None = None
        self.keep_connected: bool = client_config.keep_connected
        self.gateway: str | None = None
        self.active_srv: set[str] = set()
        self.perceived_snr: dict[str, float] = dict()
        if isinstance(client_config, WiredNodeConfig):
            self.t_pss_window, self.next_gw, self.wired = inf, client_config.gateway_id, True

        self.input_srv_active: Port[ServiceActive] = Port(ServiceActive, 'input_srv_active')
        self.input_acc: Port[AppPacket] = Port(AccessPacket, 'input_acc')
        self.input_new_location: Port[NewNodeLocation] = Port(NewNodeLocation, 'input_new_location')
        self.output_send_pss: Port[SendPSS] = Port(SendPSS, 'output_send_pss')
        self.output_gateway: Port[GatewayConnection] = Port(GatewayConnection, 'output_gateway')
        self.output_connected: Port[bool] = Port(bool, 'output_connected')
        self.output_acc: Port[AccessPacket] = Port(AccessPacket, 'output_acc')
        self.add_in_port(self.input_srv_active)
        self.add_in_port(self.input_acc)
        self.add_in_port(self.input_new_location)
        self.add_out_port(self.output_send_pss)
        self.add_out_port(self.output_gateway)
        self.add_out_port(self.output_connected)
        self.add_out_port(self.output_acc)

    @property
    def ready_to_dump(self) -> bool:
        return self.phase == self.PHASE_DISCONNECTED and not self.connection_req

    @property
    def connection_req(self) -> bool:
        return self.keep_connected and self._clock < self.t_end or self.active_srv

    def deltint_extension(self):
        self.passivate(self.phase)
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        if self.phase == self.PHASE_DISCONNECTED:
            self.deltint_disconnected(overhead)
        elif self.phase == self.PHASE_CONNECTED:
            self.deltint_connected(overhead=overhead)
        if not self.msg_queue_empty():
            self.activate(self.phase)

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        self.update_active_srv()
        msgs = self.filter_acc_msg(overhead)
        if self.phase == self.PHASE_DISCONNECTED:
            self.deltint_disconnected(overhead)
        elif self.phase == self.PHASE_AWAIT_CONNECTION:
            self.deltext_await_connection(msgs, overhead)
        elif self.phase == self.PHASE_CONNECTED:
            self.deltext_connected(msgs, overhead)
        elif self.phase == self.PHASE_AWAIT_HO:
            self.deltext_await_ho(msgs, overhead)
        elif self.phase == self.PHASE_AWAIT_DISCONNECTION:
            self.deltext_await_disconnection(msgs, overhead)
        self.process_new_location()
        if not self.msg_queue_empty():
            self.sigma = 0

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.phase = self.PHASE_DISCONNECTED
        self.deltint_extension()

    def exit(self):
        pass

    def deltint_disconnected(self, overhead: str):
        self.phase = self.PHASE_DISCONNECTED
        if self.connection_req:
            if not self.wired:
                if self._clock < self.t_pss_window:
                    self.hold_in(self.PHASE_DISCONNECTED, self.t_pss_window - self._clock)
                elif self.perceived_snr:
                    self.t_pss_window = inf
                    self.next_gw = max(self.perceived_snr, key=self.perceived_snr.get)
                else:
                    self.t_pss_window = self._clock + GatewaysConfig.PSS_WINDOW
                    if self.t_pss_window < self.t_end:
                        logging.info(f'{overhead}{self.client_id} sniffing gateways...')
                        self.add_msg_to_queue(self.output_send_pss, SendPSS(self.client_id, None))
            if self.next_gw is not None:
                logging.info(f'{overhead}{self.client_id} connecting to gateway {self.next_gw}...')
                self.aux_req = ConnectRequest(self.client_id, self.next_gw, self._clock)
                self.aux_req.send(self._clock)
                self.add_msg_to_queue(self.output_acc, self.aux_req)
                self.activate(self.PHASE_AWAIT_CONNECTION)
        else:
            self.perceived_snr = dict()

    def deltint_connected(self, overhead: str, connected: bool = True):
        self.phase = self.PHASE_CONNECTED
        if self.connection_req:
            if not self.wired:
                if self.t_pss_window == inf:
                    next_t = inf if self.active_srv else self.t_end
                    self.hold_in(self.PHASE_CONNECTED, next_t - self._clock)
                elif self._clock < self.t_pss_window:
                    self.hold_in(self.PHASE_CONNECTED, self.t_pss_window - self._clock)
                else:
                    self.t_pss_window = inf
                    snr = {gateway_id: snr for gateway_id, snr in self.perceived_snr.items()}
                    msg = RRCMessage(self.client_id, self.gateway, snr, self._clock)
                    msg.send(self._clock)
                    self.add_msg_to_queue(self.output_acc, msg)
            else:
                next_t = inf if self.active_srv else self.t_end
                self.hold_in(self.PHASE_CONNECTED, next_t - self._clock)
        else:
            self.aux_req = DisconnectRequest(self.client_id, self.gateway, self._clock)
            self.aux_req.send(self._clock)
            self.add_msg_to_queue(self.output_acc, self.aux_req)
            if connected:
                self.add_msg_to_queue(self.output_gateway, GatewayConnection(self.client_id, None))
                self.add_msg_to_queue(self.output_connected, False)
            logging.info(f'{overhead} {self.client_id} disconnecting from gateway {self.gateway}...')
            self.activate(self.PHASE_AWAIT_DISCONNECTION)

    def update_active_srv(self):
        for msg in self.input_srv_active.values:
            if msg.active:
                self.active_srv.add(msg.service_id)
            elif msg.service_id in self.active_srv:
                self.active_srv.remove(msg.service_id)

    def filter_acc_msg(self, overhead: str):
        if not self.wired:
            res = list()
            for msg in self.input_acc.values:
                if isinstance(msg, PSSMessage):
                    gateway_id, snr = msg.node_from, msg.snr
                    if gateway_id not in self.perceived_snr or self.perceived_snr[gateway_id] != snr:
                        if self._clock > self.t_pss_window or self.t_pss_window == inf:  # TODO revisar esto
                            self.t_pss_window = self._clock + GatewaysConfig.PSS_WINDOW
                        logging.info(f'{overhead}{self.client_id}<---{gateway_id}: PSS message (SNR = {snr})')
                        self.perceived_snr[gateway_id] = snr
                else:
                    res.append(msg)
            return res
        else:
            return self.input_acc.values

    def process_new_location(self):
        if not self.wired and self.input_new_location:
            if self.phase == self.PHASE_DISCONNECTED and self.connection_req:
                next_gw = max(self.perceived_snr, key=self.perceived_snr.get, default=None)
                self.add_msg_to_queue(self.output_send_pss, SendPSS(self.client_id, next_gw))
            elif self.phase == self.PHASE_CONNECTED:
                self.add_msg_to_queue(self.output_send_pss, SendPSS(self.client_id, self.gateway))
            elif self.phase == self.PHASE_AWAIT_CONNECTION or self.phase == self.PHASE_AWAIT_HO:
                self.add_msg_to_queue(self.output_send_pss, SendPSS(self.client_id, self.next_gw))

    def deltext_await_connection(self, msgs: Iterable[AppPacket], overhead: str):
        for msg in msgs:
            if isinstance(msg, ConnectResponse) and msg.request == self.aux_req:
                self.aux_req = None
                msg.receive(self._clock)
                if not self.wired:
                    self.next_gw = None
                log_msg = f'{overhead}{self.client_id}<---{msg.gateway_id}: connect response: {msg.response}'
                if msg.response:
                    self.gateway = msg.gateway_id
                    if self.connection_req:
                        logging.info(log_msg)
                        self.add_msg_to_queue(self.output_connected, True)
                        self.add_msg_to_queue(self.output_gateway, GatewayConnection(self.client_id, self.gateway))
                    else:
                        logging.info(f'{log_msg}, but connection is not required anymore. Disconnecting...')
                    self.deltint_connected(log_msg, False)
                else:
                    self.perceived_snr = dict()
                    self.t_pss_window = self._clock
                    logging.warning(log_msg)
                    self.deltint_disconnected(overhead)
                return

    def deltext_connected(self, msgs: Iterable[AppPacket], overhead: str):
        if not self.wired:
            for msg in msgs:
                if isinstance(msg, StartHandOver):
                    assert msg.gateway_from == self.gateway
                    msg.receive(self._clock)
                    self.next_gw = msg.gateway_to
                    logging.info(f'{overhead}{self.client_id}<---{self.gateway}: start HO to gateway {self.next_gw} request.')
                    msg = HandOverRequest(msg.ho_data, self._clock)
                    msg.send(self._clock)
                    self.add_msg_to_queue(self.output_acc, msg)
                    self.add_msg_to_queue(self.output_connected, False)
                    self.add_msg_to_queue(self.output_gateway, GatewayConnection(self.client_id, None))
                    self.activate(self.PHASE_AWAIT_HO)
                    return
        self.deltint_connected(overhead)

    def deltext_await_ho(self, msgs: Iterable[AppPacket], overhead: str):
        for msg in msgs:
            if isinstance(msg, HandOverResponse):
                assert msg.gateway_to == self.next_gw
                assert msg.gateway_from == self.gateway
                msg.receive(self._clock)
                response = msg.response
                logging.info(f'{overhead}{self.client_id}<---{self.next_gw}: HO from AP {self.gateway} response: {response}')
                if response:
                    self.gateway = self.next_gw
                self.next_gw = None
                msg = HandOverFinished(msg, self._clock)
                msg.send(self._clock)
                self.add_msg_to_queue(self.output_acc, msg)
                if self.connection_req:
                    self.add_msg_to_queue(self.output_connected, True)
                    self.add_msg_to_queue(self.output_gateway, GatewayConnection(self.client_id, self.gateway))
                self.deltint_connected(overhead, self.connection_req)
                return

    def deltext_await_disconnection(self, msgs: Iterable[AppPacket], overhead: str):
        for msg in msgs:
            if isinstance(msg, DisconnectResponse) and msg.request == self.aux_req:
                msg.receive(self._clock)
                gateway_id = msg.node_from
                response = msg.response
                log_msg = f'{overhead}{self.client_id}<---{gateway_id}: Disconnect response: {response}'
                if response:
                    self.gateway = None
                    if self.connection_req:
                        log_msg = f'{log_msg}, but client requires to be connected again'
                    else:
                        self.perceived_snr = dict()
                    logging.info(log_msg)
                    self.deltint_disconnected(overhead)
                else:
                    logging.warning(f'{log_msg}')
                    self.deltint_connected(overhead, False)
                return
