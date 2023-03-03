from abc import ABC, abstractmethod
from collections import deque
from typing import Callable, Dict, List, Optional
from xdevs.models import Atomic, Port, T


class ExtendedAtomic(Atomic, ABC):
    def __init__(self, name: Optional[str] = None):
        super().__init__(name)
        self._clock = 0
        self._message_queue = deque()

    def deltint(self):
        """Clears job list and returns to idle"""
        self._clock += self.sigma
        self._message_queue.clear()
        self.deltint_extension()

    def deltext(self, e):
        """Checks input ports and processes new received messages"""
        self._clock += e
        self.deltext_extension(e)

    def lambdaf(self):
        """Every message in job list is forwarded to its respective output port"""
        self.lambdaf_extension()
        for port, msg in self._message_queue:
            port.add(msg)

    @abstractmethod
    def deltint_extension(self):
        pass

    @abstractmethod
    def deltext_extension(self, e):
        pass

    @abstractmethod
    def lambdaf_extension(self):
        pass

    def add_msg_to_queue(self, out_port: Port[T], msg: T):
        """
        Adds message to be sent to the message queue
        :param Port out_port: output port for sending the message
        :param msg: Message to be sent via the output port
        :raises: :class:`ValueError`: Port is not an output port of this xDEVS module
        """
        if out_port not in self.out_ports:
            raise ValueError(f'port {str(out_port)} is not an output port of module {self.name}')
        self._message_queue.append((out_port, msg))

    def msg_queue_empty(self):
        """Checks if message queue is empty"""
        return not self._message_queue

# TODO remove
class FiniteStateMachine(ExtendedAtomic):
    def __init__(self, states: List[str], int_table: Dict[str, Callable],
                 ext_table: Dict[str, Callable], lambda_table: Dict[str, Callable],
                 initial_state: str, initial_timeout: float, name: Optional[str] = None):
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
        super().__init__(name)

        # Assert that all the possible states are included in internal, external and lambda tables
        for state in states:
            if state not in int_table:
                raise ValueError(f'State {state} not included in internal table')
            if state not in ext_table:
                raise ValueError(f'State {state} not included in external table')
            if state not in lambda_table:
                raise ValueError(f'State {state} not included in lambda table')
        self.states = states

        # Assert that there are not invalid states in internal table
        for state in int_table:
            if state not in self.states:
                raise ValueError(f'State {state} included in internal table is not valid')
        self.int_table = int_table

        # Assert that there are not invalid states in external table
        for state in int_table:
            if state not in self.states:
                raise ValueError(f'State {state} included in external table is not valid')
        self.ext_table = ext_table

        # Assert that there are not invalid states in lambda table
        for state in int_table:
            if state not in self.states:
                raise ValueError(f'State {state} included in lambda table is not valid')
        self.lambda_table = lambda_table

        # Assert that initial state is valid
        self._check_state(initial_state, initial_timeout)
        self._initial_state = initial_state
        self._initial_timeout = initial_timeout

        super().__init__(name)

    def deltint_extension(self):
        """Clears job list and returns to idle"""
        self.clear_state()
        next_state, timeout = self.int_table[self.phase]()
        self._check_state(next_state, timeout)
        self.hold_in(next_state, timeout)

    def deltext_extension(self, e):
        """Checks input ports and processes new received messages"""
        if self.ext_table[self.phase] is not None:
            try:
                next_state, timeout = self.ext_table[self.phase]()
                self._check_state(next_state, timeout)
                self.hold_in(next_state, timeout)
            # If nothing is returned, we keep the same phase and reduce the sigma by the elapsed time
            except TypeError:
                self.continuef(e)

    def lambdaf_extension(self):
        """Every message in job list is forwarded to its respective output port"""
        self._clock += self.sigma  # TODO disable this
        if self.lambda_table[self.phase] is not None:
            self.lambda_table[self.phase]()
        self._clock -= self.sigma  # TODO disable this

    def initialize(self):
        """Initializes the FSM"""
        self.hold_in(self._initial_state, self._initial_timeout)

    def exit(self):
        pass

    def clear_state(self):
        """Clears internal buffers that are part of the atomic model's state. By default, it does nothing."""
        pass

    def _check_state(self, state, timeout):
        """Checks that a given new state is valid"""
        if state not in self.states:
            raise ValueError(f'State {state} is not valid')
        if timeout < 0:
            raise ValueError('Timeout must be greater or equal to 0')