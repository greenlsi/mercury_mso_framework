import unittest
from math import inf
from mercury.config.transducers import TransducersConfig
from mercury.model.network.network import NetworkConfig, LinkConfig, StaticNodeConfig
from mercury.model.network.xh import CrosshaulNetwork
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


class CrosshaulNetworkTestCase(unittest.TestCase):
    def test_xh(self):
        TransducersConfig.LOG_NET = False
        clock: float = 0
        nodes = ['node_1', 'node_2', 'node_3']
        link_config = LinkConfig(penalty_delay=1)
        net_config: NetworkConfig = NetworkConfig('xh')
        for node_id in nodes:
            net_config.add_node(StaticNodeConfig(node_id, (0, 0)))
        net_config.connect_all(link_config)
        self.assertEqual(len(nodes), len(net_config.nodes))
        for links in net_config.links.values():
            self.assertEqual(len(nodes) - 1, len(links))
            for link in links.values():
                self.assertEqual(link_config, link)
        xh: CrosshaulNetwork = CrosshaulNetwork(net_config)
        xh.initialize()
        self.assertEqual(inf, xh.sigma)

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                msg = DummyAppPacket.create_msg(nodes[i], nodes[j], clock)
                xh.input_data.add(msg)
                msg = DummyAppPacket.create_msg(nodes[j], nodes[i], clock)
                xh.input_data.add(msg)
        external_advance(xh, 0)
        self.assertEqual(1, xh.sigma)  # penalty delay
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                msg = DummyAppPacket.create_msg(nodes[i], nodes[j], clock + 0.5)
                xh.input_data.add(msg)
                msg = DummyAppPacket.create_msg(nodes[j], nodes[i], clock + 0.5)
                xh.input_data.add(msg)
        clock += 0.5
        external_advance(xh, 0.5)
        self.assertEqual(0.5, xh.sigma)

        clock += xh.sigma
        internal_advance(xh)
        self.assertEqual(0, xh.sigma)
        internal_advance(xh)
        self.assertEqual(0.5, xh.sigma)
        for port in xh.outputs_data.values():
            self.assertEqual(len(nodes) - 1, len(port))
        clock += xh.sigma
        internal_advance(xh)
        self.assertEqual(0, xh.sigma)
        internal_advance(xh)
        self.assertEqual(inf, xh.sigma)
        for port in xh.outputs_data.values():
            self.assertEqual(len(nodes) - 1, len(port))

        for i in range(len(nodes)):
            msg = DummyAppPacket.create_msg(nodes[i], None, clock)
            xh.input_data.add(msg)
        external_advance(xh, 0)
        self.assertEqual(1, xh.sigma)
        clock += xh.sigma
        internal_advance(xh)
        self.assertEqual(0, xh.sigma)
        internal_advance(xh)
        self.assertEqual(inf, xh.sigma)
        for port in xh.outputs_data.values():
            self.assertEqual(len(nodes) - 1, len(port))

    def test_logs(self):
        NetworkConfig.LOG_NETWORK_LINKS = True
        clock: float = 0
        nodes = ['node_1', 'node_2', 'node_3']
        link_config = LinkConfig(penalty_delay=1)
        net_config: NetworkConfig = NetworkConfig('xh')
        for node_id in nodes:
            net_config.add_node(StaticNodeConfig(node_id, (0, 0)))
        net_config.connect_all(link_config)
        self.assertEqual(len(nodes), len(net_config.nodes))
        for links in net_config.links.values():
            self.assertEqual(len(nodes) - 1, len(links))
            for link in links.values():
                self.assertEqual(link_config, link)
        xh: CrosshaulNetwork = CrosshaulNetwork(net_config)
        xh.initialize()
        self.assertEqual(0, xh.sigma)
        internal_advance(xh)
        self.assertEqual(inf, xh.sigma)
        self.assertEqual(len(nodes) * (len(nodes) - 1), len(xh.output_link_report))


if __name__ == '__main__':
    unittest.main()
