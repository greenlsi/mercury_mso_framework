from abc import ABC
from typing import NoReturn
from ..common.event_generator import EventGenerator, PeriodicGenerator, UniformDistributionGenerator, \
    GaussianDistributionGenerator, ExponentialDistributionGenerator, LambdaDrivenGenerator


class ServiceSessionDuration(EventGenerator[NoReturn], ABC):
    pass


class FixedServiceSessionDuration(ServiceSessionDuration, PeriodicGenerator[NoReturn]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, period=kwargs['duration'])


class UniformDistributionSessionDuration(ServiceSessionDuration, UniformDistributionGenerator[NoReturn]):
    pass


class GaussianDistributionSessionDuration(ServiceSessionDuration, GaussianDistributionGenerator[NoReturn]):
    pass


class ExponentialDistributionSessionDuration(ServiceSessionDuration, ExponentialDistributionGenerator[NoReturn]):
    pass


class LambdaDrivenDistributionSessionDuration(LambdaDrivenGenerator[NoReturn]):
    pass
