from math import ceil
from xdevs.models import Port
from ...common.stateless import Stateless, PHASE_IDLE, INFINITY
from ...common.packet.application.ran.ran_access import PrimarySynchronizationSignal
from ...common.packet.application.ran import RadioAccessNetworkConfiguration
from ...common.mobility import NewLocation


class SignalingBroadcast(Stateless):
    """
    Create an instance of AP service broadcast module.
    :param str name: Name of the module
    :param str ap_id: ID of the AP
    :param RadioAccessNetworkConfiguration rac_config: Radio Access Control configuration
    """
    def __init__(self, name, ap_id, rac_config):

        super().__init__(name=name)
        self.ap_id = ap_id
        self.pss_period = rac_config.pss_period
        self.header = rac_config.header

        self.input_new_ue_location = Port(NewLocation, name + '_input_new_ue_location')
        self.output_pss = Port(PrimarySynchronizationSignal, name + '_output_pss')
        self.add_in_port(self.input_new_ue_location)
        self.add_out_port(self.output_pss)

    def _check_in_ports(self):
        next_timeout = INFINITY
        if self.input_new_ue_location:
            next_timeout = self._next_sigma()
        return PHASE_IDLE, next_timeout

    def process_internal_messages(self):
        self.add_msg_to_queue(self.output_pss, PrimarySynchronizationSignal(ap_id=self.ap_id, header=self.header))

    def _next_sigma(self):
        try:
            return ceil(self._clock / self.pss_period) * self.pss_period - self._clock
        except ZeroDivisionError:
            return 0

    def check_in_ports(self):
        pass
