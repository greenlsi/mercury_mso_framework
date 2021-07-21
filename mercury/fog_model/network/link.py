from math import log2
from mercury.config.network import LinkConfig, NodeConfig
from mercury.plugin import AbstractFactory
from mercury.utils.maths import euclidean_distance, from_natural_to_db, from_db_to_natural, from_dbm_to_watt
from typing import Tuple, List, Any, Union


class Link:
    def __init__(self, node_from: NodeConfig, node_to: NodeConfig, link_conf: LinkConfig):
        """

        :param node_from:
        :param node_to:
        :param link_conf:
        """
        self.link_att = None
        if link_conf.att_name is not None:
            self.link_att = AbstractFactory.create_network_attenuation(link_conf.att_name, **link_conf.att_config)
        self.link_noise = None
        if link_conf.noise_name is not None:
            self.link_noise = AbstractFactory.create_network_noise(link_conf.noise_name, **link_conf.noise_config)
        self.link_bw = link_conf.bandwidth
        self.link_share = 1
        self.frequency = link_conf.carrier_freq
        self.link_prop_speed = link_conf.prop_speed
        self.link_penalty_delay = link_conf.penalty_delay
        self.link_loss_prob = link_conf.loss_prob

        self.node_from_id = node_from.node_id
        self.node_from_location = node_from.initial_location
        tx_conf = node_from.node_trx
        self.tx_power = from_dbm_to_watt(tx_conf.tx_power)
        self.tx_gain = from_db_to_natural(tx_conf.gain)
        self.tx_psd = self.tx_power if self.link_bw == 0 else self.tx_power / self.link_bw
        self.default_mcs = ('default', tx_conf.default_eff)
        self.mcs_table = tx_conf.mcs_table
        self.tx_noise = None
        if tx_conf.noise_name is not None:
            self.tx_noise = AbstractFactory.create_network_noise(tx_conf.noise_name, **tx_conf.noise_config)

        self.node_to_id = node_to.node_id
        self.node_to_location = node_to.initial_location
        rx_conf = node_to.node_trx
        self.rx_gain = from_db_to_natural(rx_conf.gain)
        self.rx_noise = None
        if rx_conf.noise_name is not None:
            self.rx_noise = AbstractFactory.create_network_noise(rx_conf.noise_name, **rx_conf.noise_config)

        self.lut_tier_1 = False
        self.link_distance = None  # in meters
        self.link_prop_delay = None  # in seconds
        self.link_power_density = None  # in Watts / Hz
        self.link_noise_density = None  # in Watts / Hz
        self.link_snr = None  # in Watts / Watts
        self.link_mcs = None  # (MCS ID, spectral efficiency)
        self.lut_tier_2 = False
        self.link_power = None  # in dBm
        self.link_noise_power = None  # in dBm

    @property
    def bandwidth(self):
        return self.link_bw * self.link_share

    @property
    def efficiency(self):
        self._fill_luts()
        return self.mcs[1]

    @property
    def distance(self):
        self._fill_luts()
        return self.link_distance

    @property
    def tx_speed(self):
        return self.bandwidth * self.efficiency

    @property
    def prop_delay(self):
        self._fill_luts()
        return self.link_prop_delay

    @property
    def power(self):
        self._fill_luts()
        return self.link_power

    @property
    def noise(self):
        self._fill_luts()
        return self.link_noise_power

    @property
    def mcs(self):
        self._fill_luts()
        return self.link_mcs

    @property
    def snr(self) -> Union[float, None]:
        self._fill_luts()
        return from_natural_to_db(self.link_snr)

    @property
    def hit(self) -> bool:
        return self.lut_tier_2 and self.lut_tier_1

    def set_new_location(self, node_id: str, new_location: Tuple[float, ...]):
        if node_id == self.node_from_id:
            self.node_from_location = new_location
        elif node_id == self.node_to_id:
            self.node_to_location = new_location
        self.lut_tier_1 = False
        self.lut_tier_2 = False

    def set_link_share(self, share: float):
        assert 0 <= share <= 1
        if share != self.link_share:
            self.link_share = share
            self.lut_tier_2 = False

    def _fill_luts(self):
        if not self.lut_tier_1:
            self.link_distance = euclidean_distance(self.node_from_location, self.node_to_location)
            self.link_prop_delay = self._link_prop_delay()
            self.link_power_density = self._link_power_density()
            self.link_noise_density = self._link_noise_density()
            self.link_snr = self._link_snr()
            self.link_mcs = self._link_best_mcs()
            self.lut_tier_1 = True
        if not self.lut_tier_2:
            self.link_power = self.link_power_density * self.bandwidth if self.link_bw > 0 else self.link_power_density
            self.link_noise_power = self.link_noise_density * self.bandwidth
            self.lut_tier_2 = True

    def _link_prop_delay(self) -> float:
        prop_delay = 0 if self.link_prop_speed == 0 else self.link_distance / self.link_prop_speed
        return prop_delay + self.link_penalty_delay

    def _gain_cascade(self) -> List[float]:
        """return gain cascade in W/W"""
        link_att = 1 if self.link_att is None else self.link_att.attenuation(self, self.link_distance)
        return [self.tx_gain, 1 / link_att, self.rx_gain]  # The link attenuates -> the gain is the inverse!

    def _noise_cascade(self, bandwidth: float = None):
        """return power generation in Watts"""
        if bandwidth is None:
            bandwidth = self.bandwidth
        noise_sources = [self.tx_noise, self.link_noise, self.rx_noise]
        return [0 if noise is None else noise.noise_watts(self, bandwidth) for noise in noise_sources]

    def _link_power_density(self) -> float:
        """return power density in receiver's side in Watts"""
        psd = self.tx_psd
        for gain in self._gain_cascade():
            psd *= gain
        return psd

    def _link_noise(self, bandwidth: float = None) -> float:
        """return noise received by receiver in Watts"""
        if bandwidth is None:
            bandwidth = self.bandwidth
        if bandwidth == 0 or self.link_bw == 0:
            return 0
        noise = 0
        for power, gain in zip(self._noise_cascade(bandwidth), self._gain_cascade()):
            noise = noise * gain + power
        return noise

    def _link_noise_density(self) -> float:
        return self._link_noise(1)

    def _link_snr(self) -> float:
        snr = 0
        if self.link_noise_density > 0:  # If noise is zero, we use default MCS
            power_density = self.link_power_density if self.link_power_density > 0 else self.link_power
            if power_density > 0:  # If power is zero, we use default MCS
                snr = power_density / self.link_noise_density  # Signal-to-Noise Ration
        return snr

    def _link_best_mcs(self) -> Tuple[Any, float]:
        eff = self.default_mcs
        if self.mcs_table is not None and self.link_snr > 0:
            c_by_b = log2(1 + self.link_snr)  # Maximum theoretical capacity of the link (Shannon-Hartley theorem)
            for mcs_name, mcs_eff in self.mcs_table.items():
                if eff[1] <= mcs_eff <= c_by_b:
                    eff = (mcs_name, mcs_eff)
        return eff
