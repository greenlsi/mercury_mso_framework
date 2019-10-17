import logging
from xdevs.models import Port
from .internal_interfaces import ServiceRequired
from ...common import Stateless, logging_overhead
from ...common.mobility import UEMobilityConfiguration, NewLocation

LOGGING_OVERHEAD = ""


class UserEquipmentMobility(Stateless):
    """
    User Equipment Mobility xDEVS module

    :param str name: name of the xDEVS module
    :param str ue_id: ID of the UE
    :param UEMobilityConfiguration ue_mobility_config: UE mobility configuration
    """
    def __init__(self, name, ue_id, ue_mobility_config):
        super().__init__(0, name)
        self.ue_id = ue_id
        if not isinstance(ue_mobility_config, UEMobilityConfiguration):
            raise TypeError('User Equipment Mobility Configuration wrong type')
        self.ue_mobility_config = ue_mobility_config
        self.ue_location = ue_mobility_config.position

        self.input_service_required = Port(ServiceRequired, name + '_input_service_required')
        self.output_new_location = Port(NewLocation, name + '_output_new_location')
        self.add_in_port(self.input_service_required)
        self.add_out_port(self.output_new_location)

    def check_in_ports(self):
        for service_required in self.input_service_required.values:
            if service_required.required:
                self.add_msg_to_queue(self.output_new_location, NewLocation(self.ue_id, self.ue_location))
                break

    def process_internal_messages(self):
        if self.msg_queue_empty():
            self.ue_location = self.ue_mobility_config.get_location_and_advance()
            overhead = logging_overhead(self._clock, LOGGING_OVERHEAD)
            ue_id = self.ue_id
            ue_location = self.ue_location
            logging.info(overhead + '%s moved to location (%.2f, %.2f)' % (ue_id, ue_location[0], ue_location[1]))
            self.add_msg_to_queue(self.output_new_location, NewLocation(ue_id, ue_location))

    def get_next_timeout(self):
        return 0 if not self.msg_queue_empty() else self.ue_mobility_config.get_next_sigma(self._clock)
