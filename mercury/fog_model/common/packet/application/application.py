from ..packet import Packet


class ApplicationPacket(Packet):
    """
    Application packet.
    :param int header: size (in bits) of the data service_header
    :param int data: size (in bits) of the data encapsulated in this message
    """
    def __init__(self, header=0, data=0, packet_id=None):
        super().__init__(header, data)
        self.packet_id = packet_id

    def compute_size(self):
        return self.header + self.data
