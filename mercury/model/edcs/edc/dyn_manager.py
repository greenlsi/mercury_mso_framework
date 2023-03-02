from __future__ import annotations
from mercury.config.edcs import EdgeDataCenterConfig
from mercury.msg.edcs import EdgeDataCenterReport, SrvDemandEstimationReport, NewEDCConfig
from xdevs.models import Port
from ...common import ExtendedAtomic


class EDCDynamicManager(ExtendedAtomic):
    def __init__(self, edc_config: EdgeDataCenterConfig):
        from mercury.plugin.factory import AbstractFactory, DynamicEDCMapping, DynamicEDCSlicing
        self.edc_id = edc_config.edc_id
        super().__init__(f'{self.edc_id}_dyn_manager')

        self.input_srv_estimation = Port(SrvDemandEstimationReport, 'input_srv_estimation')
        self.output_edc_config = Port(NewEDCConfig, 'output_edc_config')
        self.add_in_port(self.input_srv_estimation)
        self.add_out_port(self.output_edc_config)

        self.edc_report: EdgeDataCenterReport | None = None
        self.srv_estimation: dict[str, int] = dict()

        self.mapping: DynamicEDCMapping | None = None
        if edc_config.dyn_config.mapping_id is not None:
            mapping_id = edc_config.dyn_config.mapping_id
            mapping_config = {**edc_config.dyn_config.mapping_config, 'edc_config': edc_config}
            self.mapping = AbstractFactory.create_edc_dyn_mapping(mapping_id, **mapping_config)

        self.slicing: DynamicEDCSlicing | None = None
        if edc_config.dyn_config.slicing_id is not None:
            slicing_id = edc_config.dyn_config.slicing_id
            slicing_config = {**edc_config.dyn_config.slicing_config, 'edc_config': edc_config}
            self.slicing = AbstractFactory.create_edc_dyn_slicing(slicing_id, **slicing_config)

        self.cool_down = edc_config.dyn_config.cool_down
        self.next_timeout = 0
        self.waiting = False

    def deltint_extension(self):
        if self.waiting:
            self.explore_configurations()
        self.passivate() if self.msg_queue_empty() else self.activate()

    def deltext_extension(self, e):
        self.get_new_data()
        if self._clock < self.next_timeout:  # If controller is cooling down, it waits before doing anything else
            self.hold_in(self.phase, self.next_timeout - self._clock)
        else:  # Otherwise, we explore new configurations
            self.explore_configurations()
            self.passivate() if self.msg_queue_empty() else self.activate()

    def get_new_data(self):
        self.waiting = True
        if self.input_srv_estimation:
            estimation = self.input_srv_estimation.get()
            self.edc_report = estimation.edc_report
            self.srv_estimation = estimation.demand_estimation

    def explore_configurations(self) -> None:
        if self.edc_report is not None:
            self.waiting = False
            self.next_timeout = self._clock + self.cool_down
            self.explore_slicing()
            self.explore_mapping()

    def explore_slicing(self):
        if self.slicing is not None:
            slicing = self.slicing.new_slicing(self.edc_report, self.srv_estimation)
            if slicing is not None:
                self.add_msg_to_queue(self.output_edc_config, slicing)

    def explore_mapping(self):
        if self.mapping is not None:
            mapping = self.mapping.new_mapping(self.edc_report, self.srv_estimation)
            if mapping is not None:
                self.add_msg_to_queue(self.output_edc_config, mapping)

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
