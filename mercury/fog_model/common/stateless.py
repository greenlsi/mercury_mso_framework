from abc import ABC, abstractmethod
from .fsm import FiniteStateMachine
from xdevs.models import INFINITY


PHASE_IDLE = 'idle'


class Stateless(FiniteStateMachine, ABC):
    """
    Stateless State Machine implementation for xDEVS
    :param str name: Name of the stateless state machine xDEVS atomic module
    """
    def __init__(self, initial_timeout=INFINITY, name=None):
        states = [PHASE_IDLE]
        int_table = {PHASE_IDLE: self._internal_idle}
        ext_table = {PHASE_IDLE: self._check_in_ports}
        lambda_table = {PHASE_IDLE: self.process_internal_messages}
        super().__init__(states, int_table, ext_table, lambda_table, PHASE_IDLE, initial_timeout, name)

    def _internal_idle(self):
        next_timeout = self.get_next_timeout()
        return PHASE_IDLE, next_timeout

    def _check_in_ports(self):
        self.check_in_ports()
        next_timeout = self.get_next_timeout()
        return PHASE_IDLE, next_timeout

    @abstractmethod
    def check_in_ports(self):
        """Processes incoming messages"""
        pass

    @abstractmethod
    def process_internal_messages(self):
        """Processes internal messages"""
        pass

    def get_next_timeout(self):
        return 0 if self._message_queue else INFINITY
