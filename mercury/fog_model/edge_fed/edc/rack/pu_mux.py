from xdevs.models import Port
from ....common import Multiplexer
from ..internal_ports import ChangeStatus, SetDVFSMode, OpenSessionRequest, OngoingSessionRequest, CloseSessionRequest


class ProcessingUnitMultiplexer(Multiplexer):
    """
    Processing unit multiplexer for edge data centers
    :param str name: name of the xDEVS module
    :param int n_pu: number of processing units within the data center
    """
    def __init__(self, name, n_pu):
        p_units = [i for i in range(n_pu)]
        self.input_change_status = Port(ChangeStatus, name + '_input_change_status')
        self.input_set_dvfs_mode = Port(SetDVFSMode, name + '_input_set_dvfs_mode')
        self.input_open_session = Port(OpenSessionRequest, name + '_input_create_session')
        self.input_ongoing_session = Port(OngoingSessionRequest, name + '_input_ongoing_session')
        self.input_close_session = Port(CloseSessionRequest, name + '_input_remove_session')

        self.outputs_change_status = [Port(ChangeStatus, name + '_output_change_status_' + str(i)) for i in p_units]
        self.outputs_set_dvfs_mode = [Port(SetDVFSMode, name + '_output_set_dvfs_mode_' + str(i)) for i in p_units]
        self.outputs_open_session = [Port(OpenSessionRequest, name + '_output_open_session_' + str(i)) for i in p_units]
        self.outputs_ongoing_session = [Port(OngoingSessionRequest, name + '_output_ongoing_session_' + str(i)) for
                                        i in p_units]
        self.outputs_close_session = [Port(CloseSessionRequest, name + '_output_close_session_' + str(i))
                                      for i in p_units]

        super().__init__(name, p_units)

        self.add_in_port(self.input_change_status)
        self.add_in_port(self.input_set_dvfs_mode)
        self.add_in_port(self.input_open_session)
        self.add_in_port(self.input_ongoing_session)
        self.add_in_port(self.input_close_session)

        [self.add_out_port(port) for port in self.outputs_change_status]
        [self.add_out_port(port) for port in self.outputs_set_dvfs_mode]
        [self.add_out_port(port) for port in self.outputs_open_session]
        [self.add_out_port(port) for port in self.outputs_ongoing_session]
        [self.add_out_port(port) for port in self.outputs_close_session]

    def build_routing_table(self):
        """Build routing table"""
        self.routing_table[self.input_change_status] = dict()
        self.routing_table[self.input_set_dvfs_mode] = dict()
        self.routing_table[self.input_open_session] = dict()
        self.routing_table[self.input_ongoing_session] = dict()
        self.routing_table[self.input_close_session] = dict()

        for pu_index in self.node_id_list:
            self.routing_table[self.input_change_status][pu_index] = self.outputs_change_status[pu_index]
            self.routing_table[self.input_set_dvfs_mode][pu_index] = self.outputs_set_dvfs_mode[pu_index]
            self.routing_table[self.input_open_session][pu_index] = self.outputs_open_session[pu_index]
            self.routing_table[self.input_ongoing_session][pu_index] = self.outputs_ongoing_session[pu_index]
            self.routing_table[self.input_close_session][pu_index] = self.outputs_close_session[pu_index]

    def get_node_to(self, msg):
        return msg.pu_index
