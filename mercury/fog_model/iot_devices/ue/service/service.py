from xdevs.models import Coupled, Port
from .service_data_generator import ServiceDataGenerator
from .service_session_manager import ServiceSessionManager
from ..internal_interfaces import ServiceRequired, ConnectedAccessPoint
from ....common.packet.apps.service import ServiceConfiguration, ServiceDelayReport
from ....common.packet.packet import NetworkPacket, NetworkPacketConfiguration


class Service(Coupled):
    def __init__(self, name: str, ue_id: str, service_config: ServiceConfiguration,
                 network_config: NetworkPacketConfiguration, t_initial: float, lite_id: str = None):
        """
        Service xDEVS module

        :param name: name of the xDEVS module
        :param ue_id: User Equipment ID
        :param service_config: service configuration
        :param network_config: network configuration
        :param t_initial: initial back off time before starting to operate
        """
        self.service_id = service_config.service_id
        super().__init__(name + "_" + self.service_id)

        data_generator = ServiceDataGenerator(name + '_data_generator', ue_id, service_config, t_initial)
        session_manager = ServiceSessionManager(name + '_session_manager', ue_id, service_config, network_config,
                                                t_initial, lite_id)
        self.add_component(data_generator)
        self.add_component(session_manager)

        self.input_network = Port(NetworkPacket, 'input_network')
        self.output_network = Port(NetworkPacket, 'output_network')
        self.output_service_delay_report = Port(ServiceDelayReport, 'output_service_delay_report')
        self.add_in_port(self.input_network)
        self.add_out_port(self.output_network)
        self.add_out_port(self.output_service_delay_report)

        lite = lite_id is not None
        if not lite:
            self.input_connected_ap = Port(ConnectedAccessPoint, 'input_connected_ap')
            self.output_service_required = Port(ServiceRequired, 'output_service_required')
            self.add_in_port(self.input_connected_ap)
            self.add_out_port(self.output_service_required)

        self.external_couplings_session_manager(session_manager, lite)
        self.internal_couplings(data_generator, session_manager)

    def external_couplings_session_manager(self, session_manager: ServiceSessionManager, lite: bool):
        self.add_coupling(self.input_network, session_manager.input_network)
        self.add_coupling(session_manager.output_network, self.output_network)
        self.add_coupling(session_manager.output_service_delay_report, self.output_service_delay_report)
        if not lite:
            self.add_coupling(self.input_connected_ap, session_manager.input_connected_ap)
            self.add_coupling(session_manager.output_service_required, self.output_service_required)

    def internal_couplings(self, data_generator: ServiceDataGenerator, session_manager: ServiceSessionManager):
        self.add_coupling(data_generator.output_session_request, session_manager.input_session_request)
