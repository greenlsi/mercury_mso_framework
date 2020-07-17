from mercury.fog_model.edge_fed.edc.rack.rack_node.rack_pwr import RackPowerModel
from mercury.fog_model.edge_fed.edc.rack.rack_node.rack_temp import RackTemperatureModel


class WiloIPLPowerModel(RackPowerModel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.c_p = kwargs.get('c_p', 4.18)  # TODO hacer esto más flexible para otras cosas

    def compute_rack_power(self, it_power, rack_temp: float, env_temp: float) -> float:
        delta_temp = 23
        flow = it_power / (277.78 * self.c_p * delta_temp)

        return min(900, (max(500, 20 * (flow - 4) + 500)))
