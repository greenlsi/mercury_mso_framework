import unittest
from math import inf
from mercury.config.gateway import GatewayConfig
from mercury.config.network import WiredNodeConfig, WirelessNodeConfig, AccessNetworkConfig
from mercury.config.transducers import TransducersConfig
from mercury.model.network.access import WiredAccessNetwork, WirelessAccessNetwork, ChannelShare, NewNodeLocation
from mercury.msg.client import SendPSS
from mercury.msg.packet import PhysicalPacket, NetworkPacket, AppPacket
from mercury.msg.packet.phys_packet import CrosshaulPacket
from typing import Optional
from xdevs.models import Atomic


class DummyAppPacket(AppPacket):
    def __init__(self, node_from: str, node_to: Optional[str], t_gen: float):
        super().__init__(node_from, node_to, 0, 0, t_gen)

    @staticmethod
    def create_msg(node_from: str, node_to: Optional[str], t_gen: float) -> PhysicalPacket:
        app_msg = DummyAppPacket(node_from, node_to, t_gen)
        app_msg.send(t_gen)
        net_msg = NetworkPacket(app_msg, app_msg.node_from)
        net_msg.send(t_gen)
        phys_msg = CrosshaulPacket(node_from, node_to, net_msg)
        phys_msg.send(t_gen)
        return phys_msg


def internal_advance(model: Atomic):
    for port in model.out_ports:
        port.clear()
    model.lambdaf()
    model.deltint()


def external_advance(model: Atomic, e: float):
    for port in model.out_ports:
        port.clear()
    model.deltext(e)
    for port in model.in_ports:
        port.clear()


class AccessNetworkTestCase(unittest.TestCase):
    def test_wired(self):
        TransducersConfig.LOG_NET = False
        gateways = ['olt_1', 'olt_2']
        net_config: AccessNetworkConfig = AccessNetworkConfig('acc')
        for node_id in gateways:
            net_config.add_gateway(GatewayConfig(node_id, (0, 0), True))
        acc: WiredAccessNetwork = WiredAccessNetwork(net_config)
        acc.initialize()
        self.assertEqual(inf, acc.sigma)
        # at t = 0, we create client 1
        client_1 = WiredNodeConfig('client_1', 'olt_1', 0, 2, (0, 0))
        acc.input_create_client.add(client_1)
        external_advance(acc, 0)
        self.assertEqual(inf, acc.sigma)
        self.assertTrue('client_1' in acc.dynamic_nodes)
        self.assertTrue('client_1' in acc.links['olt_1'])
        self.assertTrue('olt_1' in acc.links['client_1'])
        self.assertFalse('client_1' in acc.links['olt_2'])
        self.assertFalse('olt_2' in acc.links['client_1'])
        # at t = 1, we create client 2
        client_2 = WiredNodeConfig('client_2', 'olt_2', 1, 3, (0, 0))
        acc.input_create_client.add(client_2)
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertTrue('client_1' in acc.dynamic_nodes)
        self.assertTrue('client_2' in acc.dynamic_nodes)
        self.assertTrue('client_1' in acc.links['olt_1'])
        self.assertFalse('client_2' in acc.links['olt_1'])
        self.assertTrue('olt_1' in acc.links['client_1'])
        self.assertFalse('olt_1' in acc.links['client_2'])
        self.assertFalse('client_1' in acc.links['olt_2'])
        self.assertTrue('client_2' in acc.links['olt_2'])
        self.assertFalse('olt_2' in acc.links['client_1'])
        self.assertTrue('olt_2' in acc.links['client_2'])
        # at t = 2, we remove client 1
        acc.input_remove_client.add('client_1')
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertFalse('client_1' in acc.dynamic_nodes)
        self.assertTrue('client_2' in acc.dynamic_nodes)
        self.assertFalse(acc.links['olt_1'])
        self.assertFalse('client_1' in acc.links)
        self.assertFalse('olt_1' in acc.links['client_2'])
        self.assertFalse('client_1' in acc.links['olt_2'])
        self.assertTrue('client_2' in acc.links['olt_2'])
        self.assertTrue('olt_2' in acc.links['client_2'])
        # at t = 3, we remove client 2
        acc.input_remove_client.add('client_2')
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertFalse(acc.dynamic_nodes)
        self.assertFalse(acc.links['olt_1'])
        self.assertFalse('client_1' in acc.links)
        self.assertFalse('client_2' in acc.links)
        self.assertFalse(acc.links['olt_2'])

    def test_wired_log(self):
        TransducersConfig.LOG_NET = True
        gateways = ['olt_1', 'olt_2']
        net_config: AccessNetworkConfig = AccessNetworkConfig('acc')
        for node_id in gateways:
            net_config.add_gateway(GatewayConfig(node_id, (0, 0), True))

        acc: WiredAccessNetwork = WiredAccessNetwork(net_config)
        acc.initialize()
        self.assertEqual(inf, acc.sigma)
        # at t = 0, we create client 1
        client_1 = WiredNodeConfig('client_1', 'olt_1', 0, 2, (0, 0))
        acc.input_create_client.add(client_1)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(2, len(acc.output_link_report))
        # at t = 1, we create client 2
        client_2 = WiredNodeConfig('client_2', 'olt_2', 1, 3, (0, 0))
        acc.input_create_client.add(client_2)
        external_advance(acc, 1)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(2, len(acc.output_link_report))
        # at t = 2, we remove client 1
        acc.input_remove_client.add('client_1')
        external_advance(acc, 1)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(2, len(acc.output_link_report))
        # at t = 3, we remove client 2
        acc.input_remove_client.add('client_2')
        external_advance(acc, 1)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(2, len(acc.output_link_report))

    def test_wireless_acc(self):
        TransducersConfig.LOG_NET = True
        net_config: AccessNetworkConfig = AccessNetworkConfig('acc')
        net_config.add_gateway(GatewayConfig('ap_1', (0, 0), False))
        net_config.add_gateway(GatewayConfig('ap_2', (1, 1), False))

        acc: WirelessAccessNetwork = WirelessAccessNetwork(net_config, True)
        acc.initialize()
        self.assertEqual(inf, acc.sigma)
        # at t = 0, we create client 1
        client_1 = WirelessNodeConfig('client_1', 0, 2, 'still', {'location': (0, 0)})
        acc.input_create_client.add(client_1)
        external_advance(acc, 0)
        self.assertEqual(inf, acc.sigma)
        self.assertTrue('client_1' in acc.dynamic_nodes)
        self.assertTrue('client_1' in acc.links['ap_1'])
        self.assertTrue('ap_1' in acc.links['client_1'])
        self.assertTrue('client_1' in acc.links['ap_2'])
        self.assertTrue('ap_2' in acc.links['client_1'])
        # at t = 1, we create client 2
        client_2 = WirelessNodeConfig('client_2', 0, 2, 'still', {'location': (1, 1)})
        acc.input_create_client.add(client_2)
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertTrue('client_1' in acc.dynamic_nodes)
        self.assertTrue('client_2' in acc.dynamic_nodes)
        self.assertTrue('client_1' in acc.links['ap_1'])
        self.assertTrue('ap_1' in acc.links['client_1'])
        self.assertTrue('client_1' in acc.links['ap_2'])
        self.assertTrue('ap_2' in acc.links['client_1'])
        self.assertTrue('client_2' in acc.links['ap_1'])
        self.assertTrue('ap_1' in acc.links['client_2'])
        self.assertTrue('client_2' in acc.links['ap_2'])
        self.assertTrue('ap_2' in acc.links['client_2'])
        # at t = 2, we remove client 1
        acc.input_remove_client.add('client_1')
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertFalse('client_1' in acc.dynamic_nodes)
        self.assertFalse('client_1' in acc.links)
        self.assertTrue('client_2' in acc.dynamic_nodes)
        self.assertFalse('client_1' in acc.links['ap_1'])
        self.assertFalse('client_1' in acc.links['ap_2'])
        self.assertTrue('client_2' in acc.links['ap_1'])
        self.assertTrue('ap_1' in acc.links['client_2'])
        self.assertTrue('client_2' in acc.links['ap_2'])
        self.assertTrue('ap_2' in acc.links['client_2'])

        acc.input_new_location.add(NewNodeLocation('client_2', (1, 1)))
        external_advance(acc, 0)
        self.assertEqual(inf, acc.sigma)
        acc.input_send_pss.add(SendPSS('client_2', 'ap_1'))
        acc.input_new_location.add(NewNodeLocation('client_2', (0, 0)))
        external_advance(acc, 0)
        self.assertEqual(inf, acc.sigma)
        acc.input_new_location.add(NewNodeLocation('client_2', (1, 1)))
        acc.input_send_pss.add(SendPSS('client_2', 'ap_1'))
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual('client_2', acc.outputs_send_pss['ap_1'].get())
        self.assertEqual('client_2', acc.outputs_send_pss['ap_2'].get())
        acc.input_send_pss.add(SendPSS('client_2', 'ap_2'))
        external_advance(acc, 0)
        self.assertEqual(inf, acc.sigma)

        # at t = 3, we remove client 2
        acc.input_remove_client.add('client_2')
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertFalse(acc.dynamic_nodes)
        self.assertFalse('client_1' in acc.links)
        self.assertFalse('client_2' in acc.links)
        self.assertFalse(acc.links['ap_1'])
        self.assertFalse(acc.links['ap_2'])

    def test_wireless_srv(self):
        TransducersConfig.LOG_NET = False
        gateways = ['ap_1', 'ap_2']
        net_config: AccessNetworkConfig = AccessNetworkConfig('acc')
        for node_id in gateways:
            net_config.add_gateway(GatewayConfig(node_id, (0, 0), False))

        acc: WirelessAccessNetwork = WirelessAccessNetwork(net_config, False)
        acc.initialize()
        self.assertEqual(inf, acc.sigma)
        # at t = 0, we create client 1
        client_1 = WirelessNodeConfig('client_1', 0, 2, 'still', {'location': (0, 0)})
        acc.input_create_client.add(client_1)
        external_advance(acc, 0)
        self.assertEqual(inf, acc.sigma)
        self.assertTrue('client_1' in acc.dynamic_nodes)
        self.assertFalse(acc.links['client_1'])
        self.assertFalse('client_1' in acc.links['ap_1'])
        self.assertFalse('client_1' in acc.links['ap_2'])
        # at t = 1, we create client 2
        client_2 = WirelessNodeConfig('client_2', 0, 2, 'still', {'location': (0, 0)})
        acc.input_create_client.add(client_2)
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertTrue('client_1' in acc.dynamic_nodes)
        self.assertTrue('client_2' in acc.dynamic_nodes)
        self.assertFalse(acc.links['client_1'])
        self.assertFalse(acc.links['client_2'])
        self.assertFalse('client_1' in acc.links['ap_1'])
        self.assertFalse('client_1' in acc.links['ap_2'])
        self.assertFalse('client_2' in acc.links['ap_1'])
        self.assertFalse('client_2' in acc.links['ap_2'])
        # at t = 2, we remove client 1
        acc.input_remove_client.add('client_1')
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertFalse('client_1' in acc.dynamic_nodes)
        self.assertTrue('client_2' in acc.dynamic_nodes)
        self.assertFalse('client_1' in acc.links)
        self.assertFalse(acc.links['client_2'])
        self.assertFalse('client_1' in acc.links['ap_1'])
        self.assertFalse('client_1' in acc.links['ap_2'])
        self.assertFalse('client_2' in acc.links['ap_1'])
        self.assertFalse('client_2' in acc.links['ap_2'])
        # at t = 3, we remove client 2
        acc.input_remove_client.add('client_2')
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertFalse('client_1' in acc.dynamic_nodes)
        self.assertFalse('client_2' in acc.dynamic_nodes)
        self.assertFalse('client_1' in acc.links)
        self.assertFalse('client_2' in acc.links)
        self.assertFalse('client_1' in acc.links['ap_1'])
        self.assertFalse('client_1' in acc.links['ap_2'])
        self.assertFalse('client_2' in acc.links['ap_1'])
        self.assertFalse('client_2' in acc.links['ap_2'])

        for client_id in 'client_1', 'client_2', 'client_3':
            client = WirelessNodeConfig(client_id, 0, 2, 'still', {'location': (0, 0)})
            acc.input_create_client.add(client)
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertTrue('client_1' in acc.dynamic_nodes)
        self.assertTrue('client_2' in acc.dynamic_nodes)
        self.assertTrue('client_3' in acc.dynamic_nodes)
        self.assertFalse(acc.links['client_1'])
        self.assertFalse(acc.links['client_2'])
        self.assertFalse(acc.links['client_3'])
        self.assertFalse('client_1' in acc.links['ap_1'])
        self.assertFalse('client_1' in acc.links['ap_2'])
        self.assertFalse('client_2' in acc.links['ap_1'])
        self.assertFalse('client_2' in acc.links['ap_2'])
        self.assertFalse('client_3' in acc.links['ap_1'])
        self.assertFalse('client_3' in acc.links['ap_2'])

        acc.input_share.add(ChannelShare('ap_1', ['client_1', 'client_2']))
        acc.input_share.add(ChannelShare('ap_2', ['client_3']))
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertTrue('ap_1' in acc.links['client_1'])
        self.assertTrue('ap_1' in acc.links['client_2'])
        self.assertFalse('ap_1' in acc.links['client_3'])
        self.assertFalse('ap_2' in acc.links['client_1'])
        self.assertFalse('ap_2' in acc.links['client_2'])
        self.assertTrue('ap_2' in acc.links['client_3'])
        self.assertTrue('client_1' in acc.links['ap_1'])
        self.assertFalse('client_1' in acc.links['ap_2'])
        self.assertTrue('client_2' in acc.links['ap_1'])
        self.assertFalse('client_2' in acc.links['ap_2'])
        self.assertFalse('client_3' in acc.links['ap_1'])
        self.assertTrue('client_3' in acc.links['ap_2'])

        acc.input_new_location.add(NewNodeLocation('client_1', (1, 1)))
        acc.input_new_location.add(NewNodeLocation('client_3', (1, 1)))
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual((1, 1), acc.dynamic_nodes['client_1'].location)
        self.assertEqual((0, 0), acc.dynamic_nodes['client_2'].location)
        self.assertEqual((1, 1), acc.dynamic_nodes['client_3'].location)
        for client_id in 'client_1', 'client_3':
            for gateway_id, link in acc.links[client_id].items():
                self.assertEqual((1, 1), link.link.node_from_location)
                self.assertEqual((1, 1), acc.links[gateway_id][client_id].link.node_to_location)

        acc.input_share.add(ChannelShare('ap_1', ['client_1']))
        acc.input_share.add(ChannelShare('ap_2', ['client_2', 'client_3']))
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertTrue('ap_1' in acc.links['client_1'])
        self.assertFalse('ap_1' in acc.links['client_2'])
        self.assertFalse('ap_1' in acc.links['client_3'])
        self.assertFalse('ap_2' in acc.links['client_1'])
        self.assertTrue('ap_2' in acc.links['client_2'])
        self.assertTrue('ap_2' in acc.links['client_3'])
        self.assertTrue('client_1' in acc.links['ap_1'])
        self.assertFalse('client_1' in acc.links['ap_2'])
        self.assertFalse('client_2' in acc.links['ap_1'])
        self.assertTrue('client_2' in acc.links['ap_2'])
        self.assertFalse('client_3' in acc.links['ap_1'])
        self.assertTrue('client_3' in acc.links['ap_2'])

        for client_id in 'client_1', 'client_2', 'client_3':
            acc.input_remove_client.add(client_id)
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        self.assertFalse('client_1' in acc.dynamic_nodes)
        self.assertFalse('client_2' in acc.dynamic_nodes)
        self.assertFalse('client_3' in acc.dynamic_nodes)
        self.assertFalse('client_1' in acc.links)
        self.assertFalse('client_2' in acc.links)
        self.assertFalse('client_3' in acc.links)
        self.assertFalse('client_1' in acc.links['ap_1'])
        self.assertFalse('client_1' in acc.links['ap_2'])
        self.assertFalse('client_2' in acc.links['ap_1'])
        self.assertFalse('client_2' in acc.links['ap_2'])
        self.assertFalse('client_3' in acc.links['ap_1'])
        self.assertFalse('client_3' in acc.links['ap_2'])

    def test_wireless_srv_log(self):
        TransducersConfig.LOG_NET = True
        gateways = ['ap_1', 'ap_2']
        net_config: AccessNetworkConfig = AccessNetworkConfig('acc', wireless_div_id='equal')
        for node_id in gateways:
            net_config.add_gateway(GatewayConfig(node_id, (0, 0), False))

        acc: WirelessAccessNetwork = WirelessAccessNetwork(net_config, False)
        acc.initialize()
        self.assertEqual(inf, acc.sigma)
        # at t = 0, we create client 1
        client_1 = WirelessNodeConfig('client_1', 0, 2, 'still', {'location': (0, 0)})
        acc.input_create_client.add(client_1)
        external_advance(acc, 0)
        self.assertEqual(inf, acc.sigma)
        # at t = 1, we create client 2
        client_2 = WirelessNodeConfig('client_2', 0, 2, 'still', {'location': (0, 0)})
        acc.input_create_client.add(client_2)
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        # at t = 2, we remove client 1
        acc.input_remove_client.add('client_1')
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)
        # at t = 3, we remove client 2
        acc.input_remove_client.add('client_2')
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)

        for client_id in 'client_1', 'client_2', 'client_3':
            client = WirelessNodeConfig(client_id, 0, 2, 'still', {'location': (0, 0)})
            acc.input_create_client.add(client)
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)

        acc.input_share.add(ChannelShare('ap_1', ['client_1', 'client_2']))
        acc.input_share.add(ChannelShare('ap_2', ['client_3']))
        external_advance(acc, 1)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(6, len(acc.output_link_report))

        acc.input_new_location.add(NewNodeLocation('client_1', (1, 1)))
        acc.input_new_location.add(NewNodeLocation('client_3', (1, 1)))
        external_advance(acc, 1)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(4, len(acc.output_link_report))

        acc.input_share.add(ChannelShare('ap_1', ['client_1']))
        acc.input_share.add(ChannelShare('ap_2', ['client_2', 'client_3']))
        external_advance(acc, 1)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(8, len(acc.output_link_report))  # client_2 disconnects from one AP to another!

        acc.input_share.add(ChannelShare('ap_1', []))
        acc.input_share.add(ChannelShare('ap_2', []))
        external_advance(acc, 1)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(6, len(acc.output_link_report))  # client_2 disconnects from one AP to another!

        for client_id in 'client_1', 'client_2', 'client_3':
            acc.input_remove_client.add(client_id)
        external_advance(acc, 1)
        self.assertEqual(inf, acc.sigma)


if __name__ == '__main__':
    unittest.main()
