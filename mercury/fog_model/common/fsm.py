from collections import deque
from xdevs.models import Atomic


class FiniteStateMachine(Atomic):
    """
    Finite State Machine implementation for xDEVS
    :param list states: list of states
    :param dict int_table: {state: internal_action}. If no action is required, set internal_action_function to None
    :param dict ext_table: {state: external_action}. If no action is required, set external_action to None
    :param dict lambda_table: {state: output_action}. If no action is required, set output_action to None
    :param str initial_state: initial state of the FSM
    :param float initial_timeout: initial internal timeout of the FSM
    :param str name: Name of the stateless state machine xDEVS atomic module
    """
    def __init__(self, states, int_table, ext_table, lambda_table, initial_state, initial_timeout, name=None):
        self._clock = 0
        self._message_queue = deque()

        # Assert that all the possible states are included in internal, external and lambda tables
        for state in states:
            if state not in int_table:
                raise ValueError("State %s not included in internal table".format(state))
            if state not in ext_table:
                raise ValueError("State %s not included in external table".format(state))
            if state not in lambda_table:
                raise ValueError("State %s not included in lambda table".format(state))
        self.states = states

        # Assert that there are not invalid states in internal table
        for state in int_table:
            if state not in self.states:
                raise ValueError("State %s included in internal table is not valid".format(state))
        self.int_table = int_table

        # Assert that there are not invalid states in external table
        for state in int_table:
            if state not in self.states:
                raise ValueError("State %s included in external table is not valid".format(state))
        self.ext_table = ext_table

        # Assert that there are not invalid states in lambda table
        for state in int_table:
            if state not in self.states:
                raise ValueError("State %s included in lambda table is not valid".format(state))
        self.lambda_table = lambda_table

        # Assert that initial state is valid
        self._check_state(initial_state, initial_timeout)
        self._initial_state = initial_state
        self._initial_timeout = initial_timeout

        super().__init__(name)

    def deltint(self):
        """Clears job list and returns to idle"""
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
        self._clock += self.sigma
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

    def add_msg_to_queue(self, out_port, msg):
        """
        Adds message to be sent to the message queue
        :param Port out_port: output port for sending the message
        :param msg: Message to be sent via the output port
        :raises: :class:`ValueError`: Port is not an output port of this xDEVS module
        :raises: :class:`TypeError`: Message is not instance of output port type
        """
        if out_port not in self.out_ports:
            raise ValueError("Port %s is not an output port of module %s".format(str(out_port), self.name))
        if not isinstance(msg, out_port.p_type):
            raise TypeError("Value type is %s (%s expected)" % (type(msg).__name__, out_port.p_type.__name__))
        self._message_queue.append((out_port, msg))

    def msg_queue_empty(self):
        """Checks if message queue is empty"""
        return not self._message_queue

    def _check_state(self, state, timeout):
        """Checks that a given new state is valid"""
        if state not in self.states:
            raise ValueError("State %s is not valid".format(state))
        if timeout < 0:
            raise ValueError("Timeout must be greater or equal to 0")
