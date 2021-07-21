from abc import ABC, abstractmethod
from mercury.logger import logger as logging
from typing import List, Optional, Union, Dict, Any, Tuple, Set
from xdevs.models import Coupled
from xdevs.transducers import Transducer, Transducers
from mercury.config.core import CoreConfig
from .network.network import DynamicNodesMobility
from .edcs import EdgeDataCenters
from .smart_grid import SmartGrid
from .iot_devices import IoTDevices, IoTDevicesLite
from .core import Core
from .shortcut import Shortcut, NetworkMultiplexer
from .crosshaul import Crosshaul
from .aps import AccessPoints
from .radio import Radio, RadioShortcut


class AbstractMercury(Coupled, ABC):
    def __init__(self, name: str, services: Set[str], edge_fed: EdgeDataCenters, core: Core, xh: Optional[Crosshaul],
                 aps: Optional[AccessPoints], radio: Optional[Union[Radio, RadioShortcut]],
                 iot_devices: Union[IoTDevices, IoTDevicesLite], smart_grid: Optional[SmartGrid],
                 mobility: DynamicNodesMobility, transducers_config: Dict[str, Tuple[str, Dict[str, Any]]]):
        super().__init__(name)

        self.edge_fed: EdgeDataCenters = edge_fed
        self.core: Core = core
        self.xh: Optional[Crosshaul] = xh
        self.aps: Optional[AccessPoints] = aps
        self.radio: Optional[Union[Radio, RadioShortcut]] = radio
        self.iot_devices: Union[IoTDevices, IoTDevicesLite] = iot_devices
        self.smart_grid: Optional[SmartGrid] = smart_grid
        self.mobility: DynamicNodesMobility = mobility
        self.transducers: List[Transducer] = list()

        logging.debug("    Adding model layers...")
        for component in [edge_fed, core, xh, aps, radio, iot_devices, smart_grid, mobility]:
            if component is not None:
                self.add_component(component)
        logging.debug("    Model layers added")

        if transducers_config:
            logging.debug("    Creating transducers...")
            self.create_transducers(services, transducers_config)
            logging.debug("    Transducers created")

    def couple_layers(self):
        logging.debug("    Coupling model layers...")
        self._couple_layers()
        if self.smart_grid is not None:
            self._couple_smart_grid()
        logging.debug("    Model layers coupled")

    @abstractmethod
    def _couple_layers(self):
        pass

    def _couple_smart_grid(self):
        # internal between smart grid and core
        self.add_coupling(self.smart_grid.output_new_offer, self.core.input_electricity_offer)
        # internal between smart grid and edge fed
        for edc in self.edge_fed.edcs:
            if edc in self.smart_grid.consumers:
                self.add_coupling(self.smart_grid.outputs_consumption[edc], self.edge_fed.inputs_pwr_consumption[edc])
                self.add_coupling(self.edge_fed.outputs_pwr_demand[edc], self.smart_grid.inputs_demand[edc])

    def create_transducers(self, services: Set[str], transducers_config: Dict[str, Tuple[str, Dict[str, Any]]]):
        for t_id, (t_type, t_config) in transducers_config.items():
            # UE delay report transducer
            transducer = Transducers.create_transducer(t_type, **t_config, transducer_id=f"{t_id}_ue_delay",
                                                       sim_time_id='time', include_names=False)
            transducer.add_target_port(self.iot_devices.output_service_delay_report)
            transducer.drop_event_field('value')
            transducer.add_event_field('ue_id', str, lambda x: x.ue_id)
            transducer.add_event_field('service_id', str, lambda x: x.service_id)
            transducer.add_event_field('action', str, lambda x: x.action)
            transducer.add_event_field('generated', float, lambda x: x.generated)
            transducer.add_event_field('processed', float, lambda x: x.processed)
            transducer.add_event_field('delay', float, lambda x: x.delay)
            transducer.add_event_field('times_sent', int, lambda x: x.times_sent)
            self.transducers.append(transducer)

            # EDC report transducer
            transducer = Transducers.create_transducer(t_type, **t_config, transducer_id=f"{t_id}_edc",
                                                       sim_time_id='time', include_names=False)
            transducer.add_target_port(self.edge_fed.output_edc_report)
            transducer.drop_event_field('value')
            transducer.add_event_field('edc_id', str, lambda x: x.edc_id)
            transducer.add_event_field('utilization', float, lambda x: x.utilization)
            for service in services:
                transducer.add_event_field(f'{service}_virtual_u', float, lambda x: x.service_utilization(service))
            transducer.add_event_field('PUE', float, lambda x: x.pue)
            transducer.add_event_field('power_demand', float, lambda x: x.power_demand)
            transducer.add_event_field('it_power', float, lambda x: x.it_power)
            transducer.add_event_field('cooling_power', float, lambda x: x.cooling_power)
            self.transducers.append(transducer)

            if isinstance(self.radio, Radio):
                # Radio DL report transducer
                transducer = Transducers.create_transducer(t_type, **t_config, transducer_id=f"{t_id}_radio_dl",
                                                           sim_time_id='time', include_names=False)
                transducer.add_target_port(self.radio.output_dl_report)
                transducer.drop_event_field('value')
                transducer.add_event_field('ap_id', str, lambda x: x.node_from)
                transducer.add_event_field('ue_id', str, lambda x: x.node_to)
                transducer.add_event_field('efficiency', float, lambda x: x.spectral_efficiency)
                transducer.add_event_field('bandwidth', float, lambda x: x.bandwidth)
                transducer.add_event_field('rate', float, lambda x: x.rate)
                self.transducers.append(transducer)

                # Radio UL report transducer
                transducer = Transducers.create_transducer(t_type, **t_config, transducer_id=f"{t_id}_radio_ul",
                                                           sim_time_id='time', include_names=False)
                transducer.add_target_port(self.radio.output_ul_report)
                transducer.drop_event_field('value')
                transducer.add_event_field('ue_id', str, lambda x: x.node_from)
                transducer.add_event_field('ap_id', str, lambda x: x.node_to)
                transducer.add_event_field('efficiency', float, lambda x: x.spectral_efficiency)
                transducer.add_event_field('bandwidth', float, lambda x: x.bandwidth)
                transducer.add_event_field('rate', float, lambda x: x.rate)
                self.transducers.append(transducer)

            if self.smart_grid is not None:
                # Smart Grid report transducer
                transducer = Transducers.create_transducer(t_type, **t_config,
                                                           transducer_id=f"{t_id}_smart_grid_consumption",
                                                           sim_time_id='time', include_names=False)
                for port in self.smart_grid.outputs_consumption.values():
                    transducer.add_target_port(port)
                transducer.drop_event_field('value')
                transducer.add_event_field('consumer_id', str, lambda x: x.consumer_id)
                transducer.add_event_field('provider_id', str, lambda x: x.provider_id)
                transducer.add_event_field('electricity_cost', float, lambda x: x.electricity_cost)
                transducer.add_event_field('power_consumption', float, lambda x: x.power_consumption)
                transducer.add_event_field('power_demand', float, lambda x: x.power_demand)
                transducer.add_event_field('power_storage', float, lambda x: x.power_storage)
                transducer.add_event_field('power_generation', float, lambda x: x.power_generation)
                transducer.add_event_field('charge_from_grid', bool, lambda x: x.charge_from_grid)
                transducer.add_event_field('allow_discharge', bool, lambda x: x.allow_discharge)
                transducer.add_event_field('energy_stored', float, lambda x: x.energy_stored)
                transducer.add_event_field('energy_capacity', float, lambda x: x.energy_capacity)
                self.transducers.append(transducer)

                transducer = Transducers.create_transducer(t_type, **t_config,
                                                           transducer_id=f"{t_id}_smart_grid_offers",
                                                           sim_time_id='time', include_names=False)
                transducer.add_target_port(self.smart_grid.output_new_offer)
                transducer.drop_event_field('value')
                transducer.add_event_field('provider_id', str, lambda x: x.provider_id)
                transducer.add_event_field('electricity_cost', float, lambda x: x.cost)
                self.transducers.append(transducer)


class MercuryFogModel(AbstractMercury):

    xh: Crosshaul
    aps: AccessPoints
    radio: Radio
    iot_devices: IoTDevices

    def __init__(self, name: str, services: Set[str], edge_fed: EdgeDataCenters, core: Core, xh: Crosshaul,
                 aps: AccessPoints, radio: Radio, iot_devices: IoTDevices, smart_grid: Optional[SmartGrid],
                 mobility: DynamicNodesMobility, transducers_config: Dict[str, Tuple[str, Dict[str, Any]]]):
        super().__init__(name, services, edge_fed, core, xh, aps, radio,
                         iot_devices, smart_grid, mobility, transducers_config)
        self.couple_layers()

    def _couple_layers(self):  # TODO make this more generic
        # internal between edge fed and xh
        self.add_coupling(self.edge_fed.output_data, self.xh.input_data)
        for edc_id in self.edge_fed.edcs:
            self.add_coupling(self.xh.outputs_data[edc_id], self.edge_fed.inputs_data[edc_id])

        # internal between core and xh
        self.add_coupling(self.core.output_data, self.xh.input_data)
        self.add_coupling(self.xh.outputs_data[CoreConfig.CORE_ID], self.core.input_data)

        # internal between aps and xh
        self.add_coupling(self.aps.output_crosshaul, self.xh.input_data)
        for ap_id in self.aps.ap_ids:
            self.add_coupling(self.xh.outputs_data[ap_id], self.aps.inputs_crosshaul[ap_id])

        # internal between aps and radio
        self.add_coupling(self.aps.output_radio_bc, self.radio.input_pbch)
        self.add_coupling(self.aps.output_radio_control_dl, self.radio.input_pdcch)
        self.add_coupling(self.aps.output_radio_transport_dl, self.radio.input_pdsch)
        self.add_coupling(self.aps.output_connected_ues, self.radio.input_enable_channels)
        for ap_id in self.aps.ap_ids:
            self.add_coupling(self.radio.outputs_pucch[ap_id], self.aps.inputs_radio_control_ul[ap_id])
            self.add_coupling(self.radio.outputs_pusch[ap_id], self.aps.inputs_radio_transport_ul[ap_id])

        # internal between iot devices and radio
        self.add_coupling(self.iot_devices.output_create_ue, self.radio.input_create_node)
        self.add_coupling(self.iot_devices.output_remove_ue, self.radio.input_remove_node)
        self.add_coupling(self.iot_devices.output_radio_control_ul, self.radio.input_pucch)
        self.add_coupling(self.iot_devices.output_radio_transport_ul, self.radio.input_pusch)
        self.add_coupling(self.radio.output_pbch, self.iot_devices.input_radio_bc)
        self.add_coupling(self.radio.output_pdcch, self.iot_devices.input_radio_control_dl)
        self.add_coupling(self.radio.output_pdsch, self.iot_devices.input_radio_transport_dl)

        # internal between iot devices and mobility
        self.add_coupling(self.iot_devices.output_create_ue, self.mobility.input_create_node)
        self.add_coupling(self.iot_devices.output_remove_ue, self.mobility.input_remove_node)

        # internal between iot devices and aps
        self.add_coupling(self.iot_devices.output_repeat_pss, self.aps.input_repeat_pss)

        # internal between mobility and aps
        self.add_coupling(self.mobility.output_node_location, self.aps.input_new_location)

        # internal between mobility and radio
        self.add_coupling(self.mobility.output_node_location, self.radio.input_new_location)


class MercuryFogModelShortcut(AbstractMercury):

    aps: AccessPoints
    radio: RadioShortcut
    iot_devices: IoTDevices

    def __init__(self, name, services: Set[str], edge_fed: EdgeDataCenters, core: Core, aps: AccessPoints,
                 radio: RadioShortcut, iot_devices: IoTDevices, smart_grid: Optional[SmartGrid],
                 mobility: DynamicNodesMobility, transducers_config: Dict[str, Tuple[str, Dict[str, Any]]]):
        super().__init__(name, services, edge_fed, core, None, aps, radio,
                         iot_devices, smart_grid, mobility, transducers_config)

        logging.debug("    Building shortcut module...")
        ap_ids_list = {ap_id for ap_id in aps.ap_ids}
        edc_ids_list = {edc_id for edc_id in edge_fed.edcs}
        core_ids_list = {CoreConfig.CORE_ID}
        self.shortcut: Shortcut = Shortcut(ap_ids_list, edc_ids_list, core_ids_list, 'shortcut')
        self.add_component(self.shortcut)
        logging.debug("    Shortcut module built")

        self.couple_layers()

    def _couple_layers(self):
        self.add_coupling(self.edge_fed.output_data, self.shortcut.input_xh_data)
        for edc in self.edge_fed.edcs:
            self.add_coupling(self.shortcut.outputs_xh_data[edc], self.edge_fed.inputs_data[edc])

        self.add_coupling(self.core.output_data, self.shortcut.input_xh_data)
        self.add_coupling(self.shortcut.outputs_xh_data[CoreConfig.CORE_ID], self.core.input_data)

        self.add_coupling(self.aps.output_radio_bc, self.radio.input_data)
        self.add_coupling(self.aps.output_radio_control_dl, self.shortcut.input_radio_control)
        self.add_coupling(self.aps.output_radio_transport_dl, self.shortcut.input_radio_data)
        self.add_coupling(self.aps.output_crosshaul, self.shortcut.input_xh_data)
        for ap in self.aps.ap_ids:
            self.add_coupling(self.shortcut.outputs_xh_data[ap], self.aps.inputs_crosshaul[ap])
            self.add_coupling(self.shortcut.outputs_radio_control[ap], self.aps.inputs_radio_control_ul[ap])
            self.add_coupling(self.shortcut.outputs_radio_data[ap], self.aps.inputs_radio_transport_ul[ap])

        self.add_coupling(self.iot_devices.output_create_ue, self.mobility.input_create_node)
        self.add_coupling(self.iot_devices.output_remove_ue, self.mobility.input_remove_node)
        self.add_coupling(self.iot_devices.output_create_ue, self.radio.input_create_node)
        self.add_coupling(self.iot_devices.output_remove_ue, self.radio.input_remove_node)
        self.add_coupling(self.mobility.output_node_location, self.radio.input_new_location)

        self.add_coupling(self.iot_devices.output_repeat_pss, self.aps.input_repeat_pss)
        self.add_coupling(self.iot_devices.output_radio_control_ul, self.shortcut.input_radio_control)
        self.add_coupling(self.iot_devices.output_radio_transport_ul, self.shortcut.input_radio_data)
        self.add_coupling(self.radio.output_data, self.iot_devices.input_radio_bc)
        self.add_coupling(self.shortcut.output_control_ues, self.iot_devices.input_radio_control_dl)
        self.add_coupling(self.shortcut.output_data_ues, self.iot_devices.input_radio_transport_dl)


class MercuryLite(AbstractMercury):

    iot_devices: IoTDevicesLite

    def __init__(self, name, services: Set[str], edge_fed: EdgeDataCenters, core: Core, iot_devices: IoTDevicesLite,
                 smart_grid: Optional[SmartGrid], mobility: DynamicNodesMobility,
                 transducers_config: Dict[str, Tuple[str, Dict[str, Any]]]):
        super().__init__(name, services, edge_fed, core, None, None, None,
                         iot_devices, smart_grid, mobility, transducers_config)

        logging.debug("    Building multiplexer module...")
        self.mux = NetworkMultiplexer({*edge_fed.edcs, CoreConfig.CORE_ID})
        self.add_component(self.mux)
        logging.debug("    Multiplexer module built")

        self.couple_layers()

    def _couple_layers(self):
        self.add_coupling(self.edge_fed.output_data, self.mux.input)
        for edc_id in self.edge_fed.edcs:
            self.add_coupling(self.mux.outputs[edc_id], self.edge_fed.inputs_data[edc_id])

        self.add_coupling(self.core.output_data, self.mux.input)
        self.add_coupling(self.mux.outputs[CoreConfig.CORE_ID], self.core.input_data)

        self.add_coupling(self.iot_devices.output_network, self.mux.input)
        self.add_coupling(self.mux.output_ues, self.iot_devices.input_network)

        self.add_coupling(self.iot_devices.output_create_ue, self.mobility.input_create_node)
        self.add_coupling(self.iot_devices.output_remove_ue, self.mobility.input_remove_node)

        self.add_coupling(self.iot_devices.output_create_ue, self.core.input_create_node)
        self.add_coupling(self.iot_devices.output_remove_ue, self.core.input_remove_node)
        self.add_coupling(self.mobility.output_node_location, self.core.input_node_location)
