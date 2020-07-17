class ProcessingUnitReport:
    """
    Processing Unit report
    :param str rack_id: Rack ID
    :param int pu_index: Processing Unit index within the rack
    :param str pu_id: ID of the processing unit model
    :param float max_u: maximum utilization factor
    :param int max_start_stop: maximum number of services that can be simultaneously started and/or stopped
    :param bool status: Status of the Processing Unit (true if switched on)
    :param bool dvfs_mode: Indicates whether DVFS mode is powered on or not
    :param int dvfs_index: Indicates which DVFS configuration is being used
    :param float utilization: utilization of computation resources
    :param float power: power consumption of processing unit
    :param float temperature: temperature of processing unit
    :param dict ongoing_sessions:
    :param dict u_per_service:
    """
    def __init__(self, rack_id: str, pu_index: int, pu_id: str, max_u: float, max_start_stop: int, status: bool,
                 dvfs_mode: bool, dvfs_index: int, utilization: float, power: float, temperature: float,
                 ongoing_sessions: dict, u_per_service: dict):
        self.rack_id = rack_id
        self.pu_index = pu_index
        self.pu_id = pu_id
        self.max_u = max_u
        self.max_start_stop = max_start_stop
        self.status = status
        self.dvfs_mode = dvfs_mode
        self.dvfs_index = dvfs_index
        self.utilization = utilization
        self.power = power
        self.temperature = temperature
        self.ongoing_sessions = ongoing_sessions
        self.u_per_service = u_per_service


class ProcessingUnitConfiguration:
    """
    Processing Unit Configuration
    :param str p_unit_id: Processing unit model ID
    :param dict dvfs_table: dictionary containing DVFS table {std_u_1: {dvfs_conf_1}, ..., 100: {dvfs_conf_N}}
    :param float max_u: maximum utilization factor
    :param int max_start_stop: maximum number of services that can be simultaneously being started and/or stopped
    :param float t_on: time required by the processing unit for switching on
    :param float t_off: time required by the processing unit to switching off
    :param float t_start: time required by the processing unit to start a service
    :param float t_stop: time required by the processing unit to stop a service
    :param float t_operation: time required by the processing unit to perform an operation of an ongoing service
    :param str power_model_name: Power consumption model name
    :param dict power_model_config: Configuration parameters of power consumption model
    :param str temp_model_name: Temperature model name
    :param dict temp_model_config: Configuration parameters of temperature model
    """
    def __init__(self, p_unit_id, dvfs_table=None, max_u=100, max_start_stop=0, t_on=0, t_off=0, t_start=0, t_stop=0,
                 t_operation=0, power_model_name=None, power_model_config=None, temp_model_name=None,
                 temp_model_config=None):
        if dvfs_table is None:
            dvfs_table = {100: {}}
        try:
            assert 100 in dvfs_table
            assert max_u > 0
            assert max_start_stop >= 0
            assert t_on >= 0
            assert t_off >= 0
            assert t_start >= 0
            assert t_stop >= 0
            assert t_operation >= 0
        except AssertionError:
            raise ValueError("Processing Unit Configuration values are invalid")
        self.p_unit_id = p_unit_id
        self.dvfs_table = dvfs_table
        self.max_u = max_u
        self.max_start_stop = max_start_stop
        self.t_on = t_on
        self.t_off = t_off
        self.t_start = t_start
        self.t_stop = t_stop
        self.t_operation = t_operation
        self.power_model_name = power_model_name
        self.power_model_config = power_model_config if power_model_config is not None else dict()
        self.temp_model_name = temp_model_name
        self.temp_model_config = temp_model_config if temp_model_config is not None else dict()
