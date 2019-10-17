from abc import ABC, abstractmethod
from .crosshaul import CrosshaulTransceiverConfiguration


class EdgeFederationControllerConfiguration:
    def __init__(self, controller_id, controller_location, crosshaul_transceiver_config):
        """
        Edge Federation Controller Configuration
        :param str controller_id: Federation Controller ID
        :param tuple controller_location: Federation Controller ue_location <x, y> (in meters)
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver_config: crosshaul_config transceiver configuration
        """
        self.controller_id = controller_id
        self.controller_location = controller_location
        self.crosshaul_transceiver_config = crosshaul_transceiver_config


class EdgeDataCenterConfiguration:
    def __init__(self, edc_id, edc_location, crosshaul_transceiver_config, r_manager_config,
                 p_units_configuration_list, base_temp=298):
        """
        Edge Data Center Configuration
        :param str edc_id: ID of the Edge Data Center
        :param tuple edc_location: Access Point coordinates <x, y> (in meters)
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver_config: Crosshaul transceiver configuration
        :param list p_units_configuration_list: Configuration list of Processing Units that compose the EDC
        :param ResourceManagerConfiguration r_manager_config: Resource Manager Configuration
        :param float base_temp: Edge Data Center base temperature (in Kelvin)
        """
        self.edc_id = edc_id
        self.edc_location = edc_location
        self.crosshaul_transceiver_config = crosshaul_transceiver_config
        self.p_units_configuration_list = p_units_configuration_list
        self.r_manager_config = r_manager_config
        self.base_temp = base_temp


class EdgeDataCenterReport:
    """
    Status of an Edge Data Center.
    :param str edc_id: ID of the Edge data center
    :param float overall_std_u: Overall utilized standard utilization factor
    :param float max_std_u: Maximum available standard utilization factor
    :param float overall_power: Overall power consumption
    :param dict routing_table: dictionary with all the routing information of the EDC
    :param list p_units_report: list of ProcessingUnitReport of the EDC
    """
    def __init__(self, edc_id, overall_std_u, max_std_u, overall_power, routing_table, p_units_report):
        self.edc_id = edc_id
        self.overall_std_u = overall_std_u
        self.max_std_u = max_std_u
        self.relative_u_per_service = dict()
        for service_id, sessions in routing_table.items():
            service_u = 0
            for session_id, info in sessions.items():
                service_u += info['service_u']
            self.relative_u_per_service[service_id] = service_u / max_std_u * 100
        self.relative_u = sum([service_u for service_u in self.relative_u_per_service.values()])
        self.overall_power = overall_power
        self.routing_table = routing_table
        self.p_units_report = p_units_report


class ResourceManagerConfiguration:
    def __init__(self, hw_dvfs_mode=False, hw_power_off=False, disp_strategy=None):
        """
        Resource Manager Configuration
        :param bool hw_dvfs_mode: Activate DVFS mode (True/False)
        :param bool hw_power_off: Activate Power Off mode (True/False)
        :param DispatchingStrategy disp_strategy: Workload Allocation strategy
        """
        self.hw_dvfs_mode = hw_dvfs_mode
        self.hw_power_off = hw_power_off
        if disp_strategy is None:
            disp_strategy = MinimumDispatchingStrategy
        self.disp_strategy = disp_strategy()


class DispatchingStrategy(ABC):
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def allocate_task(self, service_id, session_id, std_u, p_units_reports):
        """

        :param str service_id: ID of the new pxsch to be allocated
        :param str session_id: ID of the new session to be allocated
        :param float std_u: Standard Utilization Factor of the pxsch to be allocated
        :param list p_units_reports: Processing units current status
        :return: index of the processing unit that is to allocate the new session
        """
        pass

    @abstractmethod
    def change_p_units_status(self, p_units_reports, hw_power_off):
        """

        :param list p_units_reports:
        :param bool hw_power_off:
        :return list:
        """
        pass

    @staticmethod
    def set_dvfs_mode(p_units_reports, hw_dvfs_mode):
        return [hw_dvfs_mode for _ in range(len(p_units_reports))]


class MinimumDispatchingStrategy(DispatchingStrategy):
    def allocate_task(self, service_id, session_id, std_u, p_units_reports):
        pu_index = None
        space = 0
        i = 0
        for report in p_units_reports:
            aux = 100 - report.utilization - std_u * report.pu_std_to_spec
            if aux >= space:
                pu_index = i
                space = aux
            i += 1
        return pu_index

    def change_p_units_status(self, p_units_reports, hw_power_off):
        res = [not hw_power_off for _ in p_units_reports]
        if hw_power_off:
            for pu_index in range(len(res)):
                if p_units_reports[pu_index].ongoing_sessions:
                    res[pu_index] = True
        return res


class MaximumDispatchingStrategy(DispatchingStrategy):
    def allocate_task(self, service_id, session_id, std_u, p_units_reports):
        pu_index = None
        space = 100
        i = 0
        for report in p_units_reports:
            aux = 100 - report.utilization - std_u * report.pu_std_to_spec
            if 0 <= aux <= space:
                pu_index = i
                space = aux
            i += 1
        return pu_index

    def change_p_units_status(self, p_units_reports, hw_power_off):
        res = [not hw_power_off for _ in p_units_reports]
        if hw_power_off:
            for pu_index in range(len(res)):
                if p_units_reports[pu_index].ongoing_sessions:
                    res[pu_index] = True
        return res


class ProcessingUnitReport:
    def __init__(self, pu_id, pu_std_to_spec, status, dvfs_mode, dvfs_index, utilization, power, temperature, ongoing_sessions):
        self.pu_id = pu_id
        self.pu_std_to_spec = pu_std_to_spec
        self.status = status
        self.dvfs_mode = dvfs_mode
        self.dvfs_index = dvfs_index
        self.utilization = utilization
        self.power = power
        self.temperature = temperature
        self.ongoing_sessions = ongoing_sessions


class ProcessingUnitConfiguration:
    def __init__(self, p_unit_id, dvfs_table=None, std_to_spec_u=1, t_off_on=0, t_on_off=0, t_operation=0, power_model=None):
        """
        Processing Unit Configuration
        :param str p_unit_id: Processing unit model ID
        :param dict dvfs_table: dictionary containing DVFS table {std_u_1: {dvfs_conf_1}, ..., 100: {dvfs_conf_N}}
        :param float std_to_spec_u: standard-to-specific utilization factor relation
        :param float t_off_on: time required for the processing unit to switch on
        :param float t_on_off: time required for the processing unit to switch off
        :param float t_operation: time required for the processing unit to perform an operation
        :param ProcessingUnitPowerModel power_model: Object that computes power depending on utilization and DVFS mode (in Watts)
        """
        if dvfs_table is None:
            dvfs_table = {100: {}}
        try:
            assert 100 in dvfs_table
            assert std_to_spec_u > 0
            assert t_off_on >= 0
            assert t_on_off >= 0
            assert t_operation >= 0
        except AssertionError:
            raise ValueError("Processing Unit Configuration values are invalid")
        self.p_unit_id = p_unit_id
        self.dvfs_table = dvfs_table
        self.std_to_spec_u = std_to_spec_u
        self.t_off_on = t_off_on
        self.t_on_off = t_on_off
        self.t_operation = t_operation
        self.power_model = power_model


class ProcessingUnitPowerModel(ABC):
    """
    <Abstract class> Power model of a given processing unit. This object is user-defined.
    """
    def __init__(self):
        pass

    @abstractmethod
    def compute_power(self, utilization, dvfs_index, dvfs_table):
        """
        Compute power consumption according to a power model. This method is user-defined.
        :param float utilization: Utilization factor of a given processing unit
        :param int dvfs_index: current DVFS table index
        :param dict dvfs_table: DVFS table
        :returns power: Processing Unit power consumption
        """
        pass


class IdleActivePowerModel(ProcessingUnitPowerModel):
    """
    Idle/active power model for processing unit.
    If switched off, power consumption is 0.
    If switched on but with no services ongoing, power consumption is idle_power.
    If switched on and with services ongoing, power consumption is active_power.
    :param float idle_power: power consumption when processing unit is idling.
    :param float active_power: power consumption when processing unit is working.
    """

    def __init__(self, idle_power, active_power):
        super().__init__()
        self.idle_power = idle_power
        self.active_power = active_power

    def compute_power(self, utilization, dvfs_index, dvfs_table):
        """
        Compute power consumption according to a power model.
        :param float utilization: Utilization factor of a given processing unit
        :param int dvfs_index: current DVFS table index
        :param dict dvfs_table: DVFS table
        :returns power: Processing Unit power consumption
        """
        return self.idle_power if utilization == 0 else self.active_power


class StaticDynamicPowerModel(ProcessingUnitPowerModel):
    """
    Static + Dynamic power model for processing unit.
    If switched off, power consumption is 0.
    If switched on, power consumption is Pstatic + Pdynamic, where Pdynamic is:
        Pdyn = alpha*V(t)^2 + f(t)*u(t)
            alpha: constant
            V(t): working voltage (it is substracted from the DVFS configuration)
            f(t): working frequency (it is substracted from the DVFS configuration)
            u(t) instantaneous utilzation factor
    :param float static_power: static power consumption.
    :param float alpha: alpha constant.
    :param string voltage_label: label for taking voltage from the DVFS table.
    :param string frequency_label: label for taking frequency from DVFS table.
    """

    def __init__(self, static_power, alpha, voltage_label='v', frequency_label='f'):
        super().__init__()
        self.static_power = static_power
        self.alpha = alpha
        self.voltage_label = voltage_label
        self.frequency_label = frequency_label

    def compute_power(self, utilization, dvfs_index, dvfs_table):
        """
        Compute power consumption according to a power model.
        :param float utilization: Utilization factor of a given processing unit
        :param int dvfs_index: current DVFS table index
        :param dict dvfs_table: DVFS table
        :returns power: Processing Unit power consumption
        """
        pow_1 = self.alpha * (dvfs_table[dvfs_index][self.voltage_label] ** 2)
        pow_2 = dvfs_table[dvfs_index][self.frequency_label] * utilization
        return pow_1 + pow_2
