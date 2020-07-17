from typing import Dict
from random import uniform
from xdevs.models import Coupled, Port
from .ue import UserEquipment, UserEquipmentLite, UserEquipmentConfiguration
from ..common.packet.apps.ran import RadioAccessNetworkConfiguration
from ..common.packet.apps.service import ServiceDelayReport
from ..common.packet.packet import NetworkPacketConfiguration, PhysicalPacket, NetworkPacket


class GuardTimeGenerator:
    def __init__(self, max_guard_time: float):
        """
        UE Guard time generator.
        :param max_guard_time: upper limit of the uniform distribution
        """
        assert max_guard_time >= 0
        self.max_guard_time = max_guard_time

    def guard_time(self):
        """returns a random number within a uniform distribution"""
        return uniform(0, self.max_guard_time)


class IoTDevicesLayerConfiguration:
    """
    IoT Devices Layer Configuration
    :param ues_config: list of UE configurations {UE ID: UE Configuration}
    :param max_guard_time: Maximum guard time to be awaited by UEs at the beginning of the simulation
    """
    def __init__(self, ues_config: Dict[str, UserEquipmentConfiguration], max_guard_time=0):
        self.ues_config = ues_config
        assert max_guard_time >= 0
        self.guard_time_generator = GuardTimeGenerator(max_guard_time)


class IoTDevices(Coupled):
    """
    IoT Devices Layer xDEVS model

    :param name: XDEVS module name
    :param iot_layer_config: Fog Layer Configuration
    :param rac_config: Radio Access Control Service configuration
    :param network_config: Network packets configuration
    """
    def __init__(self, name: str, iot_layer_config: IoTDevicesLayerConfiguration,
                 rac_config: RadioAccessNetworkConfiguration, network_config: NetworkPacketConfiguration):

        super().__init__(name)

        # Unpack configuration parameters
        ue_config_list = iot_layer_config.ues_config
        guard_time_generator = iot_layer_config.guard_time_generator

        # Check that UE IDs are unique
        self.ue_ids = [ue_id for ue_id in ue_config_list]
        if len(self.ue_ids) != len(set(self.ue_ids)):
            raise ValueError('UE IDs must be unique')

        # Start and add components
        ues = {ue_id: UserEquipment(name + '_ue_' + ue_id, ue_config, rac_config, network_config,
                                    guard_time_generator.guard_time()) for ue_id, ue_config in ue_config_list.items()}

        [self.add_component(ue) for ue in ues.values()]

        self.output_repeat_location = Port(str, 'output_repeat_location')
        self.output_service_delay_report = Port(ServiceDelayReport, 'output_service_delay_report')
        self.output_radio_control_ul = Port(PhysicalPacket, 'output_radio_control_ul')
        self.output_radio_transport_ul = Port(PhysicalPacket, 'output_radio_transport_ul')
        self.add_out_port(self.output_repeat_location)
        self.add_out_port(self.output_service_delay_report)
        self.add_out_port(self.output_radio_control_ul)
        self.add_out_port(self.output_radio_transport_ul)

        # Define I/O ports
        self.inputs_radio_bc = dict()
        self.inputs_radio_control_dl = dict()
        self.inputs_radio_transport_dl = dict()

        for ue_id, ue in ues.items():
            assert isinstance(ue, UserEquipment)
            self.inputs_radio_bc[ue_id] = Port(PhysicalPacket, 'input_radio_bc_' + ue_id)
            self.inputs_radio_control_dl[ue_id] = Port(PhysicalPacket, 'input_radio_control_dl_' + ue_id)
            self.inputs_radio_transport_dl[ue_id] = Port(PhysicalPacket, 'input_radio_transport_dl_' + ue_id)

            self.add_in_port(self.inputs_radio_bc[ue_id])
            self.add_in_port(self.inputs_radio_control_dl[ue_id])
            self.add_in_port(self.inputs_radio_transport_dl[ue_id])

            self.add_coupling(ue.output_repeat_location, self.output_repeat_location)
            self.add_coupling(ue.output_service_delay_report, self.output_service_delay_report)

            self.add_coupling(self.inputs_radio_bc[ue_id], ue.input_radio_bc)
            self.add_coupling(self.inputs_radio_control_dl[ue_id], ue.input_radio_control_dl)
            self.add_coupling(self.inputs_radio_transport_dl[ue_id], ue.input_radio_transport_dl)
            self.add_coupling(ue.output_radio_control_ul, self.output_radio_control_ul)
            self.add_coupling(ue.output_radio_transport_ul, self.output_radio_transport_ul)


class IoTDevicesLite(Coupled):
    def __init__(self, name: str, iot_layer_config: IoTDevicesLayerConfiguration,
                 network_config: NetworkPacketConfiguration, core_id: str):
        super().__init__(name)
        # Unpack configuration parameters
        ue_config_list = iot_layer_config.ues_config
        guard_generator = iot_layer_config.guard_time_generator

        # Check that UE IDs are unique
        self.ue_ids = [ue_id for ue_id in ue_config_list]
        if len(self.ue_ids) != len(set(self.ue_ids)):
            raise ValueError('UE IDs must be unique')

        # Start and add components
        ues = {ue_id: UserEquipmentLite(name + '_ue_' + ue_id, ue_config, network_config, core_id,
                                        guard_generator.guard_time())
               for ue_id, ue_config in ue_config_list.items()}
        [self.add_component(ue) for ue in ues.values()]

        self.output_network = Port(NetworkPacket, 'output_network')
        self.output_service_delay_report = Port(ServiceDelayReport, 'output_service_delay_report')
        self.add_out_port(self.output_network)
        self.add_out_port(self.output_service_delay_report)

        self.inputs_network = dict()
        for ue_id in ues:
            self.inputs_network[ue_id] = Port(NetworkPacket, 'input_network_' + ue_id)
            self.add_in_port(self.inputs_network[ue_id])
            self.add_coupling(self.inputs_network[ue_id], ues[ue_id].input_network)
            self.add_coupling(ues[ue_id].output_network, self.output_network)
            self.add_coupling(ues[ue_id].output_service_delay_report, self.output_service_delay_report)
