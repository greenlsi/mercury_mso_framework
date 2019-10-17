from .radio import RadioAntennaConfig
from .crosshaul import CrosshaulTransceiverConfiguration


class AccessPointConfiguration:
    def __init__(self, ap_id, ap_location, radio_antenna_config, crosshaul_transceiver_config):
        """
        Access Point Configuration

        :param str ap_id: ID of the Access Point
        :param tuple ap_location: Access Point coordinates <x, y> (in meters)
        :param RadioAntennaConfig radio_antenna_config: radio antenna configuration
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver_config: crosshaul_config transceiver configuration
        """
        self.ap_id = ap_id
        self.ap_location = ap_location
        self.radio_antenna_config = radio_antenna_config
        self.crosshaul_transceiver_config = crosshaul_transceiver_config
