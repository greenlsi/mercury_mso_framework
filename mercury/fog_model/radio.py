from typing import Dict
from xdevs.models import Coupled, Port
from mercury.config.network import NodeConfig
from mercury.config.radio import RadioConfig
from mercury.msg.network import RadioPacket, NodeLocation, NetworkLinkReport, EnableChannels
from .common import Multiplexer
from .network import Network, MasterNetwork, SlaveNetwork


class RadioMux(Multiplexer):

    def __init__(self, aps):
        self.input_pusch = Port(RadioPacket, "input_pusch")
        self.input_pucch = Port(RadioPacket, "input_pucch")
        self.outputs_pusch = {ap_id: Port(RadioPacket, "output_pusch_" + ap_id) for ap_id in aps}
        self.outputs_pucch = {ap_id: Port(RadioPacket, "output_pucch_" + ap_id) for ap_id in aps}

        super().__init__('radio_multiplexer', aps)

        self.add_in_port(self.input_pusch)
        self.add_in_port(self.input_pucch)
        for ap_id in aps:
            self.add_out_port(self.outputs_pusch[ap_id])
            self.add_out_port(self.outputs_pucch[ap_id])

    def build_routing_table(self):
        self.routing_table[self.input_pusch] = dict()
        self.routing_table[self.input_pucch] = dict()
        for ap_id in self.node_ids:
            self.routing_table[self.input_pusch][ap_id] = self.outputs_pusch[ap_id]
            self.routing_table[self.input_pucch][ap_id] = self.outputs_pucch[ap_id]

    def get_node_to(self, msg):
        return msg.node_to


class Radio(Coupled):
    """
    Radio Layer xDEVS Module

    :param radio_config: Radio layer Configuration
    :param aps: Dictionary {AP ID: AP Radio Node Configuration}
    """
    def __init__(self, radio_config: RadioConfig, aps: Dict[str, NodeConfig]):

        super().__init__('radio')

        self.input_create_node = Port(NodeConfig, 'input_create_ue')
        self.input_new_location = Port(NodeLocation, "input_new_location")
        self.input_remove_node = Port(str, 'input_remove_ue')
        self.input_enable_channels = Port(EnableChannels, "input_enable_channels")
        self.input_pbch = Port(RadioPacket, "input_pbch")
        self.input_pdsch = Port(RadioPacket, "input_pdsch")
        self.input_pdcch = Port(RadioPacket, "input_pdcch")
        self.input_pusch = Port(RadioPacket, "input_pusch")
        self.input_pucch = Port(RadioPacket, "input_pucch")
        self.output_pbch = Port(RadioPacket, "output_pbch")
        self.output_pdsch = Port(RadioPacket, "output_pbch")
        self.output_pdcch = Port(RadioPacket, "output_pbch")
        self.output_dl_report = Port(NetworkLinkReport, "output_dl_report")
        self.output_ul_report = Port(NetworkLinkReport, "output_ul_report")

        self.add_in_port(self.input_create_node)
        self.add_in_port(self.input_new_location)
        self.add_in_port(self.input_remove_node)
        self.add_in_port(self.input_enable_channels)
        self.add_in_port(self.input_pbch)
        self.add_in_port(self.input_pdsch)
        self.add_in_port(self.input_pdcch)
        self.add_in_port(self.input_pusch)
        self.add_in_port(self.input_pucch)
        self.add_out_port(self.output_pbch)
        self.add_out_port(self.output_pdsch)
        self.add_out_port(self.output_pdcch)
        self.add_out_port(self.output_dl_report)
        self.add_out_port(self.output_ul_report)

        self.outputs_pusch = dict()
        self.outputs_pucch = dict()
        for network_name, nodes_to, outputs in [('pusch', aps, self.outputs_pusch), ('pucch', aps, self.outputs_pucch)]:
            for node_to in nodes_to:
                outputs[node_to] = Port(RadioPacket, "output_{}_{}".format(network_name, node_to))
                self.add_out_port(outputs[node_to])

        # Create and add sub-components
        pbch = Network(aps, radio_config.base_dl_config, dyn_node_type=NodeConfig.RECEIVER, name='radio_pbch')
        pdcch = Network(aps, radio_config.base_dl_config, dyn_node_type=NodeConfig.RECEIVER, name='radio_pdcch')
        pucch = Network(aps, radio_config.base_ul_config, dyn_node_type=NodeConfig.TRANSMITTER, name='radio_pucch')
        pdsch = MasterNetwork(aps, radio_config.base_dl_config, radio_config.channel_div_name,
                              radio_config.channel_div_config, name='radio_pdsch')
        pusch = SlaveNetwork(aps, radio_config.base_ul_config, name='radio_pusch')

        for component, in_port in [(pbch, self.input_pbch), (pdsch, self.input_pdsch), (pdcch, self.input_pdcch),
                                   (pusch, self.input_pusch), (pucch, self.input_pucch)]:
            self.add_component(component)
            self.add_coupling(in_port, component.input_data)
            self.add_coupling(self.input_create_node, component.input_create_node)
            self.add_coupling(self.input_new_location, component.input_new_location)
            self.add_coupling(self.input_remove_node, component.input_remove_node)

        # For transducers
        self.add_coupling(pdsch.output_link_report, self.output_dl_report)
        self.add_coupling(pusch.output_link_report, self.output_ul_report)

        # Outputs to UEs
        self.add_coupling(pbch.output_data, self.output_pbch)
        self.add_coupling(pdsch.output_data, self.output_pdsch)
        self.add_coupling(pdcch.output_data, self.output_pdcch)
        # Master-Slave network coupling
        self.add_coupling(self.input_enable_channels, pdsch.input_enable_channels)
        self.add_coupling(pdsch.output_channel_share, pusch.input_channel_share)

        mux = RadioMux(aps)
        self.add_component(mux)
        self.add_coupling(pusch.output_data, mux.input_pusch)
        self.add_coupling(pucch.output_data, mux.input_pucch)
        for ap_id in aps:
            self.add_coupling(mux.outputs_pusch[ap_id], self.outputs_pusch[ap_id])
            self.add_coupling(mux.outputs_pucch[ap_id], self.outputs_pucch[ap_id])


class RadioShortcut(Network):
    def __init__(self, radio_config: RadioConfig, aps: Dict[str, NodeConfig]):
        super().__init__(aps, radio_config.base_dl_config, dyn_node_type=NodeConfig.RECEIVER, name='radio_shortcut')
