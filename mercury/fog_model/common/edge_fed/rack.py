class RackNodeConfiguration:
    """
    Configuration for rack node (it is related to cooling)
    """
    def __init__(self, type_id: str, temp_model_name=None, temp_model_config=None, pwr_model_name=None,
                 pwr_model_config=None):
        self.type_id = type_id
        self.temp_model_name = temp_model_name
        self.pwr_model_name = pwr_model_name
        if temp_model_config is None:
            temp_model_config = dict()
        self.temp_model_config = temp_model_config
        if pwr_model_config is None:
            pwr_model_config = dict()
        self.pwr_model_config = pwr_model_config


class RackConfiguration:
    """
    Configuration for EDCs' rack
    :param rack_id: Rack ID
    :param pu_config_list: dictionary with the configuration of all the PUs that compose the rack
    :param rack_node_config: rack node configuration
    """
    def __init__(self, rack_id: str, pu_config_list: list, rack_node_config: RackNodeConfiguration):
        self.rack_id = rack_id
        self.pu_config_list = pu_config_list
        self.rack_node_config = rack_node_config


class RackReport:
    """
    :param rack_id: Rack ID
    :param utilization: Rack standard utilization factor
    :param max_u: Maximum rack standard utilization factor
    :param temperature: Rack temperature
    :param overall_power: Rack overall power
    :param it_power: Power consumption of all the processing units
    :param cooling_power: power required by the rack for refrigerating the processing units
    :param pu_report_list: dictionary containing the reports of all the processing units within the rack
    """
    def __init__(self, rack_id: str, utilization: float, max_u: float, temperature: float, overall_power: float,
                 it_power: float, cooling_power: float, pu_report_list: dict):
        self.rack_id = rack_id
        self.utilization = utilization
        self.max_u = max_u
        self.rack_temp = temperature
        self.overall_power = overall_power
        self.it_power = it_power
        self.cooling_power = cooling_power
        self.pu_report_list = pu_report_list
        self.u_per_service = dict()
        for pu_index, pu_report in pu_report_list.items():
            for service_id, utilization in pu_report.u_per_service.items():
                if service_id not in self.u_per_service:
                    self.u_per_service[service_id] = 0
                self.u_per_service[service_id] += utilization
