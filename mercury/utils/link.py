from math import log2
from mercury.config.network import LinkConfig, NetworkNodeConfig
from mercury.msg.packet import PhysicalPacket
from mercury.msg.network import NetworkLinkReport
from typing import List, Optional, Tuple
from .maths import euclidean_distance, from_natural_to_db, from_db_to_natural, from_dbm_to_watt


class Link:
    def __init__(self, node_from: NetworkNodeConfig, node_to: NetworkNodeConfig, link_conf: LinkConfig):
        """

        :param node_from:
        :param node_to:
        :param link_conf:
        """
        from mercury.plugin import AbstractFactory as Factory, Noise, Attenuation
        self.link_att: Optional[Attenuation] = None
        if link_conf.att_id is not None:
            self.link_att = Factory.create_network_attenuation(link_conf.att_id, **link_conf.att_config)
        self.link_noise: Optional[Noise] = None
        if link_conf.noise_id is not None:
            self.link_noise = Factory.create_network_noise(link_conf.noise_id, **link_conf.noise_config)
        self.link_bw: float = link_conf.bandwidth
        self.link_share: float = 1
        self.link_freq: float = link_conf.carrier_freq
        self.link_prop_speed: float = link_conf.prop_speed
        self.link_penalty_delay: float = link_conf.penalty_delay
        self.link_loss_prob: float = link_conf.loss_prob

        self.node_from_id: str = node_from.node_id
        self.node_from_location: Tuple[float, ...] = node_from.location
        tx_conf = node_from.trx
        self.tx_power: float = from_dbm_to_watt(tx_conf.tx_power)
        self.tx_gain: float = from_db_to_natural(tx_conf.gain)
        self.tx_psd: float = self.tx_power if self.link_bw == 0 else self.tx_power / self.link_bw
        self.mcs_list: List[float] = list() if tx_conf.mcs_table is None else tx_conf.mcs_table
        self.mcs_list.sort()
        self.tx_noise: Optional[Noise] = None
        if tx_conf.noise_id is not None:
            self.tx_noise = Factory.create_network_noise(tx_conf.noise_id, **tx_conf.noise_config)

        self.node_to_id: str = node_to.node_id
        self.node_to_location: Tuple[float, ...] = node_to.location
        rx_conf = node_to.trx
        self.rx_gain: float = from_db_to_natural(rx_conf.gain)
        self.rx_noise: Optional[Noise] = None
        if rx_conf.noise_id is not None:
            self.rx_noise = Factory.create_network_noise(rx_conf.noise_id, **rx_conf.noise_config)

        self.lut_tier_1: bool = False
        self.link_distance: Optional[float] = None  # in meters
        self.link_prop_delay: Optional[float] = None  # in seconds
        self.link_power_density: Optional[float] = None  # in Watts / Hz
        self.link_noise_density: Optional[float] = None  # in Watts / Hz
        self.link_snr: Optional[float] = None  # in Watts / Watts
        self.link_mcs: Optional[float] = None  # in bps / Hz
        self.lut_tier_2: bool = False
        self.link_power: Optional[float] = None  # in Watts
        self.link_noise_power: Optional[float] = None  # in Watts

    @property
    def bandwidth(self) -> float:
        return self.link_bw * self.link_share

    @property
    def efficiency(self) -> float:
        self._fill_luts()
        return 0 if self.link_mcs is None else self.link_mcs

    @property
    def distance(self) -> float:
        self._fill_luts()
        return self.link_distance

    @property
    def tx_speed(self) -> float:
        return self.bandwidth * self.efficiency

    @property
    def prop_delay(self) -> float:
        self._fill_luts()
        return self.link_prop_delay

    @property
    def power(self) -> float:
        self._fill_luts()
        return self.link_power

    @property
    def noise(self) -> float:
        self._fill_luts()
        return self.link_noise_power

    @property
    def mcs(self) -> Optional[float]:
        self._fill_luts()
        return self.link_mcs

    @property
    def snr(self) -> Optional[float]:
        self._fill_luts()
        return from_natural_to_db(self.link_snr)

    @property
    def natural_snr(self) -> Optional[float]:
        self._fill_luts()
        return self.link_snr

    @property
    def hit(self) -> bool:
        return self.lut_tier_2 and self.lut_tier_1

    def generate_report(self) -> NetworkLinkReport:
        return NetworkLinkReport(self.node_from_id, self.node_to_id, self.bandwidth,
                                 self.link_freq, self.power, self.noise, self.mcs)

    def prepare_msg(self, msg: PhysicalPacket):
        msg.frequency = self.link_freq
        msg.bandwidth = self.bandwidth
        msg.power = self.power
        msg.noise = self.noise
        msg.mcs = self.mcs

    def set_new_location(self, node_id: str, new_location: Tuple[float, ...]):
        change = False
        if node_id == self.node_from_id:
            if new_location != self.node_from_location:
                change = True
                self.node_from_location = new_location
        elif node_id == self.node_to_id:
            if new_location != self.node_to_location:
                change = True
                self.node_to_location = new_location
        if change:
            self.lut_tier_1 = False
            self.lut_tier_2 = False

    def set_link_share(self, share: float):
        if 1 < share < 0:
            raise ValueError(f'Invalid link share {share}')
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
            return power_density / self.link_noise_density  # Signal-to-Noise Ratio
        elif self.link_power is not None:
            return self.link_power_density if self.link_power_density > 0 else self.link_power
        else:
            return 0

    def _link_best_mcs(self) -> Optional[float]:
        if self.link_snr > 0:
            c_by_b = log2(1 + self.link_snr)  # Maximum theoretical capacity of the link (Shannon-Hartley theorem)
            return max((eff for eff in self.mcs_list if eff <= c_by_b), default=c_by_b)
