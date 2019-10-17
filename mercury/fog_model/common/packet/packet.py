class Packet:
    """
    Basic class for defining a packet
    :param int header: size (in bits) of the data service_header
    :param data: data included in the packet. Its type depend on the implementation.
    :param packet_id: ID of the  single message
    """
    def __init__(self, header=0, data=None):
        self.header = header
        self.data = data
