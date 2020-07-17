from math import ceil
from xdevs.models import Port
from ...common.fsm import Stateless, INFINITY
from ...common.packet.apps.ran.ran_access import PrimarySynchronizationSignal
from ...common.packet.apps.ran import RadioAccessNetworkConfiguration


class SignalingBroadcast(Stateless):
    def __init__(self, name: str, ap_id: str, rac_config: RadioAccessNetworkConfiguration):
        """
        Create an instance of AP service broadcast module.
        :param name: Name of the module
        :param ap_id: ID of the AP
        :param rac_config: Radio Access Control configuration
        """
        super().__init__(name=name)
        self.ap_id = ap_id
        self.pss_period = rac_config.pss_period
        self.header = rac_config.header

        self.input_repeat = Port(str, 'input_repeat')
        self.output_pss = Port(PrimarySynchronizationSignal, 'output_pss')
        self.add_in_port(self.input_repeat)
        self.add_out_port(self.output_pss)

    def _check_in_ports(self):
        next_timeout = INFINITY
        for ue_id in self.input_repeat.values:
            self.add_msg_to_queue(self.output_pss, PrimarySynchronizationSignal(ap_id=self.ap_id, ue_id=ue_id,
                                                                                header=self.header))
        if self.input_repeat:
            next_timeout = self._next_sigma()
        return Stateless.PHASE_IDLE, next_timeout

    def process_internal_messages(self):
        # self.add_msg_to_queue(self.output_pss, PrimarySynchronizationSignal(ap_id=self.ap_id, header=self.header))
        pass

    def _next_sigma(self):
        if self.pss_period == 0:
            return 0
        else:
            return ceil(self._clock / self.pss_period) * self.pss_period - self._clock

    def check_in_ports(self):
        pass
