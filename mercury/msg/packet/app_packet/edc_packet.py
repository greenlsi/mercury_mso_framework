from abc import ABC
from mercury.config.packet import PacketConfig
from ...edcs import EdgeDataCenterReport
from .app_packet import AppPacket


class EdgeDataCenterPacket(AppPacket, ABC):
    def __init__(self, node_from: str, node_to: str, header_only: bool, t_gen: float):
        data: int = 0 if header_only else PacketConfig.EDGE_FED_MGMT_CONTENT
        super().__init__(node_from, node_to, data, PacketConfig.EDGE_FED_MGMT_HEADER, t_gen)


class EDCReportPacket(EdgeDataCenterPacket):
    def __init__(self, node_to: str, edc_report: EdgeDataCenterReport, t_gen: float):
        super().__init__(edc_report.edc_id, node_to, False, t_gen)
        self.edc_report: EdgeDataCenterReport = edc_report
