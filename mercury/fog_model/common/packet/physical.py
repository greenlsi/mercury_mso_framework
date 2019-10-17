from mercury.fog_model.common.packet.packet import Packet
from mercury.fog_model.common.packet.network import NetworkPacket


class PhysicalPacket(Packet):
    """
    Packet of a physical link (point-to-point)
    :param str node_from:
    :param str node_to:
    :param float power:
    :param float frequency:
    :param float bandwidth:
    :param float spectral_efficiency:
    :param NetworkPacket data: network packet to be encapsulated
    """
    def __init__(self, node_from, node_to, power, bandwidth, spectral_efficiency, header=0, data=None):
        super().__init__(header, data)
        self.node_from = node_from
        self.node_to = node_to
        self.power = power
        self.bandwidth = bandwidth
        self.spectral_efficiency = spectral_efficiency

    def compute_size(self):
        res = self.header
        if self.data:
            res += self.data.compute_size()
        return res
