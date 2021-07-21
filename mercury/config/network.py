from typing import Any, ClassVar, Dict, Optional, Tuple


class PacketConfig:
    """ Network Packet data and header configurations. """
    PHYS_RAD_HEADER: ClassVar[int] = 0
    PHYS_XH_HEADER: ClassVar[int] = 0

    NET_HEADER: ClassVar[int] = 0

    # TODO add session layer

    RAN_MGMT_HEADER: ClassVar[int] = 0

    EDGE_FED_MGMT_HEADER: ClassVar[int] = 0
    EDGE_FED_MGMT_CONTENT: ClassVar[int] = 0

    SRV_HEADERS: ClassVar[Dict[str, int]] = dict()
    SRV_CONTENTS: ClassVar[Dict[str, int]] = dict()


class LinkConfig:
    def __init__(self, bandwidth: float = 0, carrier_freq: float = 0, prop_speed: float = 0, penalty_delay: float = 0,
                 loss_prob: float = 0, att_name: Optional[str] = None, att_config: Optional[Dict[str, Any]] = None,
                 noise_name: Optional[str] = None, noise_config: Optional[Dict[str, Any]] = None):
        """
        Configuration of a communication link.
        :param bandwidth: Total available bandwidth of the link (in Hz)
        :param carrier_freq: Carrier Frequency used for transmitting messages (in Hz)
        :param prop_speed: Physical propagation speed of the link (in m/s)
        :param penalty_delay: Fixed delay to be applied to messages sent through the link (in s)
        :param loss_prob: Packet loss probability (0 if no loss occurs, 1 if all the packets are lost)
        :param att_name: Name of the attenuation function to be applied to messages sent through the link
        :param att_config: Attenuation function configuration parameters
        :param noise_name: Name of the attenuation function to be applied to messages sent through the link
        :param noise_config: Attenuation function configuration parameters
        """
        if bandwidth < 0:
            raise ValueError('Bandwidth must be greater than or equal to zero')
        if carrier_freq < 0:
            raise ValueError('Carrier frequency must be greater than or equal to zero')
        if prop_speed < 0:
            raise ValueError('Propagation speed must be greater than or equal to zero')
        if penalty_delay < 0:
            raise ValueError('Penalty delay must be greater than or equal to zero')

        self.bandwidth: float = bandwidth
        self.carrier_freq: float = carrier_freq
        self.prop_speed: float = prop_speed
        self.penalty_delay: float = penalty_delay
        self.loss_prob: float = loss_prob  # not implemented yet

        self.att_name: Optional[str] = att_name
        self.att_config: Dict[str, Any] = dict() if att_config is None else att_config

        self.noise_name: Optional[str] = noise_name
        self.noise_config: Dict[str, Any] = dict() if noise_config is None else noise_config


class TransceiverConfig:
    def __init__(self, tx_power: Optional[float] = None, gain: Optional[float] = 0,
                 noise_name: Optional[str] = None, noise_conf: Optional[Dict] = None,
                 default_eff: Optional[float] = 1, mcs_table: Optional[Dict[Any, float]] = None):
        """
        Transceiver configuration.
        :param tx_power: Transmitting power (in dBm)
        :param gain: Transmitting/receiving gain (in dB)
        :param noise_name: noise model name
        :param noise_conf: noise model configuration parameters
        :param default_eff: Default spectral efficiency in case no matching MCS
        :param mcs_table: Available Modulation and Codification Schemes. TODO if no table, use C/B. If C/B = 0 -> use default? set delay to 0?
        """
        self.tx_power: Optional[float] = tx_power
        self.gain: Optional[float] = gain
        self.noise_name: Optional[str] = noise_name
        self.noise_config = dict() if noise_conf is None else noise_conf
        self.default_eff: Optional[float] = default_eff
        self.mcs_table: Optional[Dict[Any, float]] = mcs_table


class NodeConfig:

    TRANSMITTER = 'tx'
    TRANSCEIVER = 'trx'
    RECEIVER = 'rx'

    def __init__(self, node_id: str, node_trx: Optional[TransceiverConfig] = None,
                 node_mobility_name: str = 'still', node_mobility_config: Optional[dict] = None):
        """
        Node configuration.
        :param node_id: ID of the node
        :param node_trx: Node transceiver configuration
        :param node_mobility_name: Node mobility model name
        :param node_mobility_config: Node mobility model configuration parameters
        """
        import mercury.plugin.factory as f

        self.node_id: str = node_id
        self.node_trx: Optional[TransceiverConfig] = node_trx

        if node_mobility_config is None:
            node_mobility_config = dict()
        self.node_mobility: f.NodeMobility = f.AbstractFactory.create_mobility(node_mobility_name,
                                                                               **node_mobility_config)
        self.initial_location = self.node_mobility.location

    def unpack(self) -> Tuple[str, Tuple[float, ...], Optional[TransceiverConfig]]:
        return self.node_id, self.initial_location, self.node_trx
