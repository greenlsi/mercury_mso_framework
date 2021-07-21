from typing import Tuple, Dict, Optional, Any, ClassVar
from .network import NodeConfig, TransceiverConfig


class CoreConfig:

    CORE_ID: ClassVar[str] = 'core'

    def __init__(self, core_location: Tuple[float, ...], xh_trx: Optional[TransceiverConfig] = None,
                 sdnc_name: str = 'closest', sdnc_config: Optional[Dict[str, Any]] = None):
        """
        Core Layer Configuration Parameters.
        :param core_location: Location of the Core network functions.
        :param xh_trx:  Crosshaul Transceiver of the Core Network Functions.
        :param sdnc_name:  Name of the SDNC strategy to be implemented.
        :param sdnc_config:  Any required additional configuration parameters for the SDNC strategy.
        """
        self.node: NodeConfig = NodeConfig(CoreConfig.CORE_ID, xh_trx,
                                           node_mobility_config={'initial_val': core_location})
        self.sdnc_name: str = sdnc_name
        self.sdnc_config: Dict[str, Any] = dict() if sdnc_config is None else sdnc_config
