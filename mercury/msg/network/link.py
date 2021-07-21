from typing import Optional, Set, Dict, Tuple, Any


class NetworkLinkReport:
    def __init__(self, node_from: str, node_to: str, bandwidth: float, frequency: float,
                 power: Optional[float], noise: Optional[float], mcs: Tuple[Any, float]):
        """
        Message containing the report of the state of a link between two nodes.
        :param node_from: sender node.
        :param node_to: receiver node.
        :param bandwidth: bandwidth (in Hz) of the link that interconnects both nodes.
        :param frequency: carrier frequency (in Hz) of the link that interconnects both nodes.
        :param power: received power (in W) of the link.
        :param noise: noise power (in W) added by the link.
        :param mcs: Modulation and Codification Scheme. It is a tuple (MCS_ID, Spectral efficiency (in bps/Hz)).
        """
        self.node_from: str = node_from
        self.node_to: str = node_to
        self.bandwidth: float = bandwidth
        self.frequency: float = frequency
        self.power: Optional[float] = power
        self.noise: Optional[float] = noise
        self.mcs_id: Any = mcs[0]
        self.spectral_efficiency: float = mcs[1]

    @property
    def rate(self) -> float:
        return self.bandwidth * self.spectral_efficiency


class EnableChannels:
    def __init__(self, master_node: str, slave_nodes: Optional[Set[str]] = None):
        """
        Message of shared networks to enable/disable network channels.
        :param master_node: master node.
        :param slave_nodes: set of slave nodes that have their channel enabled.
        """
        self.master_node: str = master_node
        self.slave_nodes: Set[str] = set() if slave_nodes is None else slave_nodes


class ChannelShare:
    def __init__(self, master_node: str, slave_nodes: Dict[str, float]):
        """
        Message of shared networks to establish the channel resources share between slave nodes.
        :param master_node: master node.
        :param slave_nodes: dictionary {slave node: channel resources share (from 0 to 1)}
        """
        self.master_node: str = master_node
        self.slave_nodes: Dict[str, float] = slave_nodes
