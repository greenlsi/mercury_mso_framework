from __future__ import annotations
from math import inf
from mercury.msg.packet import AppPacket, NetworkPacket
from typing import Dict, List, NoReturn
from xdevs.models import Port
from .fsm import ExtendedAtomic


class NetworkManager(ExtendedAtomic):
    def __init__(self, node_id: str, manager_id: str | None = None, enabled: bool = True):
        model_id = f'net_manager_{node_id}'
        if manager_id is not None:
            model_id = f'{model_id}_{manager_id}'
        super().__init__(model_id)
        self.node_id: str = node_id
        self.manager_id: str | None = manager_id
        self.enabled: bool = enabled
        self.awaiting_ack: List[NetworkPacket] = list()
        self.msg_queue: Dict[AppPacket, NetworkPacket] = dict()
        self.ack_queue: Dict[NetworkPacket, NetworkPacket] = dict()

        self.input_ctrl: Port[bool] = Port(bool, 'input_ctrl')
        self.input_app: Port[AppPacket] = Port(AppPacket, 'input_app')
        self.input_net: Port[NetworkPacket] = Port(NetworkPacket, 'input_net')
        self.output_app: Port[AppPacket] = Port(AppPacket, 'output_app')
        self.output_net: Port[NetworkPacket] = Port(NetworkPacket, 'output_net')
        self.add_in_port(self.input_ctrl)
        self.add_in_port(self.input_app)
        self.add_in_port(self.input_net)
        self.add_out_port(self.output_app)
        self.add_out_port(self.output_net)

    def deltint_extension(self):
        if self.enabled:
            trash = list()
            for net_msg in self.awaiting_ack:
                if net_msg.timeout <= self._clock:
                    if net_msg.ack is None:
                        net_msg.send(self._clock)
                        self.add_msg_to_queue(self.output_net, net_msg)
                    else:
                        trash.append(net_msg)
            for net_msg in trash:
                self.awaiting_ack.remove(net_msg)
        self.hold_in('STATELESS', self.next_timeout())

    def deltext_extension(self, e):
        if self.input_ctrl:
            self.enabled = self.input_ctrl.get()
        # Check incoming network messages
        for net_msg in self.input_net.values:
            assert net_msg.node_to == self.node_id
            net_msg.receive(self._clock)
            _, app_msg = net_msg.expanse_packet()
            if isinstance(app_msg, AppPacket):
                if net_msg.ack is None:
                    self.add_msg_to_queue(self.output_app, app_msg)
                self.send_ack(net_msg)
            else:
                self.receive_ack(app_msg)
        # Check incoming application messages
        for app_msg in self.input_app.values:
            self.send_app_msg(app_msg)
        self.bulk_awaiting_msg()
        self.hold_in('STATELESS', self.next_timeout())

    def lambdaf_extension(self):
        pass

    def initialize(self) -> NoReturn:
        self.passivate('STATELESS')

    def exit(self) -> NoReturn:
        pass

    def next_timeout(self) -> float:
        if not self.msg_queue_empty():
            return 0
        elif self.enabled:
            return min((msg.timeout for msg in self.awaiting_ack), default=inf) - self._clock
        else:
            return inf

    def send_ack(self, msg: NetworkPacket):
        if self.enabled:
            ack = NetworkPacket(msg, self.node_id) if msg.ack is None else msg.ack
            ack.send(self._clock)
            self.add_msg_to_queue(self.output_net, ack)
        elif msg not in self.ack_queue:
            self.ack_queue[msg] = NetworkPacket(msg, self.node_id)

    def receive_ack(self, msg: NetworkPacket):
        if msg in self.awaiting_ack:
            self.awaiting_ack.remove(msg)

    def send_app_msg(self, app_msg: AppPacket):
        net_msg = NetworkPacket(app_msg, self.node_id)
        if self.enabled:
            net_msg.send(self._clock)
            self.add_msg_to_queue(self.output_net, net_msg)
            self.awaiting_ack.append(net_msg)
        else:
            self.msg_queue[app_msg] = net_msg

    def bulk_awaiting_msg(self):
        if self.enabled:
            if self.msg_queue:
                for net_msg in self.msg_queue.values():
                    net_msg.send(self._clock)
                    self.add_msg_to_queue(self.output_net, net_msg)
                    self.awaiting_ack.append(net_msg)
                self.msg_queue.clear()
            if self.ack_queue:
                for ack_msg in self.ack_queue.values():
                    ack_msg.send(self._clock)
                    self.add_msg_to_queue(self.output_net, ack_msg)
                self.ack_queue.clear()
