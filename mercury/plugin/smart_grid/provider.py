from typing import Tuple, Optional
from abc import ABC, abstractmethod
from mercury.msg.smart_grid import ElectricityOffer
from xdevs.models import Atomic, Port, PHASE_PASSIVE, INFINITY
from mercury.utils.history_buffer import EventHistoryBuffer


class EnergyProvider(Atomic, ABC):
    def __init__(self, **kwargs):
        self.provider_id: str = kwargs['provider_id']
        self.actual_offer: Optional[float] = None
        self.eventual_offer: Optional[float] = None
        self.next_timeout: float = INFINITY
        self._clock: float = 0

        super().__init__('smart_grid_provider_{}'.format(self.provider_id))

        self.out_electricity_offer = Port(ElectricityOffer, 'out_electricity_offer')
        self.add_out_port(self.out_electricity_offer)

    def deltint(self):
        self._clock += self.sigma
        self.actual_offer = self.eventual_offer
        self.eventual_offer, self.next_timeout = self.schedule_next_offer()
        self.hold_in(PHASE_PASSIVE, self.next_timeout)

    def deltext(self, e):
        self._clock += e
        self.next_timeout -= e
        self.hold_in(PHASE_PASSIVE, self.next_timeout)

    def lambdaf(self):
        self.out_electricity_offer.add(ElectricityOffer(self.provider_id, self.eventual_offer))

    def initialize(self):
        self.hold_in(PHASE_PASSIVE, 0)

    def exit(self):
        pass

    def get_next_timeout(self):
        return self.next_timeout

    @abstractmethod
    def schedule_next_offer(self) -> Tuple[Optional[float], float]:
        """:return: tuple (new eventual offer, time to wait before publishing new offer)"""
        pass


class EnergyProviderStatic(EnergyProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.eventual_offer = kwargs.get('offer', None)

    def schedule_next_offer(self) -> Tuple[Optional[float], float]:
        return self.actual_offer, INFINITY


class EnergyProviderHistory(EnergyProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.offer_column = kwargs.get('offer_column', 'offer')
        self.buffer = EventHistoryBuffer(**kwargs)
        if not self.buffer.column_exists(self.offer_column):
            raise ValueError('dataframe does not have the mandatory column {}'.format(self.offer_column))
        self.eventual_offer = self.buffer.initial_val[self.offer_column].item()

    def schedule_next_offer(self) -> Tuple[float, float]:
        eventual = self.actual_offer
        next_time = self._clock
        while eventual == self.actual_offer and next_time < INFINITY:
            eventual = self.buffer.get_event()[self.offer_column].item()
            next_time = self.buffer.time_of_next_event()
            self.buffer.advance()
        return eventual, next_time - self._clock
