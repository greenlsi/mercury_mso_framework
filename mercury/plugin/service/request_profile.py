from abc import ABC
from typing import NoReturn
from ..common.event_generator import EventGenerator, PeriodicGenerator, UniformDistributionGenerator, \
    GaussianDistributionGenerator, ExponentialDistributionGenerator, LambdaDrivenGenerator


class ServiceRequestProfile(EventGenerator[NoReturn], ABC):
    pass


class PeriodicRequestProfile(ServiceRequestProfile, PeriodicGenerator[NoReturn]):
    pass


class UniformDistributionRequestProfile(ServiceRequestProfile, UniformDistributionGenerator[NoReturn]):
    pass


class GaussianDistributionRequestProfile(ServiceRequestProfile, GaussianDistributionGenerator[NoReturn]):
    pass


class ExponentialDistributionRequestProfile(ServiceRequestProfile, ExponentialDistributionGenerator[NoReturn]):
    pass


class LambdaDrivenRequestProfile(ServiceRequestProfile, LambdaDrivenGenerator[NoReturn]):
    pass
