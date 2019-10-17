from xdevs.models import Coupled, Port
from ..common.crosshaul import CrosshaulConfiguration
from ..common.packet.physical import PhysicalPacket
from .crosshaul_dl import CrosshaulDownLink
from .crosshaul_ul import CrosshaulUpLink


class Crosshaul(Coupled):
    def __init__(self, name, crosshaul_config, aps_location, edcs_location, fed_controller_location, amf_location,
                 sdn_controller_location):
        """
        Crosshaul Layer XDEVS module
        :param str name: Crosshaul layer module name
        :param CrosshaulConfiguration crosshaul_config: Crosshaul Layer configuration
        :param dict aps_location: dictionary {AP ID: AP Location}
        :param dict edcs_location: dictionary {EDC ID: EDC Location}
        :param dict fed_controller_location: dictionary {Fed. Controller ID: Fed. Controller Location} (size 1)
        :param dict amf_location: dictionary {AMF ID: AMF location}
        :param dict sdn_controller_location: dictionary {SDN Controller ID: SDN Controller location}
        """
        super().__init__(name)

        # Unwrap configuration parameters
        prop_speed = crosshaul_config.prop_speed
        penalty_delay = crosshaul_config.penalty_delay
        ul_frequency = crosshaul_config.ul_frequency
        dl_frequency = crosshaul_config.dl_frequency
        ul_attenuator = crosshaul_config.ul_attenuator
        dl_attenuator = crosshaul_config.dl_attenuator

        # Create and add sub-components
        crosshaul_ul = CrosshaulUpLink(name + '_ul', aps_location, edcs_location, fed_controller_location, amf_location,
                                       sdn_controller_location, ul_frequency, ul_attenuator, prop_speed)
        crosshaul_dl = CrosshaulDownLink(name + '_ul', aps_location, edcs_location, amf_location,
                                         sdn_controller_location, dl_frequency, dl_attenuator, prop_speed,
                                         penalty_delay)
        self.add_component(crosshaul_ul)
        self.add_component(crosshaul_dl)

        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.input_crosshaul_dl = Port(PhysicalPacket, name + '_input_crosshaul_dl')
        self.output_ap_ul = Port(PhysicalPacket, name + '_output_ap_ul')
        self.output_edc_ul = Port(PhysicalPacket, name + '_output_edc_ul')
        self.output_fed_controller_ul = Port(PhysicalPacket, name + '_output_fed_controller_ul')
        self.output_amf_ul = Port(PhysicalPacket, name + '_output_amd_ul')
        self.output_sdn_controller_ul = Port(PhysicalPacket, name + '_output_sdn_controller_ul')
        self.output_ap_dl = Port(PhysicalPacket, name + '_output_ap_dl')
        self.add_in_port(self.input_crosshaul_ul)
        self.add_in_port(self.input_crosshaul_dl)
        self.add_out_port(self.output_ap_ul)
        self.add_out_port(self.output_edc_ul)
        self.add_out_port(self.output_fed_controller_ul)
        self.add_out_port(self.output_amf_ul)
        self.add_out_port(self.output_sdn_controller_ul)
        self.add_out_port(self.output_ap_dl)

        # External couplings
        self._ul_external_couplings(crosshaul_ul)
        self._dl_external_couplings(crosshaul_dl)

    def _ul_external_couplings(self, crosshaul_ul):
        """
        Inserts external couplings for the crosshaul_config uplink
        :param CrosshaulUpLink crosshaul_ul: Crosshaul uplink
        """
        self.add_coupling(self.input_crosshaul_ul, crosshaul_ul.input_crosshaul_ul)
        self.add_coupling(crosshaul_ul.output_ap_ul, self.output_ap_ul)
        self.add_coupling(crosshaul_ul.output_edc_ul, self.output_edc_ul)
        self.add_coupling(crosshaul_ul.output_fed_controller_ul, self.output_fed_controller_ul)
        self.add_coupling(crosshaul_ul.output_amf_ul, self.output_amf_ul)
        self.add_coupling(crosshaul_ul.output_sdn_controller_ul, self.output_sdn_controller_ul)

    def _dl_external_couplings(self, crosshaul_dl):
        """
        Inserts external couplings for the crosshaul_config downlink
        :param CrosshaulDownLink crosshaul_dl: Crosshaul downlink
        """
        self.add_coupling(self.input_crosshaul_dl, crosshaul_dl.input_crosshaul_dl)
        self.add_coupling(crosshaul_dl.output_ap_dl, self.output_ap_dl)
