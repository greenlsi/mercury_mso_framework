from abc import ABC, abstractmethod
from scipy.constants import k
from math import log2, log10
from .packet.physical import PhysicalPacket
from collections import OrderedDict
from .network import Attenuator, FreeSpaceLossAttenuator


UL_MCS_TABLE = {
    0: 0.2344,
    1: 0.3770,
    2: 0.6016,
    3: 0.8770,
    4: 1.1758,
    5: 1.4766,
    6: 1.6953,
    7: 1.9141,
    8: 2.1602,
    9: 2.4063,
    10: 2.5703,
    11: 2.7305,
    12: 3.0293,
    13: 3.3223,
    14: 3.6094,
    15: 3.9023,
    16: 4.2129,
    17: 4.5234,
    18: 4.8164,
    19: 5.1152,
    20: 5.3320,
    21: 5.5547,
    22: 5.8906,
    23: 6.2266,
    24: 6.5703,
    25: 6.9141,
    26: 7.1602,
    27: 7.4063
}

DL_MCS_TABLE = {
    0: 0.2344,
    1: 0.3066,
    2: 0.3770,
    3: 0.4902,
    4: 0.6016,
    5: 0.7402,
    6: 0.8770,
    7: 1.0273,
    8: 1.1758,
    9: 1.3262,
    10: 1.3281,
    11: 1.4766,
    12: 1.6953,
    13: 1.9141,
    14: 2.1602,
    15: 2.4063,
    16: 2.5703,
    17: 2.5664,
    18: 2.7305,
    19: 3.0293,
    20: 3.3223,
    21: 3.6094,
    22: 3.9023,
    23: 4.2129,
    24: 4.5234,
    25: 4.8164,
    26: 5.1152,
    27: 5.3320,
    28: 5.5547
}


class RadioConfiguration:
    """
    Radio network configuration
    :param float frequency: carrier frequency for physical channels
    :param float bandwidth: channel bandwidth (in Hz)
    :param FrequencyDivisionStrategy division_strategy: Frequency division strategy
    :param float prop_speed: propagation speed (in m/s)
    :param float penalty_delay: penalty delay (in seconds)
    :param Attenuator attenuator: attenuator function
    :param int header: physical messages service_header size
    :param dict ul_mcs: Modulation and codification Scheme table for uplink
    :param dict dl_mcs: Modulation and codification Scheme table for downlink
    """
    def __init__(self, frequency=33e9, bandwidth=100e6, division_strategy=None, prop_speed=0, penalty_delay=0,
                 attenuator=None, header=0, ul_mcs=None, dl_mcs=None):
        self.frequency = frequency
        self.bandwidth = bandwidth
        if division_strategy is None:
            division_strategy = EqualFrequencyDivisionStrategy
        self.division_strategy = division_strategy()
        self.prop_speed = prop_speed
        self.penalty_delay = penalty_delay
        if attenuator is None:
            attenuator = FreeSpaceLossAttenuator
        self.attenuator = attenuator()
        self.header = header

        if ul_mcs is None:
            ul_mcs = UL_MCS_TABLE
        ul_mcs = [(i, s) for i, s in ul_mcs.items()]
        ul_mcs.sort(key=lambda x: x[1])
        self.ul_mcs_list = ul_mcs

        if dl_mcs is None:
            dl_mcs = DL_MCS_TABLE
        dl_mcs = [(i, s) for i, s in dl_mcs.items()]
        dl_mcs.sort(key=lambda x: x[1])
        self.dl_mcs_list = dl_mcs


class FrequencyDivisionStrategy(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def bandwidth_share(self, connected_ues_efficiency_dict):
        pass


class EqualFrequencyDivisionStrategy(FrequencyDivisionStrategy):
    def bandwidth_share(self, connected_ues_efficiency_dict):
        n_ues = len(connected_ues_efficiency_dict)
        return {ue_id: 1/n_ues for ue_id in connected_ues_efficiency_dict}


class ProportionalFrequencyDivisionStrategy(FrequencyDivisionStrategy):
    def bandwidth_share(self, connected_ues_efficiency_dict):
        if not connected_ues_efficiency_dict:
            return dict()
        inverse = 1 / sum([1 / eff for eff in connected_ues_efficiency_dict.values()])
        return {ue_id: inverse / eff for ue_id, eff in connected_ues_efficiency_dict.items()}


class RadioAntennaConfig:
    """
    Configuration of an standard radio antenna
    :param float power: antenna's transmitting power (in dBm)
    :param float gain: antenna's gain (in dB)
    :param list tx_mcs: list of available Modulation and Codification Schemes for transmission
    :param list rx_mcs: list of available Modulation and Codification Schemes for reception
    """
    def __init__(self, power, gain, tx_mcs, rx_mcs, temperature=300, sensitivity=None):
        self.power = power
        self.gain = gain
        self.tx_mcs = tx_mcs
        self.rx_mcs = rx_mcs
        self.temperature = temperature
        self.sensitivity = sensitivity


class RadioAntenna:
    """
    Radio antenna
    :param RadioAntennaConfig antenna_config: Radio antenna configuration
    """
    def __init__(self, antenna_config):
        self.power = antenna_config.power
        self.gain = antenna_config.gain
        self.tx_mcs = antenna_config.tx_mcs
        self.rx_mcs = antenna_config.rx_mcs
        self.temperature = antenna_config.temperature
        self.sensitivity = antenna_config.sensitivity
        self.max_length_lookup_tables = 50  # TODO
        self.snr_lookup_table = OrderedDict()
        self.rx_mcs_lookup_table = OrderedDict()

    def compute_snr(self, msg):
        """
        Computes the perceived Signal-to-Noise ratio perceived by the antenna
        :param PhysicalPacket msg: received message from radio interface
        :return snr: Signal-to-Noise Ratio of the received message (in dB)
        """
        rx_power = msg.power
        bandwidth = msg.bandwidth
        try:
            snr = self.snr_lookup_table[(rx_power, bandwidth)]
        except KeyError:
            signal = rx_power + self.gain
            # k: J/K; t: K; bandwidth: Hz -> compute noise (mW) and get noise in dBm (adding the power)
            try:
                noise = 10 * log10(k * self.temperature * bandwidth) + 30 + self.gain
            except ValueError:
                noise = 0
            snr = signal - noise
            self.snr_lookup_table[(rx_power, bandwidth)] = snr
            for _ in range(len(self.snr_lookup_table) - self.max_length_lookup_tables):
                self.snr_lookup_table.popitem(last=True)
        return snr

    def inject_power(self):
        return self.power + self.gain

    def select_best_rx_mcs(self, snr):
        try:
            rx_mcs = self.rx_mcs_lookup_table[snr]
        except KeyError:
            # 1. SNR -> C/B (Shannon's limit)
            c_by_b = log2(1 + 10 ** (snr / 10))
            # 2. Look for the greatest MCS index of the receiving MCS table that accomplishes Shannon's limit
            avaliable_mcs_index = [(mcs_index, eff) for mcs_index, eff in self.rx_mcs if eff <= c_by_b]
            avaliable_mcs_index.sort(reverse=True, key=lambda x: x[1])
            rx_mcs = avaliable_mcs_index[0]
            self.rx_mcs_lookup_table[snr] = rx_mcs
            for _ in range(len(self.rx_mcs_lookup_table) - self.max_length_lookup_tables):
                self.rx_mcs_lookup_table.popitem(last=True)
        return rx_mcs

    def get_tx_mcs(self, mcs_index):
        return mcs_index, self.tx_mcs[mcs_index][1]
