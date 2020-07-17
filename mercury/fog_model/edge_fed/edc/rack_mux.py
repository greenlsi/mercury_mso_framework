from xdevs.models import Port
from ...common import Multiplexer
from .internal_ports import ChangeStatus, SetDVFSMode, OpenSessionRequest, OngoingSessionRequest, CloseSessionRequest


class RackMultiplexer(Multiplexer):
    """
    Processing unit multiplexer for edge data centers
    :param str name: name of the xDEVS module
    :param list rack_ids: List of racks withing the Edge Data Center
    """
    def __init__(self, name, rack_ids):
        self.input_change_status = Port(ChangeStatus, name + '_input_change_status')
        self.input_set_dvfs_mode = Port(SetDVFSMode, name + '_input_set_dvfs_mode')
        self.input_open_session = Port(OpenSessionRequest, name + '_input_create_session')
        self.input_ongoing_session = Port(OngoingSessionRequest, name + '_input_ongoing_session')
        self.input_close_session = Port(CloseSessionRequest, name + '_input_remove_session')

        self.outputs_change_status = {rack_id: Port(ChangeStatus, name + '_output_change_status_' + rack_id)
                                      for rack_id in rack_ids}
        self.outputs_set_dvfs_mode = {rack_id: Port(SetDVFSMode, name + '_output_set_dvfs_mode_' + rack_id)
                                      for rack_id in rack_ids}
        self.outputs_open_session = {rack_id: Port(OpenSessionRequest, name + '_output_open_session_' + rack_id)
                                     for rack_id in rack_ids}
        self.outputs_ongoing_session = {rack_id: Port(OngoingSessionRequest, name + '_output_ongoing_session_' + rack_id)
                                        for rack_id in rack_ids}
        self.outputs_close_session = {rack_id: Port(CloseSessionRequest, name + '_output_close_session_' + rack_id)
                                      for rack_id in rack_ids}

        super().__init__(name, rack_ids)

        self.add_in_port(self.input_change_status)
        self.add_in_port(self.input_set_dvfs_mode)
        self.add_in_port(self.input_open_session)
        self.add_in_port(self.input_ongoing_session)
        self.add_in_port(self.input_close_session)

        [self.add_out_port(port) for port in self.outputs_change_status.values()]
        [self.add_out_port(port) for port in self.outputs_set_dvfs_mode.values()]
        [self.add_out_port(port) for port in self.outputs_open_session.values()]
        [self.add_out_port(port) for port in self.outputs_ongoing_session.values()]
        [self.add_out_port(port) for port in self.outputs_close_session.values()]

    def build_routing_table(self):
        """Build routing table"""
        self.routing_table[self.input_change_status] = dict()
        self.routing_table[self.input_set_dvfs_mode] = dict()
        self.routing_table[self.input_open_session] = dict()
        self.routing_table[self.input_ongoing_session] = dict()
        self.routing_table[self.input_close_session] = dict()

        for rack_id in self.node_id_list:
            self.routing_table[self.input_change_status][rack_id] = self.outputs_change_status[rack_id]
            self.routing_table[self.input_set_dvfs_mode][rack_id] = self.outputs_set_dvfs_mode[rack_id]
            self.routing_table[self.input_open_session][rack_id] = self.outputs_open_session[rack_id]
            self.routing_table[self.input_ongoing_session][rack_id] = self.outputs_ongoing_session[rack_id]
            self.routing_table[self.input_close_session][rack_id] = self.outputs_close_session[rack_id]

    def get_node_to(self, msg):
        return msg.rack_id
