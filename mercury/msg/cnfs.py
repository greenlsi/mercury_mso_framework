from typing import Dict, Optional


class DemandEstimation:
    def __init__(self, service_id: str, demand_estimation: Optional[float]):
        """
        Service demand estimation message.
        :param service_id: service ID.
        :param demand_estimation: average number of users that are expected to use the service.
        """
        self.service_id: str = service_id
        self.demand_estimation: Optional[float] = demand_estimation


class EdgeDataCenterSlicing:
    def __init__(self, edc_id: str, slicing: Dict[str, float]):
        """
        Edge Data Center resource slicing message.
        :param edc_id: Edge Data Center ID.
        :param slicing: dictionary {service_id: max_allowed_resources}
        """
        self.edc_id: str = edc_id
        self.slicing: Dict[str, float] = slicing
