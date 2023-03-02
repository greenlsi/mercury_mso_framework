from __future__ import annotations
from mercury.config.edcs import EdgeDataCenterConfig, EdgeFederationConfig
from mercury.config.gateway import GatewaysConfig
from mercury.msg.edcs import EdgeDataCenterReport, EDCProfileReport
from mercury.msg.packet import AppPacket, NetworkPacket, PacketInterface, PhysicalPacket
from mercury.msg.smart_grid import EnergyDemand
from mercury.utils.amf import AccessManagementFunction
from typing import Generic, Type
from xdevs.models import Coupled, Port
from .dyn_manager import EDCDynamicManager
from .edc_inf import EDCInterface
from .estimator import EDCDemandEstimator
from .profiler import EDCProfiler
from .r_manager import EDCResourceManager
from ...network.xh import CrosshaulTransceiver
from ...common.net_manager import NetworkManager


class EdgeDataCenter(Coupled, Generic[PacketInterface]):
    def __init__(self, p_type: Type[PacketInterface], edc_id: str, edge_fed_config: EdgeFederationConfig,
                 gws_config: GatewaysConfig, srv_priority: list[str], amf: AccessManagementFunction):
        """
        Edge data center model
        :param p_type: data ports type.
        :param edc_id: Edge data center ID.
        :param edge_fed_config: Edge federation configuration.
        :param srv_priority: service priority list.
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        self.edc_id: str = edc_id
        edc_config: EdgeDataCenterConfig = edge_fed_config.edcs_config[self.edc_id]
        self.dynamic: bool = edc_config.dyn_config is not None and edc_config.dyn_config.required
        self.smart_grid: bool = edc_config.sg_config is not None
        super().__init__(f'edc_{self.edc_id}')

        # GENERIC COMPONENTS (regardless of p_type)
        self.r_manager: EDCResourceManager = EDCResourceManager(edc_config, srv_priority, edge_fed_config.cloud_id)
        self.edc_profiler: EDCProfiler = EDCProfiler(self.edc_id, edge_fed_config.srv_profiling_windows)
        self.edc_inf: EDCInterface = EDCInterface(self.edc_id, edge_fed_config, gws_config, amf)
        for component in self.r_manager, self.edc_profiler, self.edc_inf:
            self.add_component(component)
        if self.dynamic:
            self.estimator: EDCDemandEstimator = EDCDemandEstimator(edc_id, edc_config.dyn_config.srv_estimators_config)
            self.dyn_manager: EDCDynamicManager = EDCDynamicManager(edc_config)
            self.add_component(self.estimator)
            self.add_component(self.dyn_manager)

        # INPUT/OUTPUT PORTS
        self.input_data: Port[PacketInterface] = Port(p_type, 'input_data')
        self.output_data: Port[PacketInterface] = Port(p_type, 'output_data')
        self.output_edc_report: Port[EdgeDataCenterReport] = Port(EdgeDataCenterReport, 'output_edc_report')
        self.output_profile_report: Port[EDCProfileReport] = Port(EDCProfileReport, 'output_profile_report')
        self.add_in_port(self.input_data)
        for out_port in self.output_data, self.output_edc_report, self.output_profile_report:
            self.add_out_port(out_port)
        self.add_out_port(self.output_edc_report)
        if self.smart_grid:
            self.input_sg_report: Port[EnergyDemand] = Port(EnergyDemand, 'input_sg_report')
            self.output_sg_report: Port[EnergyDemand] = Port(EnergyDemand, 'output_sg_report')
            self.add_in_port(self.input_sg_report)
            self.add_out_port(self.output_sg_report)

        # GENERIC COUPLINGS (regardless of p_type)
        self.add_coupling(self.edc_inf.output_srv, self.r_manager.input_srv)
        self.add_coupling(self.r_manager.output_srv_response, self.edc_profiler.input_srv)
        self.add_coupling(self.edc_profiler.output_srv, self.edc_inf.input_srv)
        self.add_coupling(self.edc_profiler.output_edc_report, self.edc_inf.input_report)
        self.add_coupling(self.edc_profiler.output_edc_report, self.output_edc_report)
        self.add_coupling(self.edc_profiler.output_profile_report, self.output_profile_report)
        if self.dynamic:
            self.add_coupling(self.edc_profiler.output_edc_report, self.estimator.input_edc_report)
            self.add_coupling(self.estimator.output_srv_estimation, self.dyn_manager.input_srv_estimation)
            self.add_coupling(self.dyn_manager.output_edc_config, self.r_manager.input_config)
        if self.smart_grid:
            self.add_coupling(self.r_manager.output_report, self.output_sg_report)
            self.add_coupling(self.input_sg_report, self.edc_profiler.input_edc_report)
        else:
            self.add_coupling(self.r_manager.output_report, self.edc_profiler.input_edc_report)

        # MODEL SPECIFICATION (depending on p_type)
        if p_type == AppPacket:
            self.add_coupling(self.input_data, self.edc_inf.input_app)
            self.add_coupling(self.edc_inf.output_app, self.output_data)
            self.add_coupling(self.r_manager.output_srv_request, self.output_data)
        else:
            self.net_manager: NetworkManager = NetworkManager(edc_id)
            self.add_component(self.net_manager)
            self.add_coupling(self.net_manager.output_app, self.edc_inf.input_app)
            self.add_coupling(self.edc_inf.output_app, self.net_manager.input_app)
            self.add_coupling(self.r_manager.output_srv_request, self.net_manager.input_app)
            if p_type == NetworkPacket:
                self.add_coupling(self.input_data, self.net_manager.input_net)
                self.add_coupling(self.net_manager.output_net, self.output_data)
            elif p_type == PhysicalPacket:
                if amf is None:
                    raise ValueError('amf cannot be None')
                self.edc_trx: CrosshaulTransceiver = CrosshaulTransceiver(edc_id, amf)
                self.add_component(self.edc_trx)
                self.add_coupling(self.input_data, self.edc_trx.input_phys)
                self.add_coupling(self.edc_trx.output_net_to_node, self.net_manager.input_net)
                self.add_coupling(self.net_manager.output_net, self.edc_trx.input_net)
                self.add_coupling(self.edc_trx.output_phys, self.output_data)
            else:
                raise ValueError(f'Invalid value for p_type ({p_type})')
