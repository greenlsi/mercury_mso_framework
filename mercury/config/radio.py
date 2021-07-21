from typing import Optional, ClassVar, Dict
from .network import PacketConfig, LinkConfig, TransceiverConfig


class RadioConfig:

    UL_MCS_TABLE_5G: ClassVar[Dict[int, float]] = {
        0: 0.2344, 1: 0.3770, 2: 0.6016, 3: 0.8770, 4: 1.1758, 5: 1.4766, 6: 1.6953, 7: 1.9141, 8: 2.1602, 9: 2.4063,
        10: 2.5703, 11: 2.7305, 12: 3.0293, 13: 3.3223, 14: 3.6094, 15: 3.9023, 16: 4.2129, 17: 4.5234, 18: 4.8164,
        19: 5.1152, 20: 5.3320, 21: 5.5547, 22: 5.8906, 23: 6.2266, 24: 6.5703, 25: 6.9141, 26: 7.1602, 27: 7.4063
    }

    DL_MCS_TABLE_5G: ClassVar[Dict[int, float]] = {
        0: 0.2344, 1: 0.3066, 2: 0.3770, 3: 0.4902, 4: 0.6016, 5: 0.7402, 6: 0.8770, 7: 1.0273, 8: 1.1758, 9: 1.3262,
        10: 1.3281, 11: 1.4766, 12: 1.6953, 13: 1.9141, 14: 2.1602, 15: 2.4063, 16: 2.5703, 17: 2.5664, 18: 2.7305,
        19: 3.0293, 20: 3.3223, 21: 3.6094, 22: 3.9023, 23: 4.2129, 24: 4.5234, 25: 4.8164, 26: 5.1152, 27: 5.3320,
        28: 5.5547
    }

    def __init__(self, base_dl_config: Optional[LinkConfig] = None, base_ul_config: Optional[LinkConfig] = None,
                 base_ap_antenna_config: Optional[TransceiverConfig] = None,
                 base_ue_antenna_config: Optional[TransceiverConfig] = None, channel_div_name: str = 'equal',
                 channel_div_config: Optional[dict] = None, header: int = 0):
        """
        Radio Network Layer Configuration.
        :param base_dl_config: Base downlink link configuration.
        :param base_ul_config: Base uplink link configuration.
        :param base_ap_antenna_config: Base antenna configuration of APs.
        :param base_ue_antenna_config: Base antenna configuration of UEs.
        :param channel_div_name: Channel division strategy name. By default, it is set to 'equal'.
        :param channel_div_config: Any additional configuration parameters for the channel division strategy.
        """
        # TODO review default values
        self.base_dl_config = LinkConfig(carrier_freq=33e9, att_name='fspl') if base_dl_config is None \
            else base_dl_config
        self.base_ul_config = LinkConfig(carrier_freq=33e9, att_name='fspl') if base_ul_config is None \
            else base_ul_config

        self.base_ap_antenna_config = TransceiverConfig(tx_power=50, mcs_table=self.DL_MCS_TABLE_5G) \
            if base_ap_antenna_config is None else base_ap_antenna_config
        self.base_ue_antenna_config = TransceiverConfig(tx_power=30, mcs_table=self.UL_MCS_TABLE_5G) \
            if base_ue_antenna_config is None else base_ue_antenna_config

        self.channel_div_name = channel_div_name
        self.channel_div_config = dict() if channel_div_config is None else channel_div_config

        PacketConfig.PHYS_RAD_HEADER = header


class RadioAccessNetworkConfig:
    """  Radio Access Network applications configuration. """
    pss_period: ClassVar[float] = 0
    rrc_period: ClassVar[float] = 0
    timeout: ClassVar[float] = 0.5
    bypass_amf: ClassVar[bool] = False
