from copy import deepcopy
from xdevs.models import Port
from .....common import Stateless
from .....common.edge_fed.pu import ProcessingUnitReport
from .....common.edge_fed.rack import RackNodeConfiguration, RackReport
from .rack_pwr import RackPowerModelFactory
from .rack_temp import RackTemperatureModelFactory


class RackNode(Stateless):
    """
    rack node model for xDEVS
    :param name: name of the XDEVS module
    :param rack_node_config: Rack Node configuration
    :param env_temp: Environment base temperature (in Kelvin)
    """
    rack_power_factory = RackPowerModelFactory()
    rack_temp_factory = RackTemperatureModelFactory()

    def __init__(self, name: str, rack_id: str, rack_node_config: RackNodeConfiguration, env_temp: float):
        self.rack_id = rack_id
        temp_model_name = rack_node_config.temp_model_name
        power_model_name = rack_node_config.pwr_model_name
        temp_model_config = rack_node_config.temp_model_config
        power_model_config = rack_node_config.pwr_model_config

        self.temp_model = self.rack_temp_factory.create_model(temp_model_name, **temp_model_config)
        self.power_model = self.rack_power_factory.create_model(power_model_name, **power_model_config)

        self.utilization = 0
        self.max_u = 0
        self.pu_reports = dict()
        self.power = 0
        self.temp = env_temp
        self.env_temp = env_temp

        self.input_pu_report = Port(ProcessingUnitReport, name + '_input_pu_report')
        self.output_rack_report = Port(RackReport, name + '_output_rack_report')
        super().__init__(name=name)
        self.add_in_port(self.input_pu_report)
        self.add_out_port(self.output_rack_report)

    def check_in_ports(self):
        if self.input_pu_report:
            for job in self.input_pu_report.values:
                self.pu_reports[job.pu_index] = deepcopy(job)
            self.send_rack_report()

    def process_internal_messages(self):
        pass

    def send_rack_report(self):
        rack_utilization = 0
        rack_max_u = 0
        p_units_power = 0
        p_units_temp_list = list()
        for report in self.pu_reports.values():
            rack_utilization += report.utilization
            rack_max_u += report.max_u
            p_units_power += report.power
            p_units_temp_list.append(report.temperature)
        self.utilization = rack_utilization
        self.max_u = rack_max_u
        if self.temp_model is not None:
            self.temp = self.temp_model.compute_rack_temperature(p_units_temp_list)
        if self.power_model is not None:
            self.power = self.power_model.compute_rack_power(p_units_power, self.temp, self.env_temp)
        overall_power = p_units_power + self.power
        msg = RackReport(self.rack_id, self.utilization, self.max_u, self.temp, overall_power, p_units_power,
                         self.power, self.pu_reports)
        self.add_msg_to_queue(self.output_rack_report, msg)
