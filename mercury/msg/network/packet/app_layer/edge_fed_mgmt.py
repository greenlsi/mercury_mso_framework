from abc import ABC
from typing import Dict
from mercury.config.network import PacketConfig
from ....smart_grid import PowerConsumptionReport
from ..packet import ApplicationPacket, PacketData


class EdgeFedManagementPacket(ApplicationPacket, ABC):
    def __init__(self, header_only: bool = False):
        data: PacketData = PacketData() if header_only else PacketData(PacketConfig.EDGE_FED_MGMT_CONTENT)
        super().__init__(data, PacketConfig.EDGE_FED_MGMT_HEADER)


class NewDispatchingFunction(EdgeFedManagementPacket):

    def __init__(self, dispatching):
        super().__init__(header_only=True)
        from mercury.msg.edcs import DispatchingFunction
        self.dispatching: DispatchingFunction = dispatching


class NewHotStandbyFunction(EdgeFedManagementPacket):

    def __init__(self, hot_standby):
        super().__init__(header_only=True)
        from mercury.msg.edcs import HotStandbyFunction
        self.hot_standby: HotStandbyFunction = hot_standby


class NewEDCReport(EdgeFedManagementPacket):
    def __init__(self, power_report: PowerConsumptionReport):
        super().__init__(header_only=False)
        self.power_report: PowerConsumptionReport = power_report


class NewSDNPath(EdgeFedManagementPacket):
    def __init__(self, service_route: Dict[str, str]):
        super().__init__(header_only=True)
        self.service_route: Dict[str, str] = service_route
