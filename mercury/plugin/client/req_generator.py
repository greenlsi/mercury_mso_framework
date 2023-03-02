from ..common.event_generator import *


class SrvRequestGenerator(EventGenerator[None], ABC):
    pass


class SingleSrvRequestGenerator(SrvRequestGenerator, DiracDeltaGenerator[None]):
    pass


class PeriodicSrvRequestGenerator(SrvRequestGenerator, PeriodicGenerator[None]):
    pass


class UniformSrvRequestGenerator(SrvRequestGenerator, UniformDistributionGenerator[None]):
    pass


class GaussianSrvRequestGenerator(SrvRequestGenerator, GaussianDistributionGenerator[None]):
    pass


class ExponentialSrvRequestGenerator(SrvRequestGenerator, ExponentialDistributionGenerator[None]):
    pass


class LambdaSrvRequestGenerator(SrvRequestGenerator, LambdaDrivenGenerator[None]):
    pass
