from __future__ import annotations
from abc import ABC, abstractmethod
from random import gauss


class CloudProcTimeModel(ABC):
    def __init__(self, **kwargs):
        """
        Processing unit processing time model.
        :param kwargs: any additional configuration parameter.
        """
        pass

    def proc_time(self) -> float:
        """
        Compute processing time in cloud.
        :return: processing time (in seconds) of the processing unit.
        """
        return max(0., self._proc_time)

    @property
    @abstractmethod
    def _proc_time(self) -> float:
        """
        Compute processing time in cloud.
        :return: processing time (in seconds) of the processing unit.
        """
        pass


class ConstantProcTimeModel(CloudProcTimeModel):
    def __init__(self, **kwargs):
        """
        Constant processing time model for processing unit.
        :param float: processing time (in s) of processing unit.
                      By default, it is set to 0. It must be greater than or equal to 0.
        """
        super().__init__(**kwargs)
        self.proc_t: float = kwargs.get('proc_t', 0)
        if self.proc_t < 0:
            raise ValueError(f'proc_t ({self.proc_t}) must be greater than or equal to 0')

    @property
    def _proc_time(self) -> float:
        return self.proc_t


class GaussianProcTimeModel(CloudProcTimeModel):
    def __init__(self, **kwargs):
        """
        Gaussian processing time model for cloud.
        :param float mu: mean processing time (in s) of cloud.
                         By default, it is set to 0. It must be greater than or equal to 0.
        :param float sigma: standard deviation (in s) of cloud.
                            By default, it is set to 0. It must be greater than or equal to 0.
        """
        super().__init__(**kwargs)

        self.mu: float = kwargs.get('mu', 0)
        if self.mu < 0:
            raise ValueError(f'mu ({self.mu}) must be greater than or equal to 0')

        self.sigma: float = kwargs.get('sigma', 0)
        if self.sigma < 0:
            raise ValueError(f'sigma ({self.sigma}) must be greater than or equal to 0')

    @property
    def _proc_time(self) -> float:
        return gauss(self.mu, self.sigma)
