class ResourceManagerConfiguration:
    def __init__(self, hw_dvfs_mode: bool, hw_power_off: bool, n_hot_standby: int, disp_strategy_name: str,
                 disp_strategy_config: dict = None):
        """
        Resource Manager Configuration
        :param hw_dvfs_mode: Activate DVFS mode (True/False)
        :param hw_power_off: Activate Power Off mode (True/False)
        :param n_hot_standby: Number of required PUs in hot standby
        :param disp_strategy_name: Service dispatching strategy name
        """
        self.hw_dvfs_mode = hw_dvfs_mode
        self.hw_power_off = hw_power_off
        self.n_hot_standby = n_hot_standby
        self.disp_strategy_name = disp_strategy_name
        if disp_strategy_config is None:
            disp_strategy_config = dict()
        self.disp_strategy_config = disp_strategy_config


class MirrorReport:
    def __init__(self, max_std_u, std_u):
        self.max_u = max_std_u
        self.utilization = std_u
        self.pu_report_list = dict()
