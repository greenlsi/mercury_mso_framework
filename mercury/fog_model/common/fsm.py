from abc import ABC, abstractmethod
from typing import List, Dict, Any
from collections import deque
from xdevs.models import Atomic, INFINITY


class FiniteStateMachine(Atomic):
    def __init__(self, states: List[str], int_table: Dict[str, Any], ext_table: Dict[str, Any],
                 lambda_table: Dict[str, Any], initial_state: str, initial_timeout: float, name: str = None):
        """
        Finite State Machine implementation for xDEVS
        :param states: list of states
        :param int_table: {state: internal_action}. If no action is required, set internal_action_function to None
        :param ext_table: {state: external_action}. If no action is required, set external_action to None
        :param lambda_table: {state: output_action}. If no action is required, set output_action to None
        :param initial_state: initial state of the FSM
        :param initial_timeout: initial internal timeout of the FSM
        :param name: Name of the finite state machine xDEVS atomic module
        """
        self._clock = 0
        self._message_queue = deque()

        # Assert that all the possible states are included in internal, external and lambda tables
        for state in states:
            if state not in int_table:
                raise ValueError("State {} not included in internal table".format(state))
            if state not in ext_table:
                raise ValueError("State {} not included in external table".format(state))
            if state not in lambda_table:
                raise ValueError("State {} not included in lambda table".format(state))
        self.states = states

        # Assert that there are not invalid states in internal table
        for state in int_table:
            if state not in self.states:
                raise ValueError("State {} included in internal table is not valid".format(state))
        self.int_table = int_table

        # Assert that there are not invalid states in external table
        for state in int_table:
            if state not in self.states:
                raise ValueError("State {} included in external table is not valid".format(state))
        self.ext_table = ext_table

        # Assert that there are not invalid states in lambda table
        for state in int_table:
            if state not in self.states:
                raise ValueError("State {} included in lambda table is not valid".format(state))
        self.lambda_table = lambda_table

        # Assert that initial state is valid
        self._check_state(initial_state, initial_timeout)
        self._initial_state = initial_state
        self._initial_timeout = initial_timeout

        super().__init__(name)

    def deltint(self):
        """Clears job list and returns to idle"""
        # self._clock += self.sigma  TODO habilitar esto
        self.clear_state()
        self._message_queue.clear()
        next_state, timeout = self.int_table[self.phase]()
        self._check_state(next_state, timeout)
        self.hold_in(next_state, timeout)

    def deltext(self, e):
        """Checks input ports and processes new received messages"""
        self._clock += e
        if self.ext_table[self.phase] is not None:
            try:
                next_state, timeout = self.ext_table[self.phase]()
                self._check_state(next_state, timeout)
                self.hold_in(next_state, timeout)
            # If nothing is returned, we keep the same phase and reduce the sigma by the elapsed time
            except TypeError:
                self.hold_in(self.phase, max(self.sigma - e, 0))

    def lambdaf(self):
        """Every message in job list is forwarded to its respective output port"""
        self._clock += self.sigma  # TODO deshabilitar esto
        if self.lambda_table[self.phase] is not None:
            self.lambda_table[self.phase]()
        for port, msg in self._message_queue:
            port.add(msg)

    def initialize(self):
        """Initializes the FSM"""
        self.hold_in(self._initial_state, self._initial_timeout)

    def exit(self):
        """Not used"""
        pass

    def clear_state(self):
        """Clears internal buffers that is part of the atomic model's state. By default, it does nothing."""
        pass

    def add_msg_to_queue(self, out_port, msg):
        """
        Adds message to be sent to the message queue
        :param Port out_port: output port for sending the message
        :param msg: Message to be sent via the output port
        :raises: :class:`ValueError`: Port is not an output port of this xDEVS module
        :raises: :class:`TypeError`: Message is not instance of output port type
        """
        if out_port not in self.out_ports:
            raise ValueError("Port {} is not an output port of module {}".format(str(out_port), self.name))
        if not isinstance(msg, out_port.p_type):
            raise TypeError("Value type is {} ({} expected)".format(type(msg).__name__, out_port.p_type.__name__))
        self._message_queue.append((out_port, msg))

    def msg_queue_empty(self):
        """Checks if message queue is empty"""
        return not self._message_queue

    def _check_state(self, state, timeout):
        """Checks that a given new state is valid"""
        if state not in self.states:
            raise ValueError("State {} is not valid".format(state))
        if timeout < 0:
            raise ValueError("Timeout must be greater or equal to 0")


class Stateless(FiniteStateMachine, ABC):

    PHASE_IDLE = 'idle'

    def __init__(self, initial_timeout: float = INFINITY, name: str = None):
        """
        Stateless State Machine implementation for xDEVS
        :param initial_timeout: Initial timeout for xDEVS module
        :param name: Name of the stateless state machine xDEVS atomic module
        """
        states = [self.PHASE_IDLE]
        int_table = {self.PHASE_IDLE: self._internal_idle}
        ext_table = {self.PHASE_IDLE: self._check_in_ports}
        lambda_table = {self.PHASE_IDLE: self.process_internal_messages}
        super().__init__(states, int_table, ext_table, lambda_table, self.PHASE_IDLE, initial_timeout, name)

    def _internal_idle(self):
        next_timeout = self.get_next_timeout()
        return self.PHASE_IDLE, next_timeout

    def _check_in_ports(self):
        self.check_in_ports()
        next_timeout = self.get_next_timeout()
        return self.PHASE_IDLE, next_timeout

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
