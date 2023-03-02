from __future__ import annotations


class NetworkLinkReport:
    def __init__(self, node_from: str, node_to: str, bandwidth: float, frequency: float,
                 power: float | None, noise: float | None, eff: float | None):
        """
        Message containing the report of the state of a link between two nodes.
        :param node_from: sender node.
        :param node_to: receiver node.
        :param bandwidth: bandwidth (in Hz) of the link that interconnects both nodes.
        :param frequency: carrier frequency (in Hz) of the link that interconnects both nodes.
        :param power: received power (in W) of the link.
        :param noise: noise power (in W) added by the link.
        :param eff: Spectral efficiency (in bps/Hz) of the link.
        """
        self.node_from: str = node_from
        self.node_to: str = node_to
        self.bandwidth: float | None = bandwidth
        self.frequency: float | None = frequency
        self.power: float | None = power
        self.noise: float | None = noise
        self.eff: float | None = eff

    @property
    def rate(self) -> float | None:
        if self.eff is not None:
            return self.bandwidth * self.eff

    @property
    def snr(self) -> float | None:
        return self.power if self.noise is None else self.power - self.noise


class ChannelShare:
    def __init__(self, master_node: str, slave_nodes: list[str]):
        """
        Message of shared networks to establish the channel resources share between slave nodes.
        :param master_node: master node.
        :param slave_nodes: dictionary {slave node: channel resources share (from 0 to 1)}
        """
        self.master_node: str = master_node
        self.slave_nodes: list[str] = slave_nodes


class NewNodeLocation:
    def __init__(self, node_id: str, location: tuple[float, ...]):
        """
        Message containing the new location of a node.
        :param node_id: ID of the node that changed
        :param location: new location of the node
        """
        self.node_id: str = node_id
        self.location: tuple[float, ...] = location
