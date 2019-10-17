from ..common.network import Attenuator, DummyAttenuator


class CrosshaulConfiguration:
    """
    Crosshaul layer configuration

    :param float prop_speed: Propagation speed (in m/s)
    :param float penalty_delay: Penalty delay (in s)
    :param float ul_frequency: Up Link carrier frequency
    :param float dl_frequency: Down Link carrier frequency
    :param Attenuator ul_attenuator: Up Link attenuator
    :param Attenuator dl_attenuator: Down Link attenuator
    :param int header: size (in bits) of the header of physical messages
    """
    def __init__(self, prop_speed, penalty_delay, ul_frequency, dl_frequency, ul_attenuator=None, dl_attenuator=None,
                 header=0):
        self.prop_speed = prop_speed
        self.penalty_delay = penalty_delay
        self.ul_frequency = ul_frequency
        self.dl_frequency = dl_frequency
        if ul_attenuator is None:
            ul_attenuator = DummyAttenuator
        self.ul_attenuator = ul_attenuator()
        if dl_attenuator is None:
            dl_attenuator = DummyAttenuator
        self.dl_attenuator = dl_attenuator()
        self.header = header


class CrosshaulTransceiverConfiguration:
    def __init__(self, power, bandwidth, spectral_efficiency):
        self.power = power
        self.bandwidth = bandwidth
        self.spectral_efficiency = spectral_efficiency

    def get(self):
        return self.power, self.bandwidth, self.spectral_efficiency
