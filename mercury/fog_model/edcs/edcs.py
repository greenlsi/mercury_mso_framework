from typing import Set, Dict
from xdevs.models import Coupled, Port
from mercury.config.edcs import EdgeDataCenterConfig
from mercury.msg.edcs import EdgeDataCenterReport
from mercury.msg.network import PhysicalPacket, NetworkPacket
from mercury.msg.smart_grid import PowerDemandReport, PowerConsumptionReport
from .edc import EdgeDataCenter


class EdgeDataCenters(Coupled):
    def __init__(self, edcs_config: Dict[str, EdgeDataCenterConfig],
                 services: Set[str], smart_grid: Dict[str, bool], lite: bool = False):
        """
        Edge Federation xDEVS model
        :param edcs_config: Edge Data Centers configuration dict {EDC ID: EDC configuration}
        :param services: set with all the service IDs
        :param smart_grid: indicates if the smart grid layer is activated
        :param lite: indicates if the user wants a lite version of the edge federation model
        """

        super().__init__('edge_fed')
        # Unwrap configuration parameters
        self.n_edc = len(edcs_config)

        # Define sub-modules and add them to coupled module
        self.edcs: Dict[str, EdgeDataCenter] = {edc_id: EdgeDataCenter(edc_config, services, smart_grid[edc_id], lite)
                                                for edc_id, edc_config in edcs_config.items()}
        for edc in self.edcs.values():
            self.add_component(edc)

        port_type = NetworkPacket if lite else PhysicalPacket

        # Define input/output ports
        self.output_edc_report = Port(EdgeDataCenterReport, 'output_edc_report')
        self.output_data = Port(port_type, 'output_data')
        self.add_out_port(self.output_edc_report)
        self.add_out_port(self.output_data)

        self.inputs_data = dict()
        self.inputs_pwr_consumption = dict()
        self.outputs_pwr_demand = dict()
        for edc_id, edc in self.edcs.items():
            self.add_coupling(edc.output_edc_report, self.output_edc_report)
            self.add_coupling(edc.output_data, self.output_data)

            self.inputs_data[edc_id] = Port(port_type, 'input_data_{}'.format(edc_id))
            self.add_in_port(self.inputs_data[edc_id])
            self.add_coupling(self.inputs_data[edc_id], edc.input_data)

            if smart_grid[edc_id]:
                self.inputs_pwr_consumption[edc_id] = Port(PowerConsumptionReport, 'input_consumption_{}'.format(edc_id))
                self.outputs_pwr_demand[edc_id] = Port(PowerDemandReport, 'output_pwr_demand_{}'.format(edc_id))

                self.add_in_port(self.inputs_pwr_consumption[edc_id])
                self.add_out_port(self.outputs_pwr_demand[edc_id])

                self.add_coupling(self.inputs_pwr_consumption[edc_id], edc.input_pwr_consumption)
                self.add_coupling(edc.output_pwr_demand, self.outputs_pwr_demand[edc_id])
