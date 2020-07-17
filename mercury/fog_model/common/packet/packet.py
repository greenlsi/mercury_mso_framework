class Packet:
    """
    Basic class for defining a packet
    :param header: size (in bits) of the data service_header
    :param data: data included in the packet. Its type depend on the implementation.
    :param packet_id: Packet Identifier number
    """
    def __init__(self, header: int = 0, data=None, packet_id: int = None):
        self.header = header
        self.data = data
        self.packet_id = packet_id

    @property
    def size(self):
        return self.header if self.data is None else self.header + self.data.size


class ApplicationPacket(Packet):
    """
    Application packet.
    :param int header: size (in bits) of the data service_header
    :param int data: size (in bits) of the data encapsulated in this message
    :param packet_id: Packet Identifier number
    """
    def __init__(self, header: int = 0, data: int = 0, packet_id: int = None):
        super().__init__(header, data, packet_id)

    @property
    def size(self):
        return self.header + self.data


class NetworkPacketConfiguration:
    """
    Configuration of packets of the network layer
    :param header: size (in bits) of the header of network packets
    """
    def __init__(self, header: int = 0):
        self.header = header


class NetworkPacket(Packet):
    """
    Network layer-based data (end-to-end logical addressing)
    :param node_from: node that sent the data
    :param node_to: node that is the receiver of the data
    :param data: application packet to be encapsulated
    :param packet_id: Packet Identifier number
    """
    def __init__(self, node_from: str, node_to: str, header: int = 0, data: ApplicationPacket = None,
                 packet_id: int = None):
        super().__init__(header, data, packet_id)
        self.node_from = node_from
        self.node_to = node_to


class PhysicalPacket(Packet):
    def __init__(self, node_from: str, node_to: str, header: int = 0, data: NetworkPacket = None, packet_id: int = None):
        """

        :param node_from: node that sent the data
        :param node_to: node that is the receiver of the data
        :param header: size (in bits) of the header of the packet
        :param data:
        :param packet_id:
        """
        super().__init__(header, data, packet_id)
        self.node_from = node_from
        self.node_to = node_to
        self.power = None
        self.bandwidth = None
        self.mcs = None
        self.frequency = None

        self.noise = None  # Noise of the message
        self.n_hops = 0  # Number of hops in the net

    @property
    def snr(self):
        return self.power if self.noise is None else self.power - self.noise
