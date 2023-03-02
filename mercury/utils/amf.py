from __future__ import annotations
from typing import Iterable


class AccessManagementFunction:
    def __init__(self, gateways: Iterable[str]):
        self._gateways: set[str] = set(gateways)
        self._clients: dict[str, str] = dict()

    def get_client_gateway(self, client_id: str) -> str | None:
        return self._clients.get(client_id)

    def connect_client(self, client_id: str, gateway_id: str) -> bool:
        if gateway_id not in self._gateways or self._clients.get(client_id, gateway_id) != gateway_id:
            return False
        self._clients[client_id] = gateway_id
        return True

    def disconnect_client(self, client_id: str, gateway_id: str) -> bool:
        if self._clients.get(client_id) != gateway_id:
            return False
        self._clients.pop(client_id)
        return True

    def handover_client(self, client_id: str, gateway_from_id: str, gateway_to_id: str):
        if self.disconnect_client(client_id, gateway_from_id):
            if self.connect_client(client_id, gateway_to_id):
                return True
            self.connect_client(client_id, gateway_from_id)
        return False
