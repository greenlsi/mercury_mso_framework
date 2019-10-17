from random import uniform
from .packet.application.service import ServiceConfiguration
from .radio import RadioAntennaConfig
from .mobility import UEMobilityConfiguration


class IoTDevicesLayerConfiguration:
    """
    IoT Devices Layer Configuration

    :param dict ue_configuration_list: list of UE configurations {UE ID: UE Configuration}
    :param float max_guard_time: Maximum guard time to be awaited by UEs at the beginning of the simulation
    """
    def __init__(self, ue_configuration_list, max_guard_time=0):
        for configuration in ue_configuration_list.values():
            assert isinstance(configuration, UserEquipmentConfiguration)
        self.ue_config_list = ue_configuration_list
        assert max_guard_time >= 0
        self.guard_time_generator = GuardTimeGenerator(max_guard_time)


class UserEquipmentConfiguration:
    def __init__(self, ue_id, service_config_list, ue_mobility_config, antenna_config):
        """
        User Equipment Configuration

        :param str ue_id: ID of the User Equipment
        :param list service_config_list: List of the configuration of all the services_config within a User Equipment
        :param UEMobilityConfiguration ue_mobility_config: User Equipment Mobility Configuration
        :param RadioAntennaConfig antenna_config: radio antenna configuration for the UE
        """
        self.ue_id = ue_id
        for service_config in service_config_list:
            assert isinstance(service_config, ServiceConfiguration)
        self.service_config_list = service_config_list
        self.ue_mobility_config = ue_mobility_config
        self.antenna_config = antenna_config


class GuardTimeGenerator:
    """
    UE Guard time generator.
    The method guard_time() returns a random number within a uniform distribution.

    :param float max_guard_time: upper limit of the uniform distribution
    """
    def __init__(self, max_guard_time):
        assert max_guard_time >= 0
        self.max_guard_time = max_guard_time

    def guard_time(self):
        return uniform(0, self.max_guard_time)
