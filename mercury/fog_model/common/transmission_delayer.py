from abc import ABC
from collections import deque
from xdevs import INFINITY
from . import Stateless


class TransmissionDelayer(Stateless, ABC):
    def __init__(self, name):

        super().__init__(name=name)
        self.time_events = dict()
        self.scheduled_msg = dict()
        self.lookup_table = dict()

    def add_msg_to_buffer(self, out_port, msg, channel, size, bandwidth, spectral_efficiency):
        try:
            delay = size / (bandwidth * spectral_efficiency)
        except ZeroDivisionError:
            delay = 0
        if delay == 0 and channel not in self.time_events:
            self.add_msg_to_queue(out_port, msg)
        else:
            baseline = self._clock
            if channel in self.time_events and self.time_events[channel]:
                baseline = self.time_events[channel][-1]
            event = baseline + delay
            if channel not in self.time_events:
                self.time_events[channel] = deque()
            if event not in self.time_events[channel]:
                self.time_events[channel].append(event)
                if event not in self.scheduled_msg:
                    self.scheduled_msg[event] = list()
            self.scheduled_msg[event].append((out_port, msg))

    def process_internal_messages(self):
        """Processes internal messages"""
        channels_to_remove = list()
        for channel, time_events in self.time_events.items():
            if self._clock in time_events:
                time_events.remove(self._clock)
                if not time_events:
                    channels_to_remove.append(channel)
        for channel in channels_to_remove:
            self.time_events.pop(channel)
        jobs = self.scheduled_msg.pop(self._clock, None)
        if jobs is not None:
            for out_port, msg in jobs:
                self.add_msg_to_queue(out_port, msg)

    def get_next_timeout(self):
        res = INFINITY
        if self._message_queue:
            return 0
        for channel, event in self.time_events.items():
            if event and event[0] < res:
                res = event[0]
        return res - self._clock
