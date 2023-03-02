from abc import ABC, abstractmethod
from random import gauss


class CloudNetworkDelay(ABC):
    def __init__(self, **kwargs):
        self.prop_delay: float = kwargs.get('prop_delay', 0)
        if self.prop_delay < 0:
            raise ValueError('prop_delay must be greater than or equal to 0')
        self.bit_rate: float = kwargs.get('bit_rate', 0)
        if self.bit_rate < 0:
            raise ValueError('bit_rate must be greater than or equal to 0')

    def delay(self, msg_size: int) -> float:
        return max(0., self._delay(msg_size))

    @abstractmethod
    def _delay(self, msg_size: int) -> float:
        pass

    def mean_delay(self, msg_size) -> float:
        trans_delay = 0 if self.bit_rate <= 0 else msg_size / self.bit_rate
        return self.prop_delay + trans_delay


class ConstantCloudNetworkDelay(CloudNetworkDelay):
    def _delay(self, msg_size: int) -> float:
        return self.mean_delay(msg_size)


class GaussianCloudNetworkDelay(CloudNetworkDelay):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sigma = kwargs.get('sigma', 0)
        if self.sigma < 0:
            raise ValueError('sigma must be greater than or equal to 0')

    def _delay(self, msg_size: int) -> float:
        return gauss(self.mean_delay(msg_size), self.sigma)
