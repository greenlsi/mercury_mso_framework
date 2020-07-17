from xdevs.models import Coupled, Port
from typing import Dict
from .common.packet.packet import PhysicalPacket
from .network import Nodes, NodeLocation, NodeConfiguration, LinkConfiguration, TransceiverConfiguration, Network,\
    MasterNetwork, SlaveNetwork, NetworkLinkReport, EnableChannels


class RadioConfiguration:

    UL_MCS_TABLE_5G = {
        0: 0.2344, 1: 0.3770, 2: 0.6016, 3: 0.8770, 4: 1.1758, 5: 1.4766, 6: 1.6953, 7: 1.9141, 8: 2.1602, 9: 2.4063,
        10: 2.5703, 11: 2.7305, 12: 3.0293, 13: 3.3223, 14: 3.6094, 15: 3.9023, 16: 4.2129, 17: 4.5234, 18: 4.8164,
        19: 5.1152, 20: 5.3320, 21: 5.5547, 22: 5.8906, 23: 6.2266, 24: 6.5703, 25: 6.9141, 26: 7.1602, 27: 7.4063
    }

    DL_MCS_TABLE_5G = {
        0: 0.2344, 1: 0.3066, 2: 0.3770, 3: 0.4902, 4: 0.6016, 5: 0.7402, 6: 0.8770, 7: 1.0273, 8: 1.1758, 9: 1.3262,
        10: 1.3281, 11: 1.4766, 12: 1.6953, 13: 1.9141, 14: 2.1602, 15: 2.4063, 16: 2.5703, 17: 2.5664, 18: 2.7305,
        19: 3.0293, 20: 3.3223, 21: 3.6094, 22: 3.9023, 23: 4.2129, 24: 4.5234, 25: 4.8164, 26: 5.1152, 27: 5.3320,
        28: 5.5547
    }

    def __init__(self, base_dl_config: LinkConfiguration = None, base_ul_config: LinkConfiguration = None,
                 base_dl_transceiver_config: TransceiverConfiguration = None,
                 base_ul_transceiver_config: TransceiverConfiguration = None, channel_div_name: str = 'equal',
                 channel_div_config: Dict = None):
        """

        :param base_dl_config:
        :param base_ul_config:
        :param base_dl_transceiver_config:
        :param base_ul_transceiver_config:
        :param channel_div_name:
        :param channel_div_config:
        """
        if base_dl_config is None:
            base_dl_config = LinkConfiguration(carrier_freq=33e9, att_name='fspl')
        self.base_dl_config = base_dl_config

        if base_ul_config is None:
            base_ul_config = LinkConfiguration(carrier_freq=33e9, att_name='fspl')
        self.base_ul_config = base_ul_config

        if base_dl_transceiver_config is None:
            base_dl_transceiver_config = TransceiverConfiguration(tx_power=50, mcs_table=self.DL_MCS_TABLE_5G)
        self.base_dl_transceiver_config = base_dl_transceiver_config

        if base_ul_transceiver_config is None:
            base_ul_transceiver_config = TransceiverConfiguration(tx_power=30, mcs_table=self.UL_MCS_TABLE_5G)
        self.base_ul_transceiver_config = base_ul_transceiver_config

        self.channel_div_name = channel_div_name
        if channel_div_config is None:
            channel_div_config = dict()
        self.channel_div_config = channel_div_config

        self.dl_header = base_dl_config.header
        self.ul_header = base_ul_config.header

        self.aps = None
        self.ues = None

        self.dl_template = None
        self.ul_template = None

        self.built_pbch = None
        self.built_pdsch = None
        self.built_pdcch = None
        self.built_pusch = None
        self.built_pucch = None

    def define_nodes(self, aps: Dict[str, NodeConfiguration], ues: Dict[str, NodeConfiguration]):
        if self.dl_template is not None or self.ul_template is not None:
            raise ValueError("Nodes already defined")
        self.aps = dict()
        self.ues = dict()
        self.dl_template = dict()
        self.ul_template = dict()
        for ap_id, ap_config in aps.items():
            self.dl_template[ap_id] = dict()
            if ap_config.node_trx is None:
                ap_config.node_trx = self.base_dl_transceiver_config
            self.aps[ap_id] = ap_config
            for ue_id, ue_config in ues.items():
                if ue_id not in self.ul_template:
                    self.ul_template[ue_id] = dict()
                    if ue_config.node_trx is None:
                        ue_config.node_trx = self.base_ul_transceiver_config
                    self.ues[ue_id] = ue_config
                self.dl_template[ap_id][ue_id] = self.base_dl_config
                self.ul_template[ue_id][ap_id] = self.base_ul_config


class Radio(Coupled):
    """
    Radio Layer xDEVS Module
    :param name: xDEVS module name
    :param radio_config: Radio layer Configuration
    :param ues: Dictionary {UE ID: UE Node Configuration}
    :param aps: Dictionary {AP ID: AP Radio Node Configuration}
    """
    def __init__(self, name: str, radio_config: RadioConfiguration, ues: Dict[str, NodeConfiguration],
                 aps: Dict[str, NodeConfiguration]):

        super().__init__(name)

        self.input_pbch = Port(PhysicalPacket, "input_pbch")
        self.input_pdsch = Port(PhysicalPacket, "input_pdsch")
        self.input_pdcch = Port(PhysicalPacket, "input_pdcch")
        self.input_pusch = Port(PhysicalPacket, "input_pusch")
        self.input_pucch = Port(PhysicalPacket, "input_pucch")
        self.output_dl_report = Port(NetworkLinkReport, "output_dl_report")
        self.output_ul_report = Port(NetworkLinkReport, "output_ul_report")
        self.input_repeat_location = Port(str, "input_repeat_location")
        self.output_node_location = Port(NodeLocation, "output_node_location")
        self.input_enable_channels = Port(EnableChannels, "input_enable_channels")

        self.add_in_port(self.input_pbch)
        self.add_in_port(self.input_pdsch)
        self.add_in_port(self.input_pdcch)
        self.add_in_port(self.input_pusch)
        self.add_in_port(self.input_pucch)
        self.add_in_port(self.output_dl_report)
        self.add_in_port(self.output_ul_report)
        self.add_in_port(self.input_repeat_location)
        self.add_out_port(self.output_node_location)
        self.add_in_port(self.input_enable_channels)

        # Ports for PBCH channel
        self.outputs_pbch = dict()
        self.outputs_pdsch = dict()
        self.outputs_pdcch = dict()
        self.outputs_pusch = dict()
        self.outputs_pucch = dict()

        config_loop = [
            ('pbch', ues, self.outputs_pbch), ('pdsch', ues, self.outputs_pdsch), ('pdcch', ues, self.outputs_pdcch),
            ('pusch', aps, self.outputs_pusch), ('pucch', aps, self.outputs_pucch),
        ]
        for network_name, nodes_to, outputs in config_loop:
            for node_to in nodes_to:
                outputs[node_to] = Port(PhysicalPacket, "output_{}_{}".format(network_name, node_to))
                self.add_out_port(outputs[node_to])

        default_ap_trx = radio_config.base_dl_transceiver_config
        for ap_config in aps.values():
            if ap_config.node_trx is None:
                ap_config.node_trx = default_ap_trx
        default_ue_trx = radio_config.base_ul_transceiver_config
        for ue_config in ues.values():
            if ue_config.node_trx is None:
                ue_config.node_trx = default_ue_trx

        # Create and add sub-components
        radio_config.define_nodes(aps, ues)
        nodes = {**aps, **ues}
        pbch = Network(name + "_pbch", nodes, radio_config.base_dl_config, radio_config.dl_template)
        pdcch = Network(name + "_pdcch", nodes, radio_config.base_dl_config, radio_config.dl_template)
        pucch = Network(name + "_pucch", nodes, radio_config.base_ul_config, radio_config.ul_template)
        pdsch = MasterNetwork(name + "_pdsch", aps, ues, radio_config.base_dl_config, radio_config.dl_template,
                              radio_config.channel_div_name, radio_config.channel_div_config)
        pusch = SlaveNetwork(name + "_pusch", aps, ues, radio_config.base_ul_config, radio_config.ul_template)

        nodes_mobility = Nodes(name + '_nodes', nodes)
        self.add_component(nodes_mobility)
        self.add_coupling(self.input_repeat_location, nodes_mobility.input_repeat_location)
        self.add_coupling(nodes_mobility.output_node_location, self.output_node_location)

        for component in [pbch, pdsch, pdcch, pusch, pucch]:
            self.add_component(component)
            self.add_coupling(nodes_mobility.output_node_location, component.input_node_location)

        # For transducers
        self.add_coupling(pdsch.output_link_report, self.output_dl_report)
        self.add_coupling(pusch.output_link_report, self.output_ul_report)

        for component, in_port in [(pbch, self.input_pbch), (pdsch, self.input_pdsch), (pdcch, self.input_pdcch),
                                   (pusch, self.input_pusch), (pucch, self.input_pucch)]:
            self.add_coupling(in_port, component.input_data)

        for ue_id in ues:
            self.add_coupling(pbch.outputs_node_to[ue_id], self.outputs_pbch[ue_id])
            self.add_coupling(pdsch.outputs_node_to[ue_id], self.outputs_pdsch[ue_id])
            self.add_coupling(pdcch.outputs_node_to[ue_id], self.outputs_pdcch[ue_id])

        for ap_id in aps:
            self.add_coupling(pusch.outputs_node_to[ap_id], self.outputs_pusch[ap_id])
            self.add_coupling(pucch.outputs_node_to[ap_id], self.outputs_pucch[ap_id])

        # Master-Slave network coupling
        self.add_coupling(self.input_enable_channels, pdsch.input_enable_channels)
        self.add_coupling(pdsch.output_channel_share, pusch.input_channel_share)


class RadioShortcut(Coupled):
    def __init__(self, name: str, radio_config: RadioConfiguration, ues: Dict[str, NodeConfiguration],
                 aps: Dict[str, NodeConfiguration]):

        super().__init__(name)

        self.input_pbch = Port(PhysicalPacket, "input_pbch")
        self.input_repeat_location = Port(str, "input_repeat_location")
        self.output_node_location = Port(NodeLocation, "output_node_location")

        self.add_in_port(self.input_pbch)
        self.add_in_port(self.input_repeat_location)
        self.add_out_port(self.output_node_location)

        # Ports for PBCH channel
        self.outputs_pbch = dict()
        for ue_id in ues:
            self.outputs_pbch[ue_id] = Port(PhysicalPacket, "output_pbch_" + ue_id)
            self.add_out_port(self.outputs_pbch[ue_id])

        # Create and add sub-components
        radio_config.define_nodes(aps, ues)
        nodes = {**aps, **ues}

        pbch = Network(name + "_pbch", nodes, radio_config.base_dl_config, radio_config.dl_template)
        nodes_mobility = Nodes(name + '_nodes', nodes)
        self.add_component(pbch)
        self.add_component(nodes_mobility)

        self.add_coupling(nodes_mobility.output_node_location, pbch.input_node_location)

        self.add_coupling(self.input_repeat_location, nodes_mobility.input_repeat_location)
        self.add_coupling(nodes_mobility.output_node_location, self.output_node_location)

        self.add_coupling(self.input_pbch, pbch.input_data)
        for ue_id in ues:
            self.add_coupling(pbch.outputs_node_to[ue_id], self.outputs_pbch[ue_id])
