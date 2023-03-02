from mercury.msg.packet import AppPacket, NetworkPacket, PhysicalPacket, PacketInterface
from mercury.msg.packet.app_packet.acc_packet import AccessPacket
from mercury.msg.packet.app_packet.srv_packet import SrvPacket
from typing import Generic, Type
from ...common import ExtendedAtomic
from xdevs.models import Port


class Shortcut(ExtendedAtomic, Generic[PacketInterface]):
    def __init__(self, p_type: Type[PacketInterface], client_id: str):
        if p_type not in [AppPacket, NetworkPacket]:
            raise ValueError(f'Invalid value for p_type ({p_type})')
        super().__init__(f'client_{client_id}_shortcut')
        self.p_type: Type[PacketInterface] = p_type
        self.input_data: Port[PacketInterface] = Port(p_type, 'input_data')
        self.input_phys_pss: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_phys_pss')
        self.output_data_acc: Port[PacketInterface] = Port(p_type, 'output_data_acc')
        self.output_data_srv: Port[PacketInterface] = Port(p_type, 'output_data_srv')
        self.output_app_pss: Port[AppPacket] = Port(AppPacket, 'output_app_pss')
        self.add_in_port(self.input_data)
        self.add_in_port(self.input_phys_pss)
        self.add_out_port(self.output_data_acc)
        self.add_out_port(self.output_data_srv)
        self.add_out_port(self.output_app_pss)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        for msg in self.input_data.values:
            app = msg if isinstance(msg, AppPacket) else msg.data if isinstance(msg.data, AppPacket) else msg.data.data
            if isinstance(app, AccessPacket):
                self.add_msg_to_queue(self.output_data_acc, msg)
            elif isinstance(app, SrvPacket):
                self.add_msg_to_queue(self.output_data_srv, msg)
        for phys_msg in self.input_phys_pss.values:
            phys_msg.receive(self._clock)
            phys_msg.data.receive(self._clock)
            app_msg = phys_msg.data.data
            app_msg.snr = phys_msg.snr
            self.add_msg_to_queue(self.output_app_pss, app_msg)
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
