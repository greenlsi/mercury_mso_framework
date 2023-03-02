from mercury.msg.client import GatewayConnection
from mercury.msg.packet import AppPacket, NetworkPacket, PhysicalPacket
from mercury.msg.packet.app_packet.acc_packet import AccessPacket
from mercury.msg.packet.phys_packet import RadioPacket
from typing import Optional
from xdevs.models import Port
from ...common import ExtendedAtomic


class ClientAccessTransceiver(ExtendedAtomic):
    def __init__(self, client_id: str, wired: bool, t_start: float = 0):
        """
        Model for client transceiver.
        :param client_id: ID of the client
        """
        self.client_id: str = client_id
        self.wired: bool = wired
        self.gateway_id: Optional[str] = None
        super().__init__(f'client_{self.client_id}_trx')
        self._clock = t_start

        self.input_gateway: Port[GatewayConnection] = Port(GatewayConnection, 'input_gateway')
        self.input_phys: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_phys')
        self.input_net: Port[NetworkPacket] = Port(NetworkPacket, 'input_net')
        self.output_phys_acc: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_acc')
        self.output_phys_srv: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_srv')
        self.output_net_acc: Port[NetworkPacket] = Port(NetworkPacket, 'output_net_acc')
        self.output_net_srv: Port[NetworkPacket] = Port(NetworkPacket, 'output_net_srv')

        self.add_in_port(self.input_gateway)
        self.add_in_port(self.input_phys)
        self.add_in_port(self.input_net)
        self.add_out_port(self.output_phys_acc)
        self.add_out_port(self.output_phys_srv)
        self.add_out_port(self.output_net_acc)
        self.add_out_port(self.output_net_srv)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        if self.input_gateway:
            self.gateway_id = self.input_gateway.get().gateway_id
        for phys_msg in self.input_phys.values:
            phys_msg.receive(self._clock)
            net_msg = phys_msg.data
            app_msg = net_msg.data if isinstance(net_msg.data, AppPacket) else net_msg.data.data
            out_port = self.output_net_acc if isinstance(app_msg, AccessPacket) else self.output_net_srv
            if isinstance(net_msg.data, AccessPacket):
                net_msg.data.snr = phys_msg.snr
            self.add_msg_to_queue(out_port, net_msg)
        for net_msg in self.input_net.values:
            app_msg = net_msg.data if isinstance(net_msg.data, AppPacket) else net_msg.data.data
            out_port = self.output_phys_acc if isinstance(app_msg, AccessPacket) else self.output_phys_srv
            node_to = net_msg.node_to if isinstance(app_msg, AccessPacket) else self.gateway_id
            if out_port == self.output_phys_acc or self.gateway_id is not None:
                phys_msg = RadioPacket(self.client_id, node_to, net_msg, self.wired)
                self.add_msg_to_queue(out_port, phys_msg)
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
