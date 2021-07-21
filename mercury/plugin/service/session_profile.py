from abc import ABC
from typing import NoReturn
from ..common.event_generator import EventGenerator, PeriodicGenerator, UniformDistributionGenerator, \
    GaussianDistributionGenerator, ExponentialDistributionGenerator, LambdaDrivenGenerator


class ServiceSessionProfile(EventGenerator[NoReturn], ABC):
    def next_session(self, t_close: float):
        """
        After closing it, this method schedules the next session.
        :param t_close: time when previous session was closed.
        """
        self.advance()
        self.next_t = max(self.next_t, t_close)


class PeriodicSessionProfile(ServiceSessionProfile, PeriodicGenerator[NoReturn]):
    pass


class UniformDistributionSessionProfile(ServiceSessionProfile, UniformDistributionGenerator[NoReturn]):
    pass


class GaussianDistributionSessionProfile(ServiceSessionProfile, GaussianDistributionGenerator[NoReturn]):
    pass


class ExponentialDistributionSessionProfile(ServiceSessionProfile, ExponentialDistributionGenerator[NoReturn]):
    pass


class LambdaDrivenSessionProfile(ServiceSessionProfile, LambdaDrivenGenerator[NoReturn]):
    pass
