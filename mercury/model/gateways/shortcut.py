from mercury.msg.packet import AppPacket, NetworkPacket, PhysicalPacket
from mercury.msg.packet.app_packet.acc_packet import PSSMessage
from mercury.msg.packet.phys_packet import RadioPacket
from ..common import ExtendedAtomic
from xdevs.models import Port


class Shortcut(ExtendedAtomic):
    def __init__(self, gateway_id: str):
        super().__init__(f'gateway_{gateway_id}_shortcut')
        self.input_app: Port[AppPacket] = Port(AppPacket, 'input_app')
        self.output_app: Port[AppPacket] = Port(AppPacket, 'output_app')
        self.output_phys: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_pss')
        self.add_in_port(self.input_app)
        self.add_out_port(self.output_app)
        self.add_out_port(self.output_phys)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        for app_msg in self.input_app.values:
            if isinstance(app_msg, PSSMessage):
                node_from = app_msg.gateway_id
                node_to = app_msg.client_id
                net_msg = NetworkPacket(app_msg, node_from)
                net_msg.send(self._clock)
                self.add_msg_to_queue(self.output_phys, RadioPacket(node_from, node_to, net_msg, False))
            else:
                self.add_msg_to_queue(self.output_app, app_msg)
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
