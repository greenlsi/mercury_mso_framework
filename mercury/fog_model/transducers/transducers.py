from xdevs.models import Port
from abc import ABC, abstractmethod
from ..common.fsm import Stateless
from ..common.plugin_loader import load_plugins
from ..common.edge_fed.edge_fed import EdgeDataCenterReport
from ..common.packet.apps.service import ServiceDelayReport
from ..network import NetworkLinkReport


class Transducer(Stateless, ABC):
    @abstractmethod
    def __init__(self):
        super().__init__()

    def process_internal_messages(self):
        pass


class EdgeDataCenterTransducer(Transducer, ABC):
    def __init__(self):
        super().__init__()
        self.input_edc_report = Port(EdgeDataCenterReport, 'input_edc_report')
        self.add_in_port(self.input_edc_report)

    def check_in_ports(self):
        if self.input_edc_report:
            self.process_edc_reports()

    @abstractmethod
    def process_edc_reports(self):
        pass

    @abstractmethod
    def get_edc_utilization_data(self):
        pass

    @abstractmethod
    def get_edc_power_demand_data(self):
        pass

    @abstractmethod
    def get_edc_it_power_data(self):
        pass

    @abstractmethod
    def get_edc_cooling_power_data(self):
        pass


class RadioTransducer(Transducer, ABC):
    def __init__(self):
        super().__init__()
        self.input_new_ul_mcs = Port(NetworkLinkReport, 'input_new_ul_mcs')
        self.input_new_dl_mcs = Port(NetworkLinkReport, 'input_new_dl_mcs')
        self.add_in_port(self.input_new_ul_mcs)
        self.add_in_port(self.input_new_dl_mcs)

    def check_in_ports(self):
        if self.input_new_ul_mcs:
            self.process_ul_reports()
        if self.input_new_dl_mcs:
            self.process_dl_reports()

    @abstractmethod
    def process_ul_reports(self):
        pass

    @abstractmethod
    def process_dl_reports(self):
        pass

    @abstractmethod
    def get_ul_radio_data(self):
        pass

    @abstractmethod
    def get_dl_radio_data(self):
        pass


class UEDelayTransducer(Transducer, ABC):
    def __init__(self):
        super().__init__()
        self.input_service_delay_report = Port(ServiceDelayReport, 'input_delay')
        self.add_in_port(self.input_service_delay_report)

    def check_in_ports(self):
        if self.input_service_delay_report:
            self.process_ue_delay_reports()

    @abstractmethod
    def process_ue_delay_reports(self):
        pass

    @abstractmethod
    def get_delay_data(self):
        pass


class TransducerBuilder(ABC):
    def __init__(self, scenario_config, **kwargs):
        self.scenario_config = scenario_config
        pass

    @abstractmethod
    def create_edc_transducer(self) -> EdgeDataCenterTransducer:
        pass

    @abstractmethod
    def create_radio_transducer(self) -> RadioTransducer:
        pass

    @abstractmethod
    def create_ue_delay_transducer(self) -> UEDelayTransducer:
        pass


class TransducerBuilderFactory:
    def __init__(self):
        self._builders = dict()
        for key, builder in load_plugins('mercury.transducers.plugins').items():
            self.register_builder(key, builder)

    def register_builder(self, key: str, builder: TransducerBuilder):
        self._builders[key] = builder

    def is_builder_defined(self, key: str) -> bool:
        return key in self._builders

    def create_transducer_builder(self, scenario_config, key, **kwargs) -> TransducerBuilder:
        builder = self._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder(scenario_config, **kwargs)
