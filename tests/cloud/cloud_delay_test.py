from __future__ import annotations
import unittest
from math import inf
from mercury.config.cloud import CloudConfig
from mercury.model.cloud.network_delay import CloudNetworkDelay
from mercury.msg.packet import PhysicalPacket, NetworkPacket, AppPacket
from mercury.msg.packet.phys_packet import CrosshaulPacket


class DummyAppPacket(AppPacket):
    def __init__(self, node_from: str, node_to: str | None, t_gen: float):
        super().__init__(node_from, node_to, 0, 0, t_gen)
        self.send(t_gen)

    @staticmethod
    def create_net_msg(node_from: str, node_to: str | None, t_gen: float) -> NetworkPacket:
        app_msg = DummyAppPacket(node_from, node_to, t_gen)
        net_msg = NetworkPacket(app_msg, app_msg.node_from)
        net_msg.send(t_gen)
        return net_msg

    @staticmethod
    def create_phys_msg(node_from: str, node_to: str | None, t_gen: float) -> PhysicalPacket:
        net_msg = DummyAppPacket.create_net_msg(node_from, node_to, t_gen)
        phys_msg = CrosshaulPacket(node_from, node_to, net_msg)
        phys_msg.send(t_gen)
        return phys_msg


def internal_advance(model: CloudNetworkDelay):
    for port in model.out_ports:
        port.clear()
    model.lambdaf()
    model.deltint()


def external_advance(model: CloudNetworkDelay, e: float):
    for port in model.out_ports:
        port.clear()
    model.deltext(e)
    for port in model.in_ports:
        port.clear()


class CloudDelayTestCase(unittest.TestCase):
    def test_physical(self):
        cloud_id: str = 'cloud'
        prop_delay: float = 1.
        cloud_config: CloudConfig = CloudConfig(cloud_id, delay_id='constant', delay_config={'prop_delay': prop_delay})
        cloud_delay: CloudNetworkDelay = CloudNetworkDelay(PhysicalPacket, cloud_config)
        cloud_delay.initialize()
        self.assertEqual(inf, cloud_delay.sigma)

        msg_1 = DummyAppPacket.create_phys_msg('client', 'cloud', 0)
        cloud_delay.input_data.add(msg_1)
        external_advance(cloud_delay, 0)
        self.assertEqual(prop_delay, cloud_delay.sigma)
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertTrue(cloud_delay._clock + prop_delay in cloud_delay.msg_buffer)
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        msg_2 = DummyAppPacket.create_phys_msg('cloud', 'client', 0)
        cloud_delay.input_data.add(msg_2)
        external_advance(cloud_delay, 0)
        self.assertEqual(prop_delay, cloud_delay.sigma)
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertEqual(2, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay]))
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])
        self.assertTrue(msg_2 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        msg_3 = DummyAppPacket.create_phys_msg('client', 'cloud', 0)
        cloud_delay.input_data.add(msg_3)
        external_advance(cloud_delay, prop_delay / 2)
        self.assertEqual(2, len(cloud_delay.msg_buffer))
        self.assertEqual(prop_delay / 2, cloud_delay.sigma)
        self.assertEqual(2, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2]))
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])
        self.assertTrue(msg_2 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])
        self.assertEqual(1, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay]))
        self.assertTrue(msg_3 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        internal_advance(cloud_delay)
        self.assertEqual(1, len(cloud_delay.output_to_cloud))
        self.assertEqual(msg_1, cloud_delay.output_to_cloud.get())
        self.assertEqual(1, len(cloud_delay.output_to_others))
        self.assertEqual(msg_2, cloud_delay.output_to_others.get())
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertEqual(1, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2]))
        self.assertTrue(msg_3 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])

        internal_advance(cloud_delay)
        self.assertEqual(1, len(cloud_delay.output_to_cloud))
        self.assertEqual(msg_3, cloud_delay.output_to_cloud.get())
        self.assertEqual(0, len(cloud_delay.output_to_others))
        self.assertFalse(cloud_delay.msg_buffer)

    def test_physical_loss(self):
        cloud_id: str = 'cloud'
        prop_delay: float = 1.
        cloud_config: CloudConfig = CloudConfig(cloud_id, delay_id='constant', delay_config={'prop_delay': prop_delay, 'loss_p':1})
        cloud_delay: CloudNetworkDelay = CloudNetworkDelay(PhysicalPacket, cloud_config)
        cloud_delay.initialize()
        self.assertEqual(inf, cloud_delay.sigma)

        msg_1 = DummyAppPacket.create_phys_msg('client', 'cloud', 0)
        cloud_delay.input_data.add(msg_1)
        external_advance(cloud_delay, 0)
        self.assertEqual(inf, cloud_delay.sigma)
        self.assertFalse(cloud_delay.msg_buffer)

    def test_network(self):
        cloud_id: str = 'cloud'
        prop_delay: float = 1.
        cloud_config: CloudConfig = CloudConfig(cloud_id, delay_id='constant', delay_config={'prop_delay': prop_delay})
        cloud_delay: CloudNetworkDelay = CloudNetworkDelay(NetworkPacket, cloud_config)
        cloud_delay.initialize()
        self.assertEqual(inf, cloud_delay.sigma)

        msg_1 = DummyAppPacket.create_net_msg('client', 'cloud', 0)
        cloud_delay.input_data.add(msg_1)
        external_advance(cloud_delay, 0)
        self.assertEqual(prop_delay, cloud_delay.sigma)
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertTrue(cloud_delay._clock + prop_delay in cloud_delay.msg_buffer)
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        msg_2 = DummyAppPacket.create_net_msg('cloud', 'client', 0)
        cloud_delay.input_data.add(msg_2)
        external_advance(cloud_delay, 0)
        self.assertEqual(prop_delay, cloud_delay.sigma)
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertEqual(2, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay]))
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])
        self.assertTrue(msg_2 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        msg_3 = DummyAppPacket.create_net_msg('client', 'cloud', 0)
        cloud_delay.input_data.add(msg_3)
        external_advance(cloud_delay, prop_delay / 2)
        self.assertEqual(2, len(cloud_delay.msg_buffer))
        self.assertEqual(prop_delay / 2, cloud_delay.sigma)
        self.assertEqual(2, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2]))
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])
        self.assertTrue(msg_2 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])
        self.assertEqual(1, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay]))
        self.assertTrue(msg_3 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        internal_advance(cloud_delay)
        self.assertEqual(1, len(cloud_delay.output_to_cloud))
        self.assertEqual(msg_1, cloud_delay.output_to_cloud.get())
        self.assertEqual(1, len(cloud_delay.output_to_others))
        self.assertEqual(msg_2, cloud_delay.output_to_others.get())
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertEqual(1, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2]))
        self.assertTrue(msg_3 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])

        internal_advance(cloud_delay)
        self.assertEqual(1, len(cloud_delay.output_to_cloud))
        self.assertEqual(msg_3, cloud_delay.output_to_cloud.get())
        self.assertEqual(0, len(cloud_delay.output_to_others))
        self.assertFalse(cloud_delay.msg_buffer)

    def test_network_loss(self):
        cloud_id: str = 'cloud'
        prop_delay: float = 1.
        cloud_config: CloudConfig = CloudConfig(cloud_id, delay_id='constant', delay_config={'prop_delay': prop_delay, 'loss_p':1})
        cloud_delay: CloudNetworkDelay = CloudNetworkDelay(NetworkPacket, cloud_config)
        cloud_delay.initialize()
        self.assertEqual(inf, cloud_delay.sigma)

        msg_1 = DummyAppPacket.create_net_msg('client', 'cloud', 0)
        cloud_delay.input_data.add(msg_1)
        external_advance(cloud_delay, 0)
        self.assertEqual(inf, cloud_delay.sigma)
        self.assertFalse(cloud_delay.msg_buffer)

    def test_app(self):
        cloud_id: str = 'cloud'
        prop_delay: float = 1.
        cloud_config: CloudConfig = CloudConfig(cloud_id, delay_id='constant', delay_config={'prop_delay': prop_delay})
        cloud_delay: CloudNetworkDelay = CloudNetworkDelay(AppPacket, cloud_config)
        cloud_delay.initialize()
        self.assertEqual(inf, cloud_delay.sigma)

        msg_1 = DummyAppPacket('client', 'cloud', 0)
        cloud_delay.input_data.add(msg_1)
        external_advance(cloud_delay, 0)
        self.assertEqual(prop_delay, cloud_delay.sigma)
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertTrue(cloud_delay._clock + prop_delay in cloud_delay.msg_buffer)
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        msg_2 = DummyAppPacket('cloud', 'client', 0)
        cloud_delay.input_data.add(msg_2)
        external_advance(cloud_delay, 0)
        self.assertEqual(prop_delay, cloud_delay.sigma)
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertEqual(2, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay]))
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])
        self.assertTrue(msg_2 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        msg_3 = DummyAppPacket('client', 'cloud', 0)
        cloud_delay.input_data.add(msg_3)
        external_advance(cloud_delay, prop_delay / 2)
        self.assertEqual(2, len(cloud_delay.msg_buffer))
        self.assertEqual(prop_delay / 2, cloud_delay.sigma)
        self.assertEqual(2, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2]))
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])
        self.assertTrue(msg_2 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])
        self.assertEqual(1, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay]))
        self.assertTrue(msg_3 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        internal_advance(cloud_delay)
        self.assertEqual(1, len(cloud_delay.output_to_cloud))
        self.assertEqual(msg_1, cloud_delay.output_to_cloud.get())
        self.assertEqual(1, len(cloud_delay.output_to_others))
        self.assertEqual(msg_2, cloud_delay.output_to_others.get())
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertEqual(1, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2]))
        self.assertTrue(msg_3 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])

        internal_advance(cloud_delay)
        self.assertEqual(1, len(cloud_delay.output_to_cloud))
        self.assertEqual(msg_3, cloud_delay.output_to_cloud.get())
        self.assertEqual(0, len(cloud_delay.output_to_others))
        self.assertFalse(cloud_delay.msg_buffer)

    def test_app_loss(self):
        cloud_id: str = 'cloud'
        prop_delay: float = 1.
        cloud_config: CloudConfig = CloudConfig(cloud_id, delay_id='constant', delay_config={'prop_delay': prop_delay, 'loss_p':1})
        cloud_delay: CloudNetworkDelay = CloudNetworkDelay(AppPacket, cloud_config)
        cloud_delay.initialize()
        self.assertEqual(inf, cloud_delay.sigma)

        msg_1 = DummyAppPacket('client', 'cloud', 0)
        cloud_delay.input_data.add(msg_1)
        external_advance(cloud_delay, 0)
        self.assertEqual(prop_delay, cloud_delay.sigma)
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertTrue(cloud_delay._clock + prop_delay in cloud_delay.msg_buffer)
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        msg_2 = DummyAppPacket('cloud', 'client', 0)
        cloud_delay.input_data.add(msg_2)
        external_advance(cloud_delay, 0)
        self.assertEqual(prop_delay, cloud_delay.sigma)
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertEqual(2, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay]))
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])
        self.assertTrue(msg_2 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        msg_3 = DummyAppPacket('client', 'cloud', 0)
        cloud_delay.input_data.add(msg_3)
        external_advance(cloud_delay, prop_delay / 2)
        self.assertEqual(2, len(cloud_delay.msg_buffer))
        self.assertEqual(prop_delay / 2, cloud_delay.sigma)
        self.assertEqual(2, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2]))
        self.assertTrue(msg_1 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])
        self.assertTrue(msg_2 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])
        self.assertEqual(1, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay]))
        self.assertTrue(msg_3 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay])

        internal_advance(cloud_delay)
        self.assertEqual(1, len(cloud_delay.output_to_cloud))
        self.assertEqual(msg_1, cloud_delay.output_to_cloud.get())
        self.assertEqual(1, len(cloud_delay.output_to_others))
        self.assertEqual(msg_2, cloud_delay.output_to_others.get())
        self.assertEqual(1, len(cloud_delay.msg_buffer))
        self.assertEqual(1, len(cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2]))
        self.assertTrue(msg_3 in cloud_delay.msg_buffer[cloud_delay._clock + prop_delay * 1 / 2])

        internal_advance(cloud_delay)
        self.assertEqual(1, len(cloud_delay.output_to_cloud))
        self.assertEqual(msg_3, cloud_delay.output_to_cloud.get())
        self.assertEqual(0, len(cloud_delay.output_to_others))
        self.assertFalse(cloud_delay.msg_buffer)


if __name__ == '__main__':
    unittest.main()
