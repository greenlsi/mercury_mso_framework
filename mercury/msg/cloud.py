from .profile import WindowReport


class CloudProfileReport:
    def __init__(self, cloud_id: str, srv_id: str, n_clients: int, req_type: str, result: str, window: WindowReport):
        self.cloud_id: str = cloud_id
        self.srv_id: str = srv_id
        self.n_clients: int = n_clients
        self.req_type: str = req_type
        self.result: str = result
        self.window: WindowReport = window

    def __ne__(self, other):
        return self.n_clients != self.n_clients or self.window != other.window
