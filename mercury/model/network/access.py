from __future__ import annotations
from mercury.config.network import DynamicNodeConfig, AccessNetworkConfig
from mercury.msg.client import SendPSS
from mercury.msg.network import NetworkLinkReport, NewNodeLocation, ChannelShare
from mercury.msg.packet import PhysicalPacket, PacketInterface
from typing import Type
from xdevs.models import Coupled, Port
from .network import LinkStructure, WiredAccessNetwork, WirelessAccessNetwork


class AccessNetwork(Coupled):
    def __init__(self, net_config: AccessNetworkConfig):
        """
        Access Network DEVS model. It contains wired and wireless access networks.
        :param net_config: Access network configuration.
        """
        super().__init__(net_config.network_id)
        self.input_create_client: Port[DynamicNodeConfig] = Port(DynamicNodeConfig, 'input_create_client')
        self.input_new_location: Port[NewNodeLocation] = Port(NewNodeLocation, "input_new_location")
        self.input_remove_client: Port[str] = Port(str, 'input_remove_client')
        self.input_send_pss: Port[SendPSS] = Port(SendPSS, 'input_send_pss')
        self.input_share: Port[ChannelShare] = Port(ChannelShare, 'input_share')
        self.input_wired: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_wired')
        self.input_wireless_acc: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_wireless_acc')
        self.input_wireless_srv: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_wireless_srv')
        self.output_dl: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_wired_dl')
        self.output_link_report: Port[NetworkLinkReport] = Port(NetworkLinkReport, 'output_link_report')

        self.add_in_port(self.input_create_client)
        self.add_in_port(self.input_new_location)
        self.add_in_port(self.input_remove_client)
        self.add_in_port(self.input_send_pss)
        self.add_in_port(self.input_share)
        self.add_in_port(self.input_wired)
        self.add_in_port(self.input_wireless_acc)
        self.add_in_port(self.input_wireless_srv)
        self.add_out_port(self.output_dl)
        self.add_out_port(self.output_link_report)

        self.outputs_ul: dict[str, Port[PhysicalPacket]] = dict()
        self.outputs_send_pss: dict[str, Port[str]] = dict()
        for gateway_id in net_config.wired_config.nodes:
            self.outputs_ul[gateway_id] = Port(PhysicalPacket, f'output_{gateway_id}_ul')
            self.add_out_port(self.outputs_ul[gateway_id])
        for gateway_id in net_config.wireless_config.nodes:
            self.outputs_ul[gateway_id] = Port(PhysicalPacket, f'output_{gateway_id}_ul')
            self.outputs_send_pss[gateway_id] = Port(str, f'output_{gateway_id}_send_pss')
            self.add_out_port(self.outputs_ul[gateway_id])
            self.add_out_port(self.outputs_send_pss[gateway_id])

        wired: WiredAccessNetwork = WiredAccessNetwork(net_config)
        wireless_acc: WirelessAccessNetwork = WirelessAccessNetwork(net_config, True)
        wireless_srv: WirelessAccessNetwork = WirelessAccessNetwork(net_config, False)
        for component, in_port in (wired, self.input_wired), \
                                  (wireless_acc, self.input_wireless_acc), (wireless_srv, self.input_wireless_srv):
            self.add_component(component)
            self.add_coupling(in_port, component.input_data)
            self.add_coupling(self.input_create_client, component.input_create_client)
            self.add_coupling(self.input_remove_client, component.input_remove_client)
            self.add_coupling(component.output_clients, self.output_dl)
            for gw_id, out_gw in component.outputs_data.items():
                self.add_coupling(out_gw, self.outputs_ul[gw_id])
        self.add_coupling(self.input_new_location, wireless_acc.input_new_location)
        self.add_coupling(self.input_new_location, wireless_srv.input_new_location)
        self.add_coupling(self.input_send_pss, wireless_acc.input_send_pss)
        self.add_coupling(self.input_share, wireless_srv.input_share)
        self.add_coupling(wired.output_link_report, self.output_link_report)
        self.add_coupling(wireless_srv.output_link_report, self.output_link_report)
        for gateway_id, out_port in wireless_acc.outputs_send_pss.items():
            self.add_coupling(out_port, self.outputs_send_pss[gateway_id])

    @staticmethod
    def new_access(p_type: Type[PacketInterface], net_config: AccessNetworkConfig) -> AccessNetwork | AccessNetworkShortcut:
        return AccessNetwork(net_config) if p_type == PhysicalPacket else AccessNetworkShortcut(net_config)


class AccessNetworkShortcut(WirelessAccessNetwork):
    def __init__(self, net_config: AccessNetworkConfig):
        net_config.network_id = f'{net_config.network_id}_shortcut'
        super().__init__(net_config, True)

    def send_message_through_link(self, link_struct: LinkStructure, msg: PhysicalPacket):
        """In shortcut network, messages are automatically forwarded after applying the SNR to the message."""
        link_struct.link.prepare_msg(msg)
        self.add_msg_to_queue(self.output_clients, msg)
