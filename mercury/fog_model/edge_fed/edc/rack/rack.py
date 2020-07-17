from xdevs.models import Coupled, Port
from ..internal_ports import ChangeStatus, ChangeStatusResponse, SetDVFSMode, SetDVFSModeResponse, OpenSessionRequest,\
    OpenSessionResponse, OngoingSessionRequest, OngoingSessionResponse, CloseSessionRequest, CloseSessionResponse
from ....common.edge_fed.rack import RackConfiguration, RackReport
from .pu import ProcessingUnit
from .rack_node import RackNode
from .pu_mux import ProcessingUnitMultiplexer


class Rack(Coupled):
    """
    :param name:
    :param RackConfiguration rack_config:
    :param dict services_config:
    :param float env_temp:
    """
    def __init__(self, name, rack_config, services_config, env_temp):
        super().__init__(name)

        self.input_change_status = Port(ChangeStatus, name + '_input_change_status')
        self.input_set_dvfs_mode = Port(SetDVFSMode, name + '_input_set_dvfs_mode')
        self.input_open_session = Port(OpenSessionRequest, name + '_input_open_session')
        self.input_ongoing_session = Port(OngoingSessionRequest, name + '_input_ongoing_session')
        self.input_close_session = Port(CloseSessionRequest, name + '_input_close_session')
        self.output_change_status_response = Port(ChangeStatusResponse, name + '_output_change_status_response')
        self.output_set_dvfs_mode_response = Port(SetDVFSModeResponse, name + '_output_set_dvfs_mode_response')
        self.output_open_session_response = Port(OpenSessionResponse, name + '_output_open_session_response')
        self.output_ongoing_session_response = Port(OngoingSessionResponse, name + '_output_ongoing_session_response')
        self.output_close_session_response = Port(CloseSessionResponse, name + '_output_close_session_response')
        self.output_rack_report = Port(RackReport, name + '_output_rack_report')

        self.add_in_port(self.input_change_status)               # port for incoming change status messages
        self.add_in_port(self.input_set_dvfs_mode)               # port for incoming new DVFS mode messages
        self.add_in_port(self.input_open_session)                # port for incoming open session messages
        self.add_in_port(self.input_ongoing_session)             # port for incoming ongoing session messages
        self.add_in_port(self.input_close_session)               # port for incoming close session messages
        self.add_out_port(self.output_change_status_response)    # port for leaving change status response messages
        self.add_out_port(self.output_set_dvfs_mode_response)    # port for leaving new DVFS mode response messages
        self.add_out_port(self.output_open_session_response)     # port for leaving open session response messages
        self.add_out_port(self.output_ongoing_session_response)  # port for leafing ongoing session response messages
        self.add_out_port(self.output_close_session_response)    # port for leaving close session response messages
        self.add_out_port(self.output_rack_report)               # Port for leaving rack report messages

        self.rack_id = rack_config.rack_id
        rack_node_config = rack_config.rack_node_config
        rack_node = RackNode(name, self.rack_id, rack_node_config, env_temp)
        n_pu = len(rack_config.pu_config_list)
        p_units = [ProcessingUnit(name+'_pu_'+str(i), rack_config.pu_config_list[i], rack_config.rack_id, i,
                                  services_config, env_temp)
                   for i in range(n_pu)]
        p_unit_mux = ProcessingUnitMultiplexer(name + '_pu_mux', n_pu)

        self.add_component(rack_node)
        [self.add_component(p_unit) for p_unit in p_units]
        self.add_component(p_unit_mux)

        self.external_couplings_rack_node(rack_node)
        self.external_couplings_mux(p_unit_mux)
        for p_unit in p_units:
            self.external_couplings_pu(p_unit)
            self.internal_couplings_pu_mux(p_unit, p_unit_mux)
            self.internal_couplings_pu_rack_node(p_unit, rack_node)

    def external_couplings_rack_node(self, rack_node):
        """
        :param RackNode rack_node:
        """
        self.add_coupling(rack_node.output_rack_report, self.output_rack_report)

    def external_couplings_mux(self, p_unit_mux):
        """
        :param ProcessingUnitMultiplexer p_unit_mux:
        """
        self.add_coupling(self.input_change_status, p_unit_mux.input_change_status)
        self.add_coupling(self.input_set_dvfs_mode, p_unit_mux.input_set_dvfs_mode)
        self.add_coupling(self.input_open_session, p_unit_mux.input_open_session)
        self.add_coupling(self.input_ongoing_session, p_unit_mux.input_ongoing_session)
        self.add_coupling(self.input_close_session, p_unit_mux.input_close_session)

    def external_couplings_pu(self, p_unit):
        """
        :param ProcessingUnit p_unit:
        """
        self.add_coupling(p_unit.output_change_status_response, self.output_change_status_response)
        self.add_coupling(p_unit.output_set_dvfs_mode_response, self.output_set_dvfs_mode_response)
        self.add_coupling(p_unit.output_open_session_response, self.output_open_session_response)
        self.add_coupling(p_unit.output_ongoing_session_response, self.output_ongoing_session_response)
        self.add_coupling(p_unit.output_close_session_response, self.output_close_session_response)

    def internal_couplings_pu_mux(self, p_unit, p_unit_mux):
        """
        :param ProcessingUnit p_unit:
        :param ProcessingUnitMultiplexer p_unit_mux:
        """
        pu_index = p_unit.pu_index
        self.add_coupling(p_unit_mux.outputs_change_status[pu_index], p_unit.input_change_status)
        self.add_coupling(p_unit_mux.outputs_set_dvfs_mode[pu_index], p_unit.input_set_dvfs_mode)
        self.add_coupling(p_unit_mux.outputs_open_session[pu_index], p_unit.input_open_session)
        self.add_coupling(p_unit_mux.outputs_ongoing_session[pu_index], p_unit.input_ongoing_session)
        self.add_coupling(p_unit_mux.outputs_close_session[pu_index], p_unit.input_close_session)

    def internal_couplings_pu_rack_node(self, p_unit, rack_node):
        """
        :param ProcessingUnit p_unit:
        :param RackNode rack_node:
        """
        self.add_coupling(p_unit.output_p_unit_report, rack_node.input_pu_report)
