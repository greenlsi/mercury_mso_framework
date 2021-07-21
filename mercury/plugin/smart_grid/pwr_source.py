from xdevs.models import Atomic, Port, INFINITY, PHASE_PASSIVE
from typing import Tuple
from abc import ABC, abstractmethod
from mercury.msg.smart_grid import PowerSourceReport
from mercury.utils.history_buffer import EventHistoryBuffer


class PowerSource(Atomic, ABC):
    def __init__(self, **kwargs):
        self.consumer_id = kwargs.get('consumer_id')
        self.source_id = kwargs.get('source_id')
        self.actual_power = 0
        self.eventual_power = 0
        self.next_timeout = INFINITY
        self._clock = 0

        super().__init__('smart_grid_consumer_{}'.format(self.consumer_id))

        self.output_power_report = Port(PowerSourceReport, 'output_power_report')
        self.add_out_port(self.output_power_report)

    def deltint(self):
        self._clock += self.sigma
        self.actual_power = self.eventual_power
        self.eventual_power, self.next_timeout = self.schedule_next_power()
        self.hold_in(PHASE_PASSIVE, self.next_timeout)

    def deltext(self, e):
        self._clock += e
        self.next_timeout -= e
        self.hold_in(PHASE_PASSIVE, self.next_timeout)

    def lambdaf(self):
        self.output_power_report.add(PowerSourceReport(self.consumer_id, self.source_id, self.eventual_power))

    def initialize(self):
        self.hold_in(PHASE_PASSIVE, 0)

    def exit(self):
        pass

    @abstractmethod
    def schedule_next_power(self) -> Tuple[float, float]:
        """:return: tuple (new eventual power generation, time to wait before publishing new power)"""
        pass


class PowerSourceStatic(PowerSource):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.eventual_power = kwargs.get('power')

    def schedule_next_power(self) -> Tuple[float, float]:
        return self.actual_power, INFINITY


class PowerSourceHistory(PowerSource):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.power_column = kwargs.get('power_column', 'power')
        self.buffer = EventHistoryBuffer(**kwargs)
        if not self.buffer.column_exists(self.power_column):
            raise ValueError('dataframe does not have the mandatory column {}'.format(self.power_column))
        self.eventual_power = self.buffer.initial_val[self.power_column].item()

    def schedule_next_power(self) -> Tuple[float, float]:
        eventual = self.actual_power
        next_time = self._clock
        while eventual == self.actual_power and next_time < INFINITY:
            eventual = self.buffer.get_event()[self.power_column].item()
            next_time = self.buffer.time_of_next_event()
            self.buffer.advance()
        return eventual, next_time - self._clock
