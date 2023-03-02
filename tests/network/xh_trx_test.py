import unittest
from math import inf
from mercury.model.network.xh import CrosshaulTransceiver
from mercury.msg.packet import PhysicalPacket, NetworkPacket, AppPacket
from mercury.msg.packet.phys_packet import CrosshaulPacket
from mercury.utils.amf import AccessManagementFunction
from xdevs.models import Atomic


class DummyAppPacket(AppPacket):
    def __init__(self, node_from: str, node_to: str, t_gen: float):
        super().__init__(node_from, node_to, 0, 0, t_gen)

    @staticmethod
    def create_net_msg(node_from: str, node_to: str, t_gen: float) -> NetworkPacket:
        app_msg = DummyAppPacket(node_from, node_to, t_gen)
        app_msg.send(t_gen)
        net_msg = NetworkPacket(app_msg, app_msg.node_from)
        net_msg.send(t_gen)
        return net_msg

    @staticmethod
    def create_phys_msg(node_from: str, node_to: str, t_gen: float) -> PhysicalPacket:
        net_msg = DummyAppPacket.create_net_msg(node_from, node_to, t_gen)
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


class CoreTransceiverTestCase(unittest.TestCase):
    def test_trx(self):
        amf: AccessManagementFunction = AccessManagementFunction({'gateway'})
        trx = CrosshaulTransceiver('node', amf)
        trx.initialize()
        self.assertEqual(inf, trx.sigma)

        amf.connect_client('client', 'gateway')
        phys_to_core = DummyAppPacket.create_phys_msg('dummy', 'node', 0)
        phys_to_other = DummyAppPacket.create_phys_msg('dummy', 'other', 0)
        trx.input_phys.add(phys_to_core)
        trx.input_phys.add(phys_to_other)
        external_advance(trx, 0)
        self.assertEqual(0, trx.sigma)
        internal_advance(trx)
        self.assertEqual(inf, trx.sigma)
        self.assertEqual(1, len(trx.output_net_to_node))
        self.assertEqual(phys_to_core.data, trx.output_net_to_node.get())
        self.assertEqual(1, len(trx.output_net_to_other))
        self.assertEqual(phys_to_other.data, trx.output_net_to_other.get())

        net_to_client = DummyAppPacket.create_net_msg('node', 'client', 0)
        net_to_other = DummyAppPacket.create_net_msg('node', 'other', 0)
        trx.input_net.add(net_to_client)
        trx.input_net.add(net_to_other)
        external_advance(trx, 0)
        self.assertEqual(0, trx.sigma)
        internal_advance(trx)
        self.assertEqual(inf, trx.sigma)
        self.assertEqual(2, len(trx.output_phys))
        hit = 0
        for msg in trx.output_phys.values:
            if msg.data == net_to_client:
                hit += 1
                self.assertEqual('gateway', msg.node_to)
                self.assertEqual('client', msg.data.node_to)
            elif msg.data == net_to_other:
                hit += 1
                self.assertEqual('other', msg.node_to)
                self.assertEqual('other', msg.data.node_to)
        self.assertEqual(2, hit)


if __name__ == '__main__':
    unittest.main()
