from .pu_pwr import ProcessingUnitPowerModel


class StaticDynamicPowerModel(ProcessingUnitPowerModel):
    """
    Static + Dynamic power model for processing unit.
    If switched off, power consumption is 0.
    If switched on, power consumption is Pstatic + Pdynamic, where Pdynamic is:
        Pdyn = alpha*V(t)^2 + f(t)*u(t)
            alpha: constant
            V(t): working voltage (it is substracted from the DVFS configuration)
            f(t): working frequency in GHz (it is substracted from the DVFS configuration)
            u(t) instantaneous utilzation factor
    :param float static_power: static power consumption.
    :param float alpha: alpha constant.
    :param string voltage_dvfs_label: label for taking voltage from the DVFS table.
    :param string frequency_dvfs_label: label for taking frequency from DVFS table.
    """
    def __init__(self, **kwargs):
        super().__init__()
        self.static_power = kwargs.get('static_power', 0)
        self.alpha = kwargs.get('alpha', 0)
        self.voltage_dvfs_label = kwargs.get('voltage_dvfs_label', 'v')
        self.frequency_dvfs_label = kwargs.get('frequency_dvfs_label', 'f')

    def compute_power(self, status, utilization, max_u, dvfs_index, dvfs_table):
        power = 0
        if status:
            u = utilization / max_u
            v = dvfs_table[dvfs_index].get(self.voltage_dvfs_label, 0)
            pow_1 = self.alpha * (v ** 2)
            f = dvfs_table[dvfs_index].get(self.frequency_dvfs_label, 0)
            pow_2 = f * u
            power = pow_1 + pow_2
        return power
