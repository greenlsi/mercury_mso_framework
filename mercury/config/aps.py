from typing import Tuple, Optional
from .network import TransceiverConfig, NodeConfig


class AccessPointConfig:
    def __init__(self, ap_id: str, ap_location: Tuple[float, ...], xh_trx: Optional[TransceiverConfig] = None,
                 rad_trx: Optional[TransceiverConfig] = None):
        """
        Access Point Configuration.
        :param str ap_id: ID of the Access Point
        :param tuple ap_location: Access Point coordinates <x, y> (in meters)
        :param xh_trx: Transceiver for crosshaul communications
        :param rad_trx: Transceiver for Radio communications
        """
        self.ap_id: str = ap_id
        self.ap_location: Tuple[float, ...] = ap_location
        self.xh_node: NodeConfig = NodeConfig(ap_id, xh_trx, node_mobility_config={'initial_val': ap_location})
        self.radio_node: NodeConfig = NodeConfig(ap_id, rad_trx, node_mobility_config={'initial_val': ap_location})
