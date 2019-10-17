from xdevs.models import Coupled, Port
from ..common.packet.physical import PhysicalPacket
from ..common.packet.network import NetworkPacketConfiguration
from ..common.packet.application.ran import RadioAccessNetworkConfiguration
from ..common.packet.application.ran.ran_access import NewUpLinkMCS
from ..common.mobility import NewLocation
from ..common.crosshaul import CrosshaulConfiguration
from ..common.radio import RadioConfiguration
from .ap import AccessPoint
from .radio_mux import AccessPointRadioMultiplexer
from .crosshaul_mux import AccessPointCrosshaulMultiplexer


class AccessPoints(Coupled):
    """
    Access Points layer DEVS module.

    :param str name: name of the DEVS module
    :param dict aps_config: Access Points configuration list {AP ID: AP configuration}
    :param str amf_id: ID of the AMF core function
    :param RadioAccessNetworkConfiguration rac_config: radio pxcch network configuration
    :param NetworkPacketConfiguration network_config: network packet configuration
    :param CrosshaulConfiguration crosshaul_config: crosshaul_config configuration
    :param RadioConfiguration radio_config: radio interface configuration
    """
    def __init__(self, name, aps_config, amf_id, rac_config, network_config, crosshaul_config, radio_config):
        super().__init__(name)
        # Unwrap configuration parameters
        ap_ids = [a for a in aps_config]
        if len(ap_ids) != len(set(ap_ids)):
            raise ValueError('AP IDs must be unique')

        # Create submodules and add them to the coupled model
        aps = [AccessPoint(name + '_ap_' + ap_id, ap_config, amf_id, rac_config, network_config, crosshaul_config,
                           radio_config) for ap_id, ap_config in aps_config.items()]
        radio_mux = AccessPointRadioMultiplexer(name + '_radio_mux', ap_ids)
        crosshaul_mux = AccessPointCrosshaulMultiplexer(name + '_crosshaul_mux', ap_ids)
        [self.add_component(ap) for ap in aps]
        self.add_component(radio_mux)
        self.add_component(crosshaul_mux)

        # Crosshaul-related input/output ports
        self.input_crosshaul_dl = Port(PhysicalPacket, name + '_input_crosshaul_dl')
        self.input_crosshaul_ul = Port(PhysicalPacket, name + '_input_crosshaul_ul')
        self.output_crosshaul_dl = Port(PhysicalPacket, name + '_output_crosshaul_dl')
        self.output_crosshaul_ul = Port(PhysicalPacket, name + '_output_crosshaul_ul')
        self.add_in_port(self.input_crosshaul_dl)
        self.add_in_port(self.input_crosshaul_ul)
        self.add_out_port(self.output_crosshaul_dl)
        self.add_out_port(self.output_crosshaul_ul)

        # Radio-related input/output ports
        self.input_radio_control_ul = Port(PhysicalPacket, name + '_input_radio_control_ul')
        self.input_radio_transport_ul = Port(PhysicalPacket, name + '_input_radio_transport_ul')
        self.output_radio_bc = Port(PhysicalPacket, name + '_output_radio_bc')
        self.output_radio_control_dl = Port(PhysicalPacket, name + '_output_radio_control_dl')
        self.output_radio_transport_dl = Port(PhysicalPacket, name + '_output_radio_transport_dl')
        self.add_in_port(self.input_radio_control_ul)
        self.add_in_port(self.input_radio_transport_ul)
        self.add_out_port(self.output_radio_bc)
        self.add_out_port(self.output_radio_control_dl)
        self.add_out_port(self.output_radio_transport_dl)

        # Handy ports
        self.input_new_ue_location = Port(NewLocation, name + '_input_new_ue_location')
        self.output_ul_mcs = Port(NewUpLinkMCS, name + '_output_new_ul_mcs')
        self.add_in_port(self.input_new_ue_location)
        self.add_out_port(self.output_ul_mcs)

        self._radio_mux_external_coupling(radio_mux)
        self._crosshaul_mux_external_coupling(crosshaul_mux)
        for ap in aps:
            self._ap_external_coupling(ap)
            self._crosshaul_mux_ap_internal_coupling(crosshaul_mux, ap)
            self._radio_mux_ap_internal_coupling(radio_mux, ap)

    def _radio_mux_external_coupling(self, radio_mux):
        """
        Add external couplings for radio multiplexer
        :param AccessPointRadioMultiplexer radio_mux: Radio multiplexer
        """
        self.add_coupling(self.input_radio_control_ul, radio_mux.input_control_ul)
        self.add_coupling(self.input_radio_transport_ul, radio_mux.input_transport_ul)

    def _crosshaul_mux_external_coupling(self, crosshaul_mux):
        """
        Add external coupling for crosshaul_config multiplexer
        :param AccessPointCrosshaulMultiplexer crosshaul_mux: Crosshaul multiplexer
        """
        self.add_coupling(self.input_crosshaul_ul, crosshaul_mux.input_crosshaul_ul)
        self.add_coupling(self.input_crosshaul_dl, crosshaul_mux.input_crosshaul_dl)

    def _ap_external_coupling(self, ap):
        """
        Add external coupling for Access Points
        :param AccessPoint ap: Access Point
        """
        self.add_coupling(self.input_new_ue_location, ap.input_new_ue_location)
        self.add_coupling(ap.output_ul_mcs, self.output_ul_mcs)
        self.add_coupling(ap.output_crosshaul_ul, self.output_crosshaul_ul)
        self.add_coupling(ap.output_crosshaul_dl, self.output_crosshaul_dl)
        self.add_coupling(ap.output_radio_bc, self.output_radio_bc)
        self.add_coupling(ap.output_radio_control_dl, self.output_radio_control_dl)
        self.add_coupling(ap.output_radio_transport_dl, self.output_radio_transport_dl)

    def _crosshaul_mux_ap_internal_coupling(self, crosshaul_mux, ap):
        """
        Add internal couplings between Crosshaul Multiplexer and Access Point
        :param AccessPointCrosshaulMultiplexer crosshaul_mux: Crosshaul Multiplexer
        :param AccessPoint ap: Access Point
        """
        self.add_coupling(crosshaul_mux.outputs_crosshaul_ul[ap.ap_id], ap.input_crosshaul_ul)
        self.add_coupling(crosshaul_mux.outputs_crosshaul_dl[ap.ap_id], ap.input_crosshaul_dl)

    def _radio_mux_ap_internal_coupling(self, radio_mux, ap):
        """
        Add internal couplings between Radio Multiplexer and Access Point
        :param AccessPointRadioMultiplexer radio_mux: Radio Multiplexer
        :param AccessPoint ap: Access Point
        """
        self.add_coupling(radio_mux.outputs_control_ul[ap.ap_id], ap.input_radio_control_ul)
        self.add_coupling(radio_mux.outputs_transport_ul[ap.ap_id], ap.input_radio_transport_ul)
