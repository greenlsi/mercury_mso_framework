from .packet import Packet
from .application import ApplicationPacket


class NetworkPacketConfiguration:
    def __init__(self, header):
        self.header = header


class NetworkPacket(Packet):
    """
    Network layer-based data (end-to-end logical addressing)
    :param node_from: node that sent the data
    :param node_to: node that is the receiver of the data
    :param ApplicationPacket data: Application packet that is encapsulated
    """
    def __init__(self, node_from, node_to, header=0, data=None):
        super().__init__(header, data)
        self.node_from = node_from
        self.node_to = node_to

    def compute_size(self):
        res = self.header
        if self.data:
            res += self.data.compute_size()
        return res
