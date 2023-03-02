from __future__ import annotations
from typing import Generic, Type
from xdevs.models import Coupled, Port
from mercury.config.client import ServicesConfig
from mercury.config.edcs import EdgeFederationConfig
from mercury.config.gateway import GatewaysConfig
from mercury.msg.edcs import EdgeDataCenterReport, EDCProfileReport
from mercury.msg.packet import PacketInterface
from mercury.utils.amf import AccessManagementFunction
from .edc import EdgeDataCenter


class EdgeDataCenters(Coupled, Generic[PacketInterface]):
    def __init__(self, p_type: Type[PacketInterface], edge_fed_config: EdgeFederationConfig,
                 gws_config: GatewaysConfig, srv_priority: list[str], amf: AccessManagementFunction | None):
        """
        Model containing all the edge data centers.
        :param p_type: input/output data port type.
        :param edge_fed_config: edge federation configuration.
        :param srv_priority: service priority list.
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        super().__init__(f'edge_fed_{edge_fed_config.edge_fed_id}')
        services: list[str] = list(ServicesConfig.SERVICES)
        for srv_id in srv_priority:
            services.remove(srv_id)
        srv_priority.extend(services)

        # Components
        self.edcs: dict[str, EdgeDataCenter[PacketInterface]] = dict()
        for edc_id in edge_fed_config.edcs_config:
            edc = EdgeDataCenter(p_type, edc_id, edge_fed_config, gws_config, srv_priority, amf)
            self.edcs[edc_id] = edc
            self.add_component(edc)

        self.output_data: Port[PacketInterface] = Port(p_type, 'output_data')
        self.output_edc_report: Port[EdgeDataCenterReport] = Port(EdgeDataCenterReport, 'output_edc_report')
        self.output_profile_report: Port[EDCProfileReport] = Port(EDCProfileReport, 'output_profile_report')
        for out_port in self.output_data, self.output_edc_report, self.output_profile_report:
            self.add_out_port(out_port)
        self.add_out_port(self.output_edc_report)
        self.inputs_data: dict[str, Port[PacketInterface]] = dict()
        for edc_id, edc in self.edcs.items():
            self.inputs_data[edc_id] = Port(p_type, f'input_data_{edc_id}')
            self.add_in_port(self.inputs_data[edc_id])
            self.add_coupling(self.inputs_data[edc_id], edc.input_data)
            self.add_coupling(edc.output_edc_report, self.output_edc_report)
            self.add_coupling(edc.output_profile_report, self.output_profile_report)
            self.add_coupling(edc.output_data, self.output_data)

        if any(edc_config.sg_config is not None for edc_config in edge_fed_config.edcs_config.values()):
            self.inputs_sg_report: dict[str, Port[EdgeDataCenterReport]] = dict()
            self.outputs_sg_report: dict[str, Port[EdgeDataCenterReport]] = dict()
            for edc_id, edc in self.edcs.items():
                if edc.smart_grid:
                    self.inputs_sg_report[edc_id] = Port(EdgeDataCenterReport, f'input_sg_report_{edc_id}')
                    self.outputs_sg_report[edc_id] = Port(EdgeDataCenterReport, f'output_sg_report_{edc_id}')
                    self.add_in_port(self.inputs_sg_report[edc_id])
                    self.add_out_port(self.outputs_sg_report[edc_id])
                    self.add_coupling(self.inputs_sg_report[edc_id], edc.input_sg_report)
                    self.add_coupling(edc.output_sg_report, self.outputs_sg_report[edc_id])
