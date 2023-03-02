from __future__ import annotations
from typing import Generic, Type
from xdevs.models import Coupled, Port
from mercury.config.cloud import CloudConfig
from mercury.config.transducers import TransducersConfig
from mercury.msg.cloud import CloudProfileReport
from mercury.msg.packet import AppPacket, NetworkPacket, PacketInterface, PhysicalPacket
from mercury.utils.amf import AccessManagementFunction
from .cloud_pool import CloudPool
from .network_delay import CloudNetworkDelay
from .profiler import CloudProfiler
from ..network.xh import CrosshaulTransceiver
from ..common import NetworkManager


class Cloud(Coupled, Generic[PacketInterface]):
    def __init__(self, p_type: Type[PacketInterface], cloud_config: CloudConfig, amf: AccessManagementFunction | None):
        """
        Model containing all the edge data centers.
        :param p_type: input/output data port type.
        :param cloud_config: cloud configuration.
        :param amf: Reference to the Access Management Function. It is used to locate clients in the network.
        """
        self.cloud_id: str = cloud_config.cloud_id
        super().__init__(f'cloud_{self.cloud_id}')

        # GENERIC COMPONENTS (regardless of p_type)
        self.cloud_pool: CloudPool = CloudPool(cloud_config)
        self.network_delay: CloudNetworkDelay = CloudNetworkDelay(p_type, cloud_config)
        self.add_component(self.cloud_pool)
        self.add_component(self.network_delay)
        if TransducersConfig.LOG_CLOUD:
            srv_profiling_windows: dict[str, float] = {srv_id: srv_config.profiling_window
                                                       for srv_id, srv_config in cloud_config.srv_config.items()}
            self.cloud_profiler: CloudProfiler = CloudProfiler(self.cloud_id, srv_profiling_windows)
            self.add_component(self.cloud_profiler)

        # INPUT/OUTPUT PORTS
        self.input_data: Port[PacketInterface] = Port(p_type, 'input_data')
        self.output_data: Port[PacketInterface] = Port(p_type, 'output_data')
        self.output_profile: Port[CloudProfileReport] = Port(CloudProfileReport, 'output_profile')
        self.add_in_port(self.input_data)
        self.add_out_port(self.output_data)
        self.add_out_port(self.output_profile)

        # GENERIC COUPLINGS (regardless of p_type)
        self.add_coupling(self.input_data, self.network_delay.input_data)
        self.add_coupling(self.network_delay.output_to_others, self.output_data)
        if TransducersConfig.LOG_CLOUD:
            self.add_coupling(self.cloud_pool.output_responses, self.cloud_profiler.input_srv)
            self.add_coupling(self.cloud_profiler.output_profile, self.output_profile)

        # MODEL SPECIFICATION (depending on p_type)
        if p_type == AppPacket:
            self.add_coupling(self.network_delay.output_to_cloud, self.cloud_pool.input_requests)
            self.add_coupling(self.cloud_pool.output_responses, self.network_delay.input_data)
        else:
            self.net_manager: NetworkManager = NetworkManager(self.cloud_id)
            self.add_component(self.net_manager)
            self.add_coupling(self.net_manager.output_app, self.cloud_pool.input_requests)
            self.add_coupling(self.cloud_pool.output_responses, self.net_manager.input_app)
            if p_type == NetworkPacket:
                self.add_coupling(self.network_delay.output_to_cloud, self.net_manager.input_net)
                self.add_coupling(self.net_manager.output_net, self.network_delay.input_data)
            elif p_type == PhysicalPacket:
                if amf is None:
                    raise ValueError('amf cannot be None')
                self.cloud_trx: CrosshaulTransceiver = CrosshaulTransceiver(self.cloud_id, amf)
                self.add_component(self.cloud_trx)
                self.add_coupling(self.network_delay.output_to_cloud, self.cloud_trx.input_phys)
                self.add_coupling(self.cloud_trx.output_net_to_node, self.net_manager.input_net)
                self.add_coupling(self.net_manager.output_net, self.cloud_trx.input_net)
                self.add_coupling(self.cloud_trx.output_phys, self.network_delay.input_data)
            else:
                raise ValueError(f'Invalid value for p_type ({p_type})')
