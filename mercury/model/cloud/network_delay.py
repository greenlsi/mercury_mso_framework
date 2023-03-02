from __future__ import annotations
from math import inf
from mercury.config.cloud import CloudConfig
from mercury.msg.packet import PacketInterface, AppPacket
from random import uniform
from typing import Generic, Type, NoReturn
from xdevs.models import Port
from ..common.fsm import ExtendedAtomic


class CloudNetworkDelay(ExtendedAtomic, Generic[PacketInterface]):
    def __init__(self, p_type: Type[PacketInterface], cloud_config: CloudConfig):
        from mercury.plugin import AbstractFactory, CloudNetworkDelay
        cloud_id: str = cloud_config.cloud_id
        super().__init__(f'{cloud_id}_delay')
        self.cloud_id = cloud_id
        self.msg_buffer: dict[float, list[PacketInterface]] = dict()

        delay_id = cloud_config.delay_id
        delay_config = cloud_config.delay_config
        # We pop the loss probability, as this is managed by the model instead of the plugin
        self.loss_p = 0 if p_type == AppPacket else delay_config.pop('loss_p', 0)
        if self.loss_p < 0 or self.loss_p > 1:
            raise ValueError('invalid loss probability value')
        self.network_delay: CloudNetworkDelay = AbstractFactory.create_cloud_net_delay(delay_id, **delay_config)

        self.input_data: Port[PacketInterface] = Port(p_type, "input_data")
        self.output_to_cloud: Port[PacketInterface] = Port(p_type, "output_to_cloud")
        self.output_to_others: Port[PacketInterface] = Port(p_type, "output_to_others")
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_to_cloud)
        self.add_out_port(self.output_to_others)

    def deltint_extension(self):
        self.msg_buffer.pop(self._clock)
        self.sigma = self.next_sigma()

    def deltext_extension(self, e):
        for msg in self.input_data.values:
            if self.loss_p == 0 or uniform(0, 1) > self.loss_p:  # input messages can get lost!
                t_out = self._clock + self.network_delay.delay(msg.size)
                if t_out not in self.msg_buffer:
                    self.msg_buffer[t_out] = list()
                self.msg_buffer[t_out].append(msg)
        self.sigma = self.next_sigma()

    def lambdaf_extension(self):
        clock = self._clock + self.sigma
        for msg in self.msg_buffer.get(clock, list()):
            port_to = self.output_to_cloud if msg.node_to == self.cloud_id else self.output_to_others
            port_to.add(msg)

    def initialize(self) -> NoReturn:
        self.sigma = self.next_sigma()

    def exit(self) -> NoReturn:
        pass

    def next_sigma(self) -> float:
        return min(self.msg_buffer, default=inf) - self._clock
