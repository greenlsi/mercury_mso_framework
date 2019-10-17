from xdevs.models import Coupled, Port
from ...common.iot_devices import UserEquipmentConfiguration
from ...common.mobility import NewLocation
from ...common.radio import RadioConfiguration
from ...common.packet.physical import PhysicalPacket
from ...common.packet.network import NetworkPacketConfiguration
from ...common.packet.application.ran import RadioAccessNetworkConfiguration
from ...common.packet.application.service import ServiceDelayReport
from ...common.packet.application.ran.ran_access import NewDownLinkMCS
from .ue_antenna import UserEquipmentAntenna
from .ue_mobility import UserEquipmentMobility
from .service_mux import UEServiceMux
from .service import Service
from .access_manager import AccessManager


class UserEquipment(Coupled):
    def __init__(self, name, ue_config, rac_config, network_config, radio_config, t_initial=0):
        """
        User Equipment xDEVS model

        :param str name: xDEVS model name
        :param UserEquipmentConfiguration ue_config: User Equipment Configuration
        :param RadioAccessNetworkConfiguration rac_config: Radio Access Network service packets configuration
        :param NetworkPacketConfiguration network_config: Network packets configuration
        :param RadioConfiguration radio_config: Radio Channels configuration
        :param float t_initial: Initial guard time in order to avoid identical simultaneous behavior between UEs
        """
        super().__init__(name)

        # Unpack configuration parameters
        ue_id = ue_config.ue_id
        service_config_list = ue_config.service_config_list
        ue_mobility_config = ue_config.ue_mobility_config
        antenna_config = ue_config.antenna_config
        service_ids = [service_config.service_id for service_config in service_config_list]

        self.ue_id = ue_id

        # Define and add components
        mobility = UserEquipmentMobility(name + '_mobility', ue_id, ue_mobility_config)
        antenna = UserEquipmentAntenna(name + '_antenna', ue_id, network_config, radio_config, antenna_config)
        access_manager = AccessManager(name + '_access_manager', ue_id, rac_config)
        service_mux = UEServiceMux(name + '_service_mux', service_ids)
        services = [Service(name + service.service_id, ue_id, service, network_config, t_initial)
                    for service in service_config_list]
        self.add_component(mobility)
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

        self.output_new_location = Port(NewLocation, name + '_output_new_location')
        self.output_service_delay_report = Port(ServiceDelayReport, name + '_output_service_delay_report')
        self.output_dl_mcs = Port(NewDownLinkMCS, name + '_output_new_dl_mcs')
        self.add_out_port(self.output_new_location)
        self.add_out_port(self.output_service_delay_report)
        self.add_out_port(self.output_dl_mcs)

        self.external_couplings_antenna(antenna)
        self.external_couplings_mobility(mobility)
        for service in services:
            self.external_couplings_service(service)

        self.internal_couplings_antenna_access(antenna, access_manager)
        self.internal_couplings_antenna_mux(antenna, service_mux)
        for service in services:
            self.internal_couplings_antenna_service(antenna, service)
            self.internal_coupling_service_mobility(service, mobility)
            self.internal_couplings_access_service(access_manager, service)
            self.internal_couplings_mux_service(service_mux, service)

    def external_couplings_antenna(self, antenna):
        """
        :param UserEquipmentAntenna antenna:
        """
        self.add_coupling(self.input_radio_bc, antenna.input_radio_bc)
        self.add_coupling(self.input_radio_control_dl, antenna.input_radio_control_dl)
        self.add_coupling(self.input_radio_transport_dl, antenna.input_radio_transport_dl)
        self.add_coupling(antenna.output_radio_control_ul, self.output_radio_control_ul)
        self.add_coupling(antenna.output_radio_transport_ul, self.output_radio_transport_ul)
        self.add_coupling(antenna.output_dl_mcs, self.output_dl_mcs)

    def external_couplings_mobility(self, mobility):
        """
        :param UserEquipmentMobility mobility:
        """
        self.add_coupling(mobility.output_new_location, self.output_new_location)

    def external_couplings_service(self, service):
        """
        :param Service service:
        """
        self.add_coupling(service.output_service_delay_report, self.output_service_delay_report)

    def internal_couplings_antenna_access(self, antenna, access_manager):
        """
        :param UserEquipmentAntenna antenna:
        :param AccessManager access_manager:
        """
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

    def internal_couplings_antenna_service(self, antenna, service):
        """
        :param UserEquipmentAntenna antenna:
        :param Service service:
        """
        self.add_coupling(service.output_network, antenna.input_service)

    def internal_couplings_antenna_mux(self, antenna, service_mux):
        """
        :param UserEquipmentAntenna antenna:
        :param UEServiceMux service_mux:
        """
        self.add_coupling(antenna.output_service, service_mux.input_network)

    def internal_couplings_mux_service(self, service_mux, service):
        """
        :param UEServiceMux service_mux:
        :param Service service:
        """
        service_id = service.service_id
        self.add_coupling(service_mux.outputs_network[service_id], service.input_network)

    def internal_couplings_access_service(self, access_manager, service):
        """
        :param AccessManager access_manager:
        :param Service service:
        """
        self.add_coupling(access_manager.output_connected_ap, service.input_connected_ap)
        self.add_coupling(service.output_service_required, access_manager.input_service_required)

    def internal_coupling_service_mobility(self, service, mobility):
        """
        :param Service service:
        :param UserEquipmentMobility mobility:
        """
        self.add_coupling(service.output_service_required, mobility.input_service_required)
