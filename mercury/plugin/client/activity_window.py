from ..common.event_generator import *


class SrvActivityWindowGenerator(EventGenerator[None], ABC):
    pass


class ConstantSrvWindowGenerator(SrvActivityWindowGenerator, PeriodicGenerator[None]):
    def __init__(self, **kwargs):
        kwargs = {**kwargs, 'period': kwargs['length']}
        super().__init__(**kwargs)


class UniformSrvWindowGenerator(SrvActivityWindowGenerator, UniformDistributionGenerator[None]):
    pass


class GaussianSrvWindowGenerator(SrvActivityWindowGenerator, GaussianDistributionGenerator[None]):
    pass


class ExponentialSrvWindowGenerator(SrvActivityWindowGenerator, ExponentialDistributionGenerator[None]):
    pass


class LambdaSrvSessionDuration(LambdaDrivenGenerator[None]):
    pass
