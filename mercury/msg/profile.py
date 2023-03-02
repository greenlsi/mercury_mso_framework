from __future__ import annotations
from abc import ABC, abstractmethod
from collections import deque
from math import inf
from mercury.msg.packet.app_packet.srv_packet import SrvRelatedResponse
from typing import Generator


class WindowReport:
    def __init__(self, window_n: int, window_acc_delay: float):
        self.window_n: int = window_n
        self.window_acc_delay: float = window_acc_delay

    @property
    def window_mean_delay(self) -> float | None:
        return self.window_acc_delay / self.window_n if self.window_n else None

    def __ne__(self, other):
        return self.window_n != other.window_n or self.window_acc_delay != other.window_acc_delay


class ProfileWindow:
    def __init__(self, window_size: float):
        if window_size < 0:
            raise ValueError(f'invalid value for window_size ({window_size})')
        self.window_size: float = window_size
        self.t_last: float = 0
        self.total_n: int = 0
        self.total_acc_delay: float = 0
        self.window_acc_delay: float = 0
        self.window: deque[tuple[float, str, float]] = deque()

    @property
    def window_n(self) -> int:
        return len(self.window)

    @property
    def t_next(self) -> float:
        return self.window[0][0] + self.window_size if self.window else inf

    @property
    def window_mean_delay(self) -> float | None:
        return self.window_acc_delay / self.window_n if self.window else None

    @property
    def total_mean_delay(self) -> float | None:
        return self.total_acc_delay / self.total_n if self.total_n else None

    def report(self) -> WindowReport:
        return WindowReport(self.window_n, self.window_acc_delay)

    def clean(self, t: float) -> Generator[str, None, None]:
        if t < self.t_last:
            raise ValueError(f'invalid value for t: {t} (last_t: {self.t_last})')
        self.t_last = t
        while self.window and self.t_next <= self.t_last:
            _, client_id, delay = self.window.popleft()
            self.window_acc_delay -= delay
            yield client_id

    def push(self, t: float, client_id: str, delay: float):
        if t < self.t_last:
            raise ValueError(f'invalid value for t: {t} (last_t: {self.t_last})')
        if delay < 0:
            raise ValueError(f'invalid delay ({delay})')
        self.t_last = t
        self.total_n += 1
        self.total_acc_delay += delay
        self.window_acc_delay += delay
        self.window.append((t, client_id, delay))


class AbstractProfile(ABC):
    def __init__(self):
        self.profiles: dict[str, AbstractProfile | ProfileWindow] = dict()

    @property
    def t_last(self):
        return max((profile.t_last for profile in self.profiles.values()), default=0)

    @property
    def t_next(self) -> float:
        return min((profile.t_next for profile in self.profiles.values()), default=inf)

    @property
    def rejected_total_n(self) -> int:
        return sum(profile.rejected_total_n for profile in self.profiles.values())

    @property
    def rejected_window_n(self) -> int:
        return sum(profile.rejected_window_n for profile in self.profiles.values())

    @property
    def rejected_total_acc_delay(self) -> float:
        return sum(profile.rejected_total_acc_delay for profile in self.profiles.values())

    @property
    def rejected_total_mean_delay(self) -> float | None:
        rejected_total_n = self.rejected_total_n
        return self.rejected_total_acc_delay / rejected_total_n if rejected_total_n else None

    @property
    def rejected_window_acc_delay(self) -> float:
        return sum(profile.rejected_window_acc_delay for profile in self.profiles.values())

    @property
    def rejected_window_mean_delay(self) -> float | None:
        rejected_window_n = self.rejected_window_n
        return self.rejected_window_acc_delay / rejected_window_n if rejected_window_n else None

    @property
    def met_deadline_total_n(self) -> int:
        return sum(profile.met_deadline_total_n for profile in self.profiles.values())

    @property
    def met_deadline_total_acc_delay(self) -> float:
        return sum(profile.met_deadline_total_acc_delay for profile in self.profiles.values())

    @property
    def met_deadline_total_mean_delay(self) -> float | None:
        met_deadline_total_n = self.met_deadline_total_n
        return self.met_deadline_total_acc_delay / met_deadline_total_n if met_deadline_total_n else None

    @property
    def met_deadline_window_n(self) -> int:
        return sum(profile.met_deadline_window_n for profile in self.profiles.values())

    @property
    def met_deadline_window_acc_delay(self) -> float:
        return sum(profile.met_deadline_window_acc_delay for profile in self.profiles.values())

    @property
    def met_deadline_window_mean_delay(self) -> float | None:
        met_deadline_window_n = self.met_deadline_window_n
        return self.met_deadline_window_acc_delay / met_deadline_window_n if met_deadline_window_n else None

    @property
    def missed_deadline_total_n(self) -> int:
        return sum(profile.missed_deadline_total_n for profile in self.profiles.values())

    @property
    def missed_deadline_total_acc_delay(self) -> float:
        return sum(profile.missed_deadline_total_acc_delay for profile in self.profiles.values())

    @property
    def missed_deadline_total_mean_delay(self) -> float | None:
        missed_deadline_total_n = self.missed_deadline_total_n
        return self.missed_deadline_total_acc_delay / missed_deadline_total_n if missed_deadline_total_n else None

    @property
    def missed_deadline_window_n(self) -> int:
        return sum(profile.missed_deadline_window_n for profile in self.profiles.values())

    @property
    def missed_deadline_window_acc_delay(self) -> float:
        return sum(profile.missed_deadline_window_acc_delay for profile in self.profiles.values())

    @property
    def missed_deadline_window_mean_delay(self) -> float | None:
        missed_deadline_window_n = self.missed_deadline_window_n
        return self.missed_deadline_window_acc_delay / missed_deadline_window_n if missed_deadline_window_n else None

    @property
    def accepted_total_n(self) -> int:
        return self.met_deadline_total_n + self.missed_deadline_total_n

    @property
    def accepted_total_acc_delay(self) -> float:
        return self.met_deadline_total_acc_delay + self.missed_deadline_total_acc_delay

    @property
    def accepted_total_mean_delay(self) -> float | None:
        accepted_total_n = self.accepted_total_n
        return self.accepted_total_acc_delay / accepted_total_n if accepted_total_n else None

    @property
    def accepted_window_n(self) -> int:
        return self.met_deadline_window_n + self.missed_deadline_window_n

    @property
    def accepted_window_acc_delay(self) -> float:
        return self.met_deadline_window_acc_delay + self.missed_deadline_window_acc_delay

    @property
    def accepted_window_mean_delay(self) -> float | None:
        accepted_window_n = self.accepted_window_n
        return self.accepted_window_acc_delay / accepted_window_n if accepted_window_n else None

    @property
    def total_n(self) -> int:
        return self.rejected_total_n + self.accepted_total_n

    @property
    def total_acc_delay(self) -> float:
        return self.rejected_total_acc_delay + self.accepted_total_acc_delay

    @property
    def total_mean_delay(self) -> float | None:
        total_n = self.total_n
        return self.total_acc_delay / total_n if total_n else None

    @property
    def window_n(self) -> int:
        return self.rejected_window_n + self.accepted_window_n

    @property
    def window_acc_delay(self) -> float:
        return self.rejected_window_acc_delay + self.accepted_window_acc_delay

    @property
    def window_mean_delay(self) -> float | None:
        window_n = self.window_n
        return self.window_acc_delay / window_n if window_n else None

    @abstractmethod
    def push(self, t: float, response: SrvRelatedResponse) -> bool:
        pass

    @abstractmethod
    def clean(self, t: float) -> Generator[str, None, None] | bool:
        pass


class ResponseProfile(AbstractProfile):

    REJECTED = 'rejected'
    MET_DEADLINE = 'met_deadline'
    MISSED_DEADLINE = 'missed_deadline'

    def __init__(self, window_size: float):
        super().__init__()
        self.profiles: dict[str, ProfileWindow] = {
            ResponseProfile.REJECTED: ProfileWindow(window_size),
            ResponseProfile.MET_DEADLINE: ProfileWindow(window_size),
            ResponseProfile.MISSED_DEADLINE: ProfileWindow(window_size),
        }

    def __eq__(self, other):
        return self.total_n == other.total_n

    @property
    def rejected_total_n(self) -> int:
        return self.profiles[self.REJECTED].total_n

    @property
    def rejected_window_n(self) -> int:
        return self.profiles[self.REJECTED].window_n

    @property
    def rejected_total_acc_delay(self) -> float:
        return self.profiles[self.REJECTED].total_acc_delay

    @property
    def rejected_window_acc_delay(self) -> float:
        return self.profiles[self.REJECTED].window_acc_delay

    @property
    def met_deadline_total_n(self) -> int:
        return self.profiles[self.MET_DEADLINE].total_n

    @property
    def met_deadline_window_n(self) -> int:
        return self.profiles[self.MET_DEADLINE].window_n

    @property
    def met_deadline_total_acc_delay(self) -> float:
        return self.profiles[self.MET_DEADLINE].total_acc_delay

    @property
    def met_deadline_window_acc_delay(self) -> float:
        return self.profiles[self.MET_DEADLINE].window_acc_delay

    @property
    def missed_deadline_total_n(self) -> int:
        return self.profiles[self.MISSED_DEADLINE].total_n

    @property
    def missed_deadline_window_n(self) -> int:
        return self.profiles[self.MISSED_DEADLINE].window_n

    @property
    def missed_deadline_total_acc_delay(self) -> float:
        return self.profiles[self.MISSED_DEADLINE].total_acc_delay

    @property
    def missed_deadline_window_acc_delay(self) -> float:
        return self.profiles[self.MISSED_DEADLINE].window_acc_delay

    def push(self, t: float, response: SrvRelatedResponse) -> bool:
        profile = self.profiles[self.REJECTED]
        if response.successful:
            profile = self.profiles[self.MET_DEADLINE] if response.deadline_met else self.profiles[self.MISSED_DEADLINE]
        profile.push(t, response.client_id, response.t_processing)
        return True

    def clean(self, t: float) -> Generator[str, None, None]:
        for profile in self.profiles.values():
            for client_id in profile.clean(t):
                yield client_id


class SrvProfile(AbstractProfile):
    def __init__(self, window_size: float):
        super().__init__()
        if window_size < 0:
            raise ValueError(f'invalid value for window_size ({window_size})')
        self.window_size: float = window_size
        self.clients: dict[str, int] = dict()
        self.profiles: dict[str, ResponseProfile] = dict()

    @property
    def n_clients(self) -> int:
        return len(self.clients)

    def push(self, t: float, response: SrvRelatedResponse) -> bool:
        client_id = response.client_id
        req_type_id = type(response.request).__name__
        self.clients[client_id] = self.clients.get(client_id, 0) + 1
        if req_type_id not in self.profiles:
            self.profiles[req_type_id] = ResponseProfile(self.window_size)
        return self.profiles[req_type_id].push(t, response)

    def clean(self, t: float) -> bool:
        res = False
        for profile in self.profiles.values():
            for client_id in profile.clean(t):
                res = True
                self.clients[client_id] -= 1
                if self.clients[client_id] == 0:
                    self.clients.pop(client_id)
        return res


class EDCProfile(AbstractProfile):
    def __init__(self, edc_id: str, srv_profiling_windows: dict[str, float]):
        super().__init__()
        self.edc_id: str = edc_id
        self.profiles: dict[str, SrvProfile] = {srv_id: SrvProfile(window_size)
                                                for srv_id, window_size in srv_profiling_windows.items()}

    def push(self, t: float, response: SrvRelatedResponse) -> bool:
        service_id = response.service_id
        return service_id in self.profiles and self.profiles[service_id].push(t, response)

    def clean(self, t: float) -> bool:
        res = False
        for profile in self.profiles.values():
            res |= profile.clean(t)
        return res


class CloudProfile(AbstractProfile):
    def __init__(self, cloud_id: str, srv_profiling_windows: dict[str, float]):
        super().__init__()
        self.cloud_id: str = cloud_id
        self.profiles: dict[str, SrvProfile] = {srv_id: SrvProfile(window_size)
                                                for srv_id, window_size in srv_profiling_windows.items()}

    def push(self, t: float, response: SrvRelatedResponse) -> bool:
        service_id = response.service_id
        return service_id in self.profiles and self.profiles[service_id].push(t, response)

    def clean(self, t: float) -> bool:
        res = False
        for profile in self.profiles.values():
            res |= profile.clean(t)
        return res
