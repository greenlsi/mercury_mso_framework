from .pu_pwr import ProcessingUnitPowerModel


class IdleActivePowerModel(ProcessingUnitPowerModel):
    """
    Idle/active power model for processing unit.
        If switched off, power consumption is 0.
        If switched on but with no services ongoing, power consumption is idle_power.
        If switched on and with services ongoing, power consumption is active_power.
    :param float idle_power: power consumption when processing unit is idling.
    :param float active_power: power consumption when processing unit is working.
    """
    def __init__(self, **kwargs):
        super().__init__()
        self.idle_power = kwargs.get('idle_power', 0)
        self.active_power = kwargs.get('active_power', 0)

    def compute_power(self, status, utilization, max_u, dvfs_index, dvfs_table):
        power = 0
        if status:
            power = self.idle_power if utilization == 0 else self.active_power
        return power
