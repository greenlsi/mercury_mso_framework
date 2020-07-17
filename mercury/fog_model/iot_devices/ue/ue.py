from typing import List
from xdevs.models import Coupled, Port
from ...common.packet.packet import PhysicalPacket, NetworkPacket, NetworkPacketConfiguration
from ...common.packet.apps.ran import RadioAccessNetworkConfiguration
from ...common.packet.apps.service import ServiceDelayReport
from .ue_antenna import UserEquipmentAntenna
from .service_mux import UEServiceMux
from .service import Service
from .access_manager import AccessManager

from ...common.packet.apps.service import ServiceConfiguration
from ...network.node import TransceiverConfiguration, NodeConfiguration


class UserEquipmentConfiguration:
    def __init__(self, ue_id: str, service_config_list: List[ServiceConfiguration],
                 radio_trx: TransceiverConfiguration = None, mobility_name: str = None, **kwargs):
        """

        :param ue_id:
        :param service_config_list:
        :param radio_trx:
        :param mobility_name:
        :param kwargs:
        """
        self.ue_id = ue_id
        for service_config in service_config_list:
            assert isinstance(service_config, ServiceConfiguration)
        self.service_config_list = service_config_list
        self.radio_node = NodeConfiguration(ue_id, radio_trx, mobility_name, **kwargs)
        self.ue_location = self.radio_node.initial_location


class UserEquipment(Coupled):
    def __init__(self, name: str, ue_config: UserEquipmentConfiguration, rac_config: RadioAccessNetworkConfiguration,
                 network_config: NetworkPacketConfiguration, t_initial: float = 0):
        """
        User Equipment xDEVS model
        :param name: xDEVS model name
        :param ue_config: User Equipment Configuration
        :param rac_config: Radio Access Network service packets configuration
        :param network_config: Network packets configuration
        :param t_initial: Initial guard time in order to avoid identical simultaneous behavior between UEs
        """
        super().__init__(name)

        # Unpack configuration parameters
        ue_id = ue_config.ue_id
        service_config_list = ue_config.service_config_list
        service_ids = [service_config.service_id for service_config in service_config_list]

        self.ue_id = ue_id

        # Define and add components
        antenna = UserEquipmentAntenna(name + '_antenna', ue_id, network_config)
        access_manager = AccessManager(name + '_access_manager', ue_id, rac_config)
        service_mux = UEServiceMux(name + '_service_mux', service_ids)
        services = [Service(name + service.service_id, ue_id, service, network_config, t_initial)
                    for service in service_config_list]
        self.add_component(antenna)
        self.add_component(access_manager)
        self.add_component(service_mux)
        [self.add_component(service) for service in services]

        # I/O ports
        self.input_radio_bc = Port(PhysicalPacket, name + '_input_radio_bc')
        self.input_radio_control_dl = Port(PhysicalPacket, name + '_input_radio_control_dl')
        self.input_radio_transport_dl = Port(PhysicalPacket, name + '_input_radio_transport_dl')
        self.output_radio_control_ul = Port(PhysicalPacket, name + '_output_radio_control_ul')
        self.output_radio_transport_ul = Port(PhysicalPacket, name + '_output_radio_transport_ul')
        self.add_in_port(self.input_radio_bc)
        self.add_in_port(self.input_radio_control_dl)
        self.add_in_port(self.input_radio_transport_dl)
        self.add_out_port(self.output_radio_control_ul)
        self.add_out_port(self.output_radio_transport_ul)

        self.output_repeat_location = Port(str, 'output_repeat_location')
        self.output_service_delay_report = Port(ServiceDelayReport, 'output_service_delay_report')
        self.add_out_port(self.output_repeat_location)
        self.add_out_port(self.output_service_delay_report)

        self.external_couplings_antenna(antenna)
        self.external_couplings_access(access_manager)
        for service in services:
            self.external_couplings_service(service)

        self.internal_couplings_antenna_access(antenna, access_manager)
        self.internal_couplings_antenna_mux(antenna, service_mux)
        for service in services:
            self.internal_couplings_antenna_service(antenna, service)
            self.internal_couplings_access_service(access_manager, service)
            self.internal_couplings_mux_service(service_mux, service)

    def external_couplings_antenna(self, antenna: UserEquipmentAntenna):
        self.add_coupling(self.input_radio_bc, antenna.input_radio_bc)
        self.add_coupling(self.input_radio_control_dl, antenna.input_radio_control_dl)
        self.add_coupling(self.input_radio_transport_dl, antenna.input_radio_transport_dl)
        self.add_coupling(antenna.output_radio_control_ul, self.output_radio_control_ul)
        self.add_coupling(antenna.output_radio_transport_ul, self.output_radio_transport_ul)

    def external_couplings_service(self, service: Service):
        self.add_coupling(service.output_service_delay_report, self.output_service_delay_report)

    def external_couplings_access(self, access: AccessManager):
        self.add_coupling(access.output_repeat_location, self.output_repeat_location)

    def internal_couplings_antenna_access(self, antenna: UserEquipmentAntenna, access_manager: AccessManager):
        self.add_coupling(antenna.output_pss, access_manager.input_pss)
        self.add_coupling(antenna.output_access_response, access_manager.input_access_response)
        self.add_coupling(antenna.output_disconnect_response, access_manager.input_disconnect_response)
        self.add_coupling(antenna.output_ho_started, access_manager.input_ho_started)
        self.add_coupling(antenna.output_ho_finished, access_manager.input_ho_finished)
        self.add_coupling(access_manager.output_access_request, antenna.input_access_request)
        self.add_coupling(access_manager.output_disconnect_request, antenna.input_disconnect_request)
        self.add_coupling(access_manager.output_rrc, antenna.input_rrc)
        self.add_coupling(access_manager.output_ho_ready, antenna.input_ho_ready)
        self.add_coupling(access_manager.output_ho_response, antenna.input_ho_response)
        self.add_coupling(access_manager.output_connected_ap, antenna.input_connected_ap)
        self.add_coupling(access_manager.output_antenna_powered, antenna.input_antenna_powered)

    def internal_couplings_antenna_service(self, antenna: UserEquipmentAntenna, service: Service):
        self.add_coupling(service.output_network, antenna.input_service)

    def internal_couplings_antenna_mux(self, antenna: UserEquipmentAntenna, service_mux: UEServiceMux):
        self.add_coupling(antenna.output_service, service_mux.input_network)

    def internal_couplings_mux_service(self, service_mux: UEServiceMux, service: Service):
        service_id = service.service_id
        self.add_coupling(service_mux.outputs_network[service_id], service.input_network)

    def internal_couplings_access_service(self, access_manager: AccessManager, service: Service):
        self.add_coupling(access_manager.output_connected_ap, service.input_connected_ap)
        self.add_coupling(service.output_service_required, access_manager.input_service_required)


class UserEquipmentLite(Coupled):
    def __init__(self, name: str, ue_config: UserEquipmentConfiguration,
                 network_config: NetworkPacketConfiguration, core_id: str, t_initial: float = 0):
        super().__init__(name)

        ue_id = ue_config.ue_id
        service_config_list = ue_config.service_config_list
        service_ids = [service_config.service_id for service_config in service_config_list]

        self.ue_id = ue_id

        # Define and add components
        services = [Service(name + service.service_id, ue_id, service, network_config, t_initial, lite_id=core_id)
                    for service in service_config_list]
        [self.add_component(service) for service in services]

        self.input_network = Port(NetworkPacket, 'input_network')
        self.output_network = Port(NetworkPacket, 'output_network')
        self.output_service_delay_report = Port(ServiceDelayReport, 'output_service_delay_report')
        self.add_in_port(self.input_network)
        self.add_out_port(self.output_network)
        self.add_out_port(self.output_service_delay_report)

        if len(services) > 1:  # More than one service -> we add a multiplexer
            service_mux = UEServiceMux(name + '_service_mux', service_ids)
            self.add_component(service_mux)
            self.add_coupling(self.input_network, service_mux.input_network)
            for service in services:
                self.add_coupling(service_mux.outputs_network[service.service_id], service.input_network)
        else:  # Otherwise, multiplexer is not required
            self.add_coupling(self.input_network, services[0].input_network)
        for service in services:
            self.add_coupling(service.output_network, self.output_network)
            self.add_coupling(service.output_service_delay_report, self.output_service_delay_report)
