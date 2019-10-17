from xdevs.models import Coupled, Port
from .ue import UserEquipment
from .ue_mux import UserEquipmentMultiplexer
from ..common.mobility import NewLocation
from ..common.iot_devices import IoTDevicesLayerConfiguration
from ..common.packet.application.ran import RadioAccessNetworkConfiguration
from ..common.packet.application.ran.ran_access import NewDownLinkMCS
from ..common.packet.application.service import ServiceDelayReport
from ..common.packet.network import NetworkPacketConfiguration
from ..common.radio import RadioConfiguration
from ..common.packet.physical import PhysicalPacket


class IoTDevices(Coupled):
    """
    IoT Devices Layer xDEVS model

    :param str name: XDEVS module name
    :param IoTDevicesLayerConfiguration iot_layer_config: Fog Layer Configuration
    :type iot_layer_config: IoTDevicesLayerConfiguration
    :param RadioAccessNetworkConfiguration rac_config: Radio Access Control Service configuration
    :param NetworkPacketConfiguration network_config: Network packets configuration
    :param RadioConfiguration radio_config: Radio interface configuration
    """
    def __init__(self, name, iot_layer_config, rac_config, network_config, radio_config):

        super().__init__(name)

        # Unpack configuration parameters
        ue_config_list = iot_layer_config.ue_config_list
        guard_time_generator = iot_layer_config.guard_time_generator

        # Check that UE IDs are unique
        ue_id_list = [ue_id for ue_id in ue_config_list]
        if len(ue_id_list) != len(set(ue_id_list)):
            raise ValueError('UE IDs must be unique')

        # Start and add components
        ue_mux = UserEquipmentMultiplexer(name + '_mux', ue_id_list)
        ues = [UserEquipment(name + '_ue_' + ue_id, ue_config, rac_config, network_config, radio_config,
                             guard_time_generator.guard_time()) for ue_id, ue_config in ue_config_list.items()]

        self.add_component(ue_mux)
        [self.add_component(ue) for ue in ues]

        # Define I/O ports
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

        self.external_couplings_ue_mux(ue_mux)
        for ue in ues:
            self.external_couplings_ue(ue)
            self.internal_couplings_ue_mux(ue, ue_mux)

    def external_couplings_ue_mux(self, ue_mux):
        """
        :param UserEquipmentMultiplexer ue_mux:
        """
        self.add_coupling(self.input_radio_bc, ue_mux.input_radio_bc)
        self.add_coupling(self.input_radio_control_dl, ue_mux.input_radio_control_dl)
        self.add_coupling(self.input_radio_transport_dl, ue_mux.input_radio_transport_dl)

    def external_couplings_ue(self, ue):
        """
        :param UserEquipment ue:
        """
        self.add_coupling(ue.output_radio_control_ul, self.output_radio_control_ul)
        self.add_coupling(ue.output_radio_transport_ul, self.output_radio_transport_ul)

        self.add_coupling(ue.output_new_location, self.output_new_location)
        self.add_coupling(ue.output_service_delay_report, self.output_service_delay_report)
        self.add_coupling(ue.output_dl_mcs, self.output_dl_mcs)

    def internal_couplings_ue_mux(self, ue, ue_mux):
        """
        :param UserEquipment ue:
        :param UserEquipmentMultiplexer ue_mux:
        """
        ue_id = ue.ue_id
        self.add_coupling(ue_mux.outputs_radio_bc[ue_id], ue.input_radio_bc)
        self.add_coupling(ue_mux.outputs_radio_control_dl[ue_id], ue.input_radio_control_dl)
        self.add_coupling(ue_mux.outputs_radio_transport_dl[ue_id], ue.input_radio_transport_dl)
