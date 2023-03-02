from ..common.event_generator import *


class SrvActivityGenerator(EventGenerator[None], ABC):
    def next_activity(self, t_close: float):
        """
        After closing it, this method schedules the next session.
        :param t_close: time when previous session was closed.
        """
        self.advance()
        self.next_t = max(self.next_t, t_close)


class SingleSrvActivityGenerator(SrvActivityGenerator, DiracDeltaGenerator[None]):
    pass


class PeriodicSrvActivityGenerator(SrvActivityGenerator, PeriodicGenerator[None]):
    pass


class UniformSrvActivityGenerator(SrvActivityGenerator, UniformDistributionGenerator[None]):
    pass


class GaussianSrvActivityGenerator(SrvActivityGenerator, GaussianDistributionGenerator[None]):
    pass


class ExponentialSrvActivityGenerator(SrvActivityGenerator, ExponentialDistributionGenerator[None]):
    pass


class LambdaSrvActivityGenerator(SrvActivityGenerator, LambdaDrivenGenerator[None]):
    pass
