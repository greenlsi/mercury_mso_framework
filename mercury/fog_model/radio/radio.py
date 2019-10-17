from xdevs.models import Coupled, Port
from ..common.radio import RadioConfiguration
from ..common.packet.physical import PhysicalPacket
from ..common.mobility import NewLocation
from .radio_pbch import PhysicalBroadcastChannel
from .radio_pxcch import PhysicalControlChannel
from .radio_pxsch import PhysicalTransportChannel


class Radio(Coupled):
    def __init__(self, name, radio_config, ues_location, aps_location):
        """
        Radio Layer XDEVS Module
        :param str name: XDEVS module name
        :param RadioConfiguration radio_config: Radio layer Configuration
        :param dict ues_location: Dictionary {UE ID: UE Location}
        :param dict aps_location: Dictionary {AP ID: AP Location}
        """
        super().__init__(name)

        # Unwrap configuration parameters
        frequency = radio_config.frequency
        attenuator = radio_config.attenuator
        prop_speed = radio_config.prop_speed
        penalty_delay = radio_config.penalty_delay

        # Create and add sub-components
        pbch = PhysicalBroadcastChannel(name + '_pbch', aps_location, ues_location, frequency, attenuator, prop_speed,
                                        penalty_delay)
        pxcch = PhysicalControlChannel(name + '_pxcch', aps_location, ues_location, frequency, attenuator, prop_speed,
                                       penalty_delay)
        pxsch = PhysicalTransportChannel(name + '_pxsch', aps_location, ues_location, frequency, attenuator, prop_speed,
                                         penalty_delay)
        self.add_component(pbch)
        self.add_component(pxcch)
        self.add_component(pxsch)

        # Input port for ue_location changes
        self.input_new_location = Port(NewLocation, name + '_input_new_location')
        self.add_in_port(self.input_new_location)

        # Broadcast Network
        self.input_radio_pbch = Port(PhysicalPacket, name + '_input_pbch')
        self.output_radio_pbch = Port(PhysicalPacket, name + '_output_pbch')
        self.add_in_port(self.input_radio_pbch)
        self.add_out_port(self.output_radio_pbch)
        # External couplings
        self._pbch_external_couplings(pbch)

        # Access and Control Network
        self.input_radio_pxcch = Port(PhysicalPacket, name + '_input_pxcch')
        self.output_radio_pucch = Port(PhysicalPacket, name + '_output_pucch')
        self.output_radio_pdcch = Port(PhysicalPacket, name + '_output_pdcch')
        self.add_in_port(self.input_radio_pxcch)
        self.add_out_port(self.output_radio_pucch)
        self.add_out_port(self.output_radio_pdcch)
        # External couplings
        self._access_external_couplings(pxcch)

        # Transport network
        self.input_radio_pxsch = Port(PhysicalPacket, name + '_input_pxsch')
        self.output_radio_pusch = Port(PhysicalPacket, name + '_output_pusch')
        self.output_radio_pdsch = Port(PhysicalPacket, name + '_output_pdsch')
        self.add_in_port(self.input_radio_pxsch)
        self.add_out_port(self.output_radio_pusch)
        self.add_out_port(self.output_radio_pdsch)
        # External couplings
        self._transport_external_couplings(pxsch)

    def _pbch_external_couplings(self, pbch):
        """
        Broadcast Network external couplings
        :param PhysicalBroadcastChannel pbch: Broadcast Network
        """
        self.add_coupling(self.input_new_location, pbch.input_new_location)
        self.add_coupling(self.input_radio_pbch, pbch.input_radio_bc)
        self.add_coupling(pbch.output_radio_bc, self.output_radio_pbch)

    def _access_external_couplings(self, pxcch):
        """
        Access Network external couplings
        :param PhysicalControlChannel pxcch: Access and Control Network
        """
        self.add_coupling(self.input_new_location, pxcch.input_new_location)
        self.add_coupling(self.input_radio_pxcch, pxcch.input_radio_pxcch)
        self.add_coupling(pxcch.output_radio_pdcch, self.output_radio_pdcch)
        self.add_coupling(pxcch.output_radio_pucch, self.output_radio_pucch)

    def _transport_external_couplings(self, pxsch):
        """
        Service Network external couplings
        :param PhysicalTransportChannel pxsch: Transport Network
        """
        self.add_coupling(self.input_new_location, pxsch.input_new_location)
        self.add_coupling(self.input_radio_pxsch, pxsch.input_radio_pxsch)
        self.add_coupling(pxsch.output_radio_pdsch, self.output_radio_pdsch)
        self.add_coupling(pxsch.output_radio_pusch, self.output_radio_pusch)
