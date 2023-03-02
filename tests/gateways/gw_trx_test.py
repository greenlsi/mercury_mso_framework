import unittest
from math import inf
from mercury.model.gateways.gw_trx import *
from mercury.msg.packet import AppPacket
from mercury.msg.packet.app_packet.acc_packet import PSSMessage
from xdevs.models import Atomic


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


class DummyAppPacket(AppPacket):
    def __init__(self, node_from: str, node_to: str, t_gen: float):
        super().__init__(node_from, node_to, 0, 0, t_gen)

    @staticmethod
    def phys_msg(node_from: str, node_to: str, t_gen: float) -> PhysicalPacket:
        app_msg = DummyAppPacket(node_from, node_to, t_gen)
        app_msg.send(t_gen)
        net_msg = NetworkPacket(app_msg, app_msg.node_from)
        net_msg.send(t_gen)
        phys_msg = CrosshaulPacket(node_from, node_to, net_msg)
        phys_msg.send(t_gen)
        return phys_msg

    @staticmethod
    def net_msg(node_from: str, node_to: str, t_gen: float) -> NetworkPacket:
        app_msg = DummyAppPacket(node_from, node_to, t_gen)
        app_msg.send(t_gen)
        net_msg = NetworkPacket(app_msg, node_from)
        net_msg.send(t_gen)
        return net_msg


class GatewayTransceiversTest(unittest.TestCase):
    def test_xh_trx(self):
        gateway_id: str = 'gateway'
        other_id: str = 'other'
        trx = CrosshaulTransceiver(gateway_id)
        trx.initialize()
        self.assertEqual(inf, trx.sigma)

        phys_to_other = DummyAppPacket.phys_msg(other_id, other_id, 0)
        phys_to_gw = DummyAppPacket.phys_msg(other_id, gateway_id, 0)
        net_to_other = DummyAppPacket.net_msg(other_id, gateway_id, 0)
        trx.input_phys.add(phys_to_other)
        trx.input_phys.add(phys_to_gw)
        trx.input_net.add(net_to_other)
        external_advance(trx, 1)
        self.assertEqual(0, trx.sigma)
        internal_advance(trx)
        self.assertEqual(inf, trx.sigma)
        self.assertEqual(phys_to_other.data, trx.output_net_to_acc.get())
        self.assertEqual(1, phys_to_other.t_rcv[-1])
        self.assertEqual(phys_to_gw.data, trx.output_net.get())
        self.assertEqual(1, phys_to_gw.t_rcv[-1])
        self.assertEqual(net_to_other, trx.output_phys.get().data)
        self.assertEqual(net_to_other.t_sent[-1], trx.output_phys.get().t_sent[-1])

    def test_acc_trx(self):
        gateway_id: str = 'gateway'
        other_id: str = 'other'
        trx = AccessTransceiver(gateway_id, True)
        trx.initialize()
        self.assertEqual(inf, trx.sigma)

        phys_acc = DummyAppPacket.phys_msg(other_id, gateway_id, 0)
        phys_srv = DummyAppPacket.phys_msg(other_id, gateway_id, 0)
        phys_srv_to_other = DummyAppPacket.phys_msg(other_id, other_id, 0)
        app_acc = PSSMessage('gw', other_id, 0)
        app_acc.send(0)
        net_acc = NetworkPacket(app_acc, app_acc.node_from)
        net_acc.send(0)
        net_srv = DummyAppPacket.net_msg(other_id, gateway_id, 0)
        trx.input_phys.add(phys_acc)
        trx.input_phys.add(phys_srv)
        trx.input_phys.add(phys_srv_to_other)
        trx.input_net.add(net_acc)
        trx.input_net.add(net_srv)
        external_advance(trx, 1)
        self.assertEqual(0, trx.sigma)
        internal_advance(trx)
        self.assertEqual(inf, trx.sigma)
        n_hits = 0
        for msg in trx.output_net.values:
            if msg in [phys_acc.data, phys_srv.data]:
                n_hits += 1
        self.assertEqual(2, n_hits)
        self.assertEqual(1, phys_acc.t_rcv[-1])
        self.assertEqual(1, phys_srv.t_rcv[-1])
        self.assertEqual(phys_srv_to_other.data, trx.output_net_to_xh.get())
        self.assertEqual(1, phys_srv_to_other.t_rcv[-1])
        self.assertEqual(net_acc, trx.output_phys_acc.get().data)
        self.assertEqual(net_acc.t_sent[-1], trx.output_phys_acc.get().t_sent[-1])
        self.assertEqual(net_srv, trx.output_phys_srv.get().data)
        self.assertEqual(net_srv.t_sent[-1], trx.output_phys_srv.get().t_sent[-1])


if __name__ == '__main__':
    unittest.main()
