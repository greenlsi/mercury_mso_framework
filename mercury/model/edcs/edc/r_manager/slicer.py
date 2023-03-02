from __future__ import annotations
from mercury.config.edcs import EdgeDataCenterConfig
from .pu import ProcessingUnit


class EDCResourceSlicer:
    def __init__(self, edc_config: EdgeDataCenterConfig, srv_priority: list[str]):
        """
        Edge Data Center resource slicer.
        :param srv_priority: list of services in decreasing priority order. The resource slicer
                             will allocate first resources for the services with higher priority.
        :param edc_config: configuration parameters of the EDC.
        """
        from mercury.plugin import AbstractFactory, PUMappingStrategy
        self.edc_id: str = edc_config.edc_id
        self.srv_priority: list[str] = srv_priority
        self.pu_twins: list[ProcessingUnit] = list()
        for pu_id, pu_config in edc_config.pu_configs.items():
            self.pu_twins.append(ProcessingUnit(f'{pu_id}_slicer', pu_id, pu_config, edc_config.edc_temp, True))
        self.mapping: PUMappingStrategy = AbstractFactory.create_edc_pu_mapping('epu')

    def slice_resources(self, srv_slicing: dict[str, int]) -> dict[str | None, tuple[int, list[str]]]:
        """
        It slices all the PUs of the EDC according to the expected service demand.
        :param srv_slicing: for every service, it determines number of clients that the EDC is expected to provide
                            service simultaneously.
        :return: for every service, it determines which PUs of the EDC are selected to process requests of the service.
                 It also provides the maximum number of clients that can be dispatched simultaneously with the slice.
                 The slicer will try to provide slices that are large enough to meet the service slicing criteria.
                 The None key corresponds to PUs that are not assigned to any slice.
        """
        sliced_pus: dict[str | None, tuple[int, list[str]]] = dict()
        free_pus: list[ProcessingUnit] = [pu_twin for pu_twin in self.pu_twins]
        for service_id in self.srv_priority:
            expected_slice_size = srv_slicing.get(service_id, 0)
            if expected_slice_size > 0:
                slice_size, slice_pus = 0, list()
                map_priority_queue = self.mapping.map_priority_queue(free_pus, service_id)
                while slice_size < expected_slice_size and not map_priority_queue.empty():
                    _, pu_twin = map_priority_queue.get()
                    slice_size += pu_twin.max_n_tasks(service_id)
                    slice_pus.append(pu_twin.pu_id)
                    free_pus.remove(pu_twin)
                sliced_pus[service_id] = slice_size, slice_pus
        sliced_pus[None] = 0, [pu_twin.pu_id for pu_twin in free_pus]
        return sliced_pus
