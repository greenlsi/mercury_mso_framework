from __future__ import annotations
from mercury.msg.packet import PhysicalPacket, NetworkPacket
from mercury.msg.packet.phys_packet import CrosshaulPacket
from mercury.utils.amf import AccessManagementFunction
from xdevs.models import Port
from .network import AbstractNetwork
from ..common import ExtendedAtomic


class CrosshaulNetwork(AbstractNetwork):
    pass


class CrosshaulTransceiver(ExtendedAtomic):
    def __init__(self, node_id: str, amf: AccessManagementFunction):
        """
        Core network transceiver.
        :param node_id: ID of the node that owns the transceiver
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        self.node_id: str = node_id
        self.amf: AccessManagementFunction = amf
        super().__init__(f'xh_trx_{self.node_id}')
        self.input_net: Port[NetworkPacket] = Port(NetworkPacket, 'input_net')
        self.input_phys: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_phys')
        self.output_net_to_node: Port[NetworkPacket] = Port(NetworkPacket, 'output_net_to_node')
        self.output_net_to_other: Port[NetworkPacket] = Port(NetworkPacket, 'output_net_to_other')
        self.output_phys: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys')
        self.add_in_port(self.input_net)
        self.add_in_port(self.input_phys)
        self.add_out_port(self.output_net_to_node)
        self.add_out_port(self.output_net_to_other)
        self.add_out_port(self.output_phys)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        for phys_msg in self.input_phys.values:
            phys_msg.receive(self._clock)
            net_msg = phys_msg.data
            out_port = self.output_net_to_node if net_msg.node_to == self.node_id else self.output_net_to_other
            self.add_msg_to_queue(out_port, net_msg)
        for net_msg in self.input_net.values:
            node_to = self.amf.get_client_gateway(net_msg.node_to)
            if node_to is None:
                node_to = net_msg.node_to
            self.add_msg_to_queue(self.output_phys, CrosshaulPacket(self.node_id, node_to, net_msg))
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
