from math import ceil
from xdevs.models import Port, INFINITY, PHASE_PASSIVE
from mercury.config.radio import RadioAccessNetworkConfig
from mercury.msg.network.packet.app_layer.ran import PrimarySynchronizationSignal
from ...common import ExtendedAtomic
from ...network.network import NodeLocation


class SignalingBroadcast(ExtendedAtomic):
    def __init__(self, ap_id: str):
        """
        Create an instance of AP service broadcast module.
        :param ap_id: ID of the AP
        """
        super().__init__('aps_ap_{}_pss'.format(ap_id))
        self.ap_id = ap_id
        self.input_repeat = Port(str, 'input_repeat')
        self.input_new_location = Port(NodeLocation, 'input_new_location')
        self.output_pss = Port(PrimarySynchronizationSignal, 'output_pss')
        self.add_in_port(self.input_repeat)
        self.add_in_port(self.input_new_location)
        self.add_out_port(self.output_pss)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        for ue_id in self.input_repeat.values:
            self.add_msg_to_queue(self.output_pss, PrimarySynchronizationSignal(ap_id=self.ap_id, ue_id=ue_id))
        for location in self.input_new_location.values:
            self.add_msg_to_queue(self.output_pss, PrimarySynchronizationSignal(self.ap_id, location.node_id))

        next_timeout = INFINITY if self.msg_queue_empty() else self._next_sigma()
        self.hold_in(PHASE_PASSIVE, next_timeout)

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def process_internal_messages(self):
        pass

    def _next_sigma(self):
        pss_period = RadioAccessNetworkConfig.pss_period
        return 0 if pss_period == 0 else ceil(self._clock / pss_period) * pss_period - self._clock
