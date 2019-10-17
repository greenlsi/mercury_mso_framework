from xdevs.models import Coupled, Port
from .service_data_generator import ServiceDataGenerator
from .service_session_manager import ServiceSessionManager
from ..internal_interfaces import ServiceRequired, ConnectedAccessPoint
from ....common.packet.application.service import ServiceConfiguration, ServiceDelayReport
from ....common.packet.network import NetworkPacket, NetworkPacketConfiguration


class Service(Coupled):
    """
    Service xDEVS module

    :param str name: name of the xDEVS module
    :param str ue_id: User Equipment ID
    :param  ServiceConfiguration service_config: service configuration
    :param NetworkPacketConfiguration network_config: network configuration
    :param float t_initial: initial back off time before starting to operate
    """
    def __init__(self, name, ue_id, service_config, network_config, t_initial):
        self.service_id = service_config.service_id
        super().__init__(name + "_" + self.service_id)

        data_generator = ServiceDataGenerator(name + '_data_generator', ue_id, service_config, t_initial)
        session_manager = ServiceSessionManager(name + '_session_manager', ue_id, service_config, network_config,
                                                t_initial)
        self.add_component(data_generator)
        self.add_component(session_manager)

        self.input_connected_ap = Port(ConnectedAccessPoint, name + '_input_connected_ap')
        self.input_network = Port(NetworkPacket, name + '_input_network')
        self.output_network = Port(NetworkPacket, name + '_output_network')
        self.output_service_required = Port(ServiceRequired, name + '_output_service_required')
        self.output_service_delay_report = Port(ServiceDelayReport, name + '_output_service_delay_report')

        self.add_in_port(self.input_connected_ap)
        self.add_in_port(self.input_network)
        self.add_out_port(self.output_network)
        self.add_out_port(self.output_service_required)
        self.add_out_port(self.output_service_delay_report)

        self.external_couplings_session_manager(session_manager)
        self.internal_couplings(data_generator, session_manager)

    def external_couplings_session_manager(self, session_manager):
        """
        External couplings for the service session manager module
        :param ServiceSessionManager session_manager: service session manager xDEVS module
        """
        self.add_coupling(self.input_network, session_manager.input_network)
        self.add_coupling(self.input_connected_ap, session_manager.input_connected_ap)
        self.add_coupling(session_manager.output_network, self.output_network)
        self.add_coupling(session_manager.output_service_required, self.output_service_required)
        self.add_coupling(session_manager.output_service_delay_report, self.output_service_delay_report)

    def internal_couplings(self, data_generator, session_manager):
        """
        Internal couplings between the service session manager and the service data generator modules
        :param ServiceDataGenerator data_generator: service data generator xDEVS module
        :param ServiceSessionManager session_manager: service session manager xDEVS module
        """
        self.add_coupling(data_generator.output_session_request, session_manager.input_session_request)
