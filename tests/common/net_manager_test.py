import math
import unittest
from mercury.config.packet import PacketConfig
from mercury.msg.packet import AppPacket, NetworkPacket
from mercury.model.common import NetworkManager


class ClientDummyApp(AppPacket):
    def __init__(self, packet_id: int, t_gen: float):
        super().__init__("manager", "node_to", 0, 0, t_gen)
        self.packet_id = packet_id


class NetworkDummyApp(AppPacket):
    def __init__(self, packet_id: int, t_gen: float):
        super().__init__("node_to", "manager", 0, 0, t_gen)
        self.packet_id = packet_id


class NetworkManagerTest(unittest.TestCase):
    def test_basic(self):
        PacketConfig.LOG_NETWORK_REPORT = False
        clock = 0
        manager = NetworkManager('manager', 'test', True)
        manager.initialize()
        self.assertFalse(manager.awaiting_ack)
        self.assertEqual(manager.sigma, math.inf)

        clock += 1
        msg = ClientDummyApp(1, clock)
        msg.send(clock)
        manager.input_app.add(msg)

        manager.deltext(1)
        self.assertEqual(manager.sigma, 0)
        self.assertEqual(len(manager.awaiting_ack), 1)
        for msg in manager.awaiting_ack:
            self.assertFalse(msg.ack)
            self.assertEqual(msg.timeout, clock + PacketConfig.SESSION_TIMEOUT)
        self.assertEqual(len(manager._message_queue), 1)
        for port in manager.in_ports:
            port.clear()

        manager.lambdaf()
        self.assertEqual(len(manager.output_net), 1)
        tcp_msgs = list(manager.output_net.values)
        for msg in tcp_msgs:
            msg.receive(clock)
            msg.data.receive(clock)
        tcp_req = [msg for msg in tcp_msgs]
        for port in manager.out_ports:
            port.clear()
        manager.deltint()
        self.assertEqual(manager.sigma, 1)

        clock += 1
        manager.lambdaf()
        self.assertEqual(len(manager.output_net), 0)
        manager.deltint()
        self.assertEqual(manager.sigma, 0)
        manager.lambdaf()
        self.assertEqual(len(manager.output_net), 1)
        manager.deltint()
        self.assertEqual(manager.sigma, 1)
        for port in manager.out_ports:
            port.clear()

        clock += 0.5
        for req in tcp_req:
            ack = NetworkPacket(req, req.node_to)
            manager.input_net.add(ack)
        manager.deltext(0.5)
        for port in manager.in_ports:
            port.clear()
        self.assertEqual(manager.sigma, math.inf)

        b = NetworkDummyApp(2, clock)
        b.send(clock)

        net_tcp_msg = NetworkPacket(b, b.node_from)
        manager.input_net.add(net_tcp_msg)

        clock += 0.5
        manager.deltext(0.5)
        self.assertEqual(manager.sigma, 0)
        self.assertFalse(manager.awaiting_ack)
        for msg in manager.awaiting_ack:
            self.assertFalse(msg.ack)
            self.assertEqual(msg.timeout, clock + 1)
        self.assertEqual(len(manager._message_queue), 2)
        for port in manager.in_ports:
            port.clear()

        manager.lambdaf()
        self.assertEqual(len(manager.output_net), 1)
        self.assertEqual(len(manager.output_app), 1)
        self.assertFalse(manager.awaiting_ack)
        for port in manager.out_ports:
            port.clear()
        manager.deltint()
        self.assertEqual(manager.sigma, math.inf)
        self.assertFalse(manager.awaiting_ack)

        manager.input_net.add(net_tcp_msg)
        clock += 0.5
        manager.deltext(0.5)
        self.assertEqual(manager.sigma, 0)
        self.assertFalse(manager.awaiting_ack)
        self.assertEqual(len(manager._message_queue), 1)
        for port in manager.in_ports:
            port.clear()

        manager.lambdaf()
        self.assertEqual(len(manager.output_net), 1)
        self.assertFalse(manager.awaiting_ack)
        for port in manager.out_ports:
            port.clear()
        manager.deltint()
        self.assertEqual(manager.sigma, math.inf)
        self.assertFalse(manager.awaiting_ack)

    def test_enable(self):
        PacketConfig.LOG_NETWORK_REPORT = False
        clock = 0
        manager = NetworkManager('manager', 'test', False)
        manager.initialize()
        self.assertFalse(manager.enabled)
        self.assertFalse(manager.awaiting_ack)
        self.assertEqual(manager.sigma, math.inf)

        clock += 1
        msg = ClientDummyApp(1, clock)
        msg.send(clock)
        manager.input_app.add(msg)

        manager.deltext(1)
        self.assertEqual(manager.sigma, math.inf)
        self.assertEqual(len(manager.msg_queue), 1)
        self.assertEqual(len(manager.awaiting_ack), 0)
        self.assertEqual(len(manager._message_queue), 0)
        for port in manager.in_ports:
            port.clear()

        # We send messages again -> nothing should change
        msg.send(clock)
        manager.input_app.add(msg)
        manager.deltext(1)
        self.assertEqual(manager.sigma, math.inf)
        self.assertEqual(len(manager.msg_queue), 1)
        self.assertEqual(len(manager.awaiting_ack), 0)
        self.assertEqual(len(manager._message_queue), 0)
        for port in manager.in_ports:
            port.clear()

        manager.input_ctrl.add(True)
        manager.deltext(1)
        self.assertEqual(manager.sigma, 0)
        self.assertEqual(len(manager.msg_queue), 0)
        self.assertEqual(len(manager.awaiting_ack), 1)
        self.assertEqual(len(manager._message_queue), 1)
        for port in manager.in_ports:
            port.clear()

        manager.lambdaf()
        self.assertEqual(len(manager.output_net), 1)
        tcp_msgs = list(manager.output_net.values)
        for msg in tcp_msgs:
            msg.receive(clock)
            msg.data.receive(clock)
        tcp_req = [msg for msg in tcp_msgs]
        for port in manager.out_ports:
            port.clear()
        manager.deltint()
        self.assertEqual(manager.sigma, 1)

        clock += 1
        manager.lambdaf()
        self.assertEqual(len(manager.output_net), 0)
        manager.deltint()
        self.assertEqual(manager.sigma, 0)
        manager.lambdaf()
        self.assertEqual(len(manager.output_net), 1)
        manager.deltint()
        self.assertEqual(manager.sigma, 1)
        for port in manager.out_ports:
            port.clear()

        clock += 0.5
        for msg in tcp_req:
            manager.input_net.add(NetworkPacket(msg, msg.node_from))
        manager.deltext(0.5)
        for port in manager.in_ports:
            port.clear()
        self.assertEqual(manager.sigma, math.inf)

        b = NetworkDummyApp(2, clock)
        b.send(clock)

        net_tcp_msg = NetworkPacket(b, b.node_from)
        manager.input_net.add(net_tcp_msg)

        clock += 0.5
        manager.deltext(0.5)
        self.assertEqual(manager.sigma, 0)
        self.assertFalse(manager.awaiting_ack)
        for msg in manager.awaiting_ack:
            self.assertFalse(msg.ack)
            self.assertEqual(msg.timeout, clock + 1)
        self.assertEqual(len(manager._message_queue), 2)
        for port in manager.in_ports:
            port.clear()

        manager.lambdaf()
        self.assertEqual(len(manager.output_net), 1)
        self.assertEqual(len(manager.output_app), 1)
        self.assertFalse(manager.awaiting_ack)
        for port in manager.out_ports:
            port.clear()
        manager.deltint()
        self.assertEqual(manager.sigma, math.inf)
        self.assertFalse(manager.awaiting_ack)

        manager.input_net.add(net_tcp_msg)
        clock += 0.5
        manager.deltext(0.5)
        self.assertEqual(manager.sigma, 0)
        self.assertFalse(manager.awaiting_ack)
        self.assertEqual(len(manager._message_queue), 1)
        for port in manager.in_ports:
            port.clear()

        manager.lambdaf()
        self.assertEqual(len(manager.output_net), 1)
        self.assertFalse(manager.awaiting_ack)
        for port in manager.out_ports:
            port.clear()
        manager.deltint()
        self.assertEqual(manager.sigma, math.inf)
        self.assertFalse(manager.awaiting_ack)


if __name__ == '__main__':
    unittest.main()
