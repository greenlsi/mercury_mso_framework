import unittest
from math import inf
import mercury.logger as logger
from mercury.model.network.mobility import MobilityManager, WirelessNodeConfig
from typing import Any, Dict
from xdevs.models import Atomic


logger.set_logger_level('INFO')
logger.add_stream_handler()


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


def confluent_advance(model: Atomic, e: float):
    for port in model.out_ports:
        port.clear()
    model.lambdaf()
    model.deltcon(e)
    for port in model.in_ports:
        port.clear()


class MobilityManagerTestCase(unittest.TestCase):
    def test_manager(self):
        mob_id: str = '2D_function'
        mob_config: Dict[str, Any] = {
            'function': lambda x: 0,
            'interval': (0, 100),
            'delta': 10,
            'sigma': 5,
        }
        clients = [
            WirelessNodeConfig('client_1', 0, 10, mob_id, mob_config),
            WirelessNodeConfig('client_2', 10, 20, mob_id, mob_config),
            WirelessNodeConfig('client_3', 15, 30, mob_id, mob_config),
            WirelessNodeConfig('client_4', 20, 40, mob_id, mob_config),
        ]

        manager: MobilityManager = MobilityManager()
        manager.initialize()
        self.assertFalse(manager.wireless_nodes)
        self.assertEqual(inf, manager.sigma)
        # t = 0
        manager.input_create_node.add(clients[0])
        external_advance(manager, 0)
        self.assertEqual(1, len(manager.wireless_nodes))
        self.assertTrue('client_1' in manager.wireless_nodes)
        self.assertEqual(0, manager.sigma)
        internal_advance(manager)
        self.assertEqual(1, len(manager.output_new_location))
        location = manager.output_new_location.get()
        self.assertEqual('client_1', location.node_id)
        self.assertEqual((0, 0), location.location)
        self.assertEqual(5, manager.sigma)
        # t = 5
        internal_advance(manager)
        self.assertEqual(1, len(manager.output_new_location))
        location = manager.output_new_location.get()
        self.assertEqual('client_1', location.node_id)
        self.assertEqual((10, 0), location.location)
        self.assertEqual(inf, manager.sigma)  # client_1 is waiting to be removed
        # t = 10
        manager.input_create_node.add(clients[1])
        manager.input_remove_node.add('client_1')
        external_advance(manager, 5)
        self.assertEqual(0, manager.sigma)
        internal_advance(manager)
        self.assertEqual(1, len(manager.output_new_location))
        location = manager.output_new_location.get()
        self.assertEqual('client_2', location.node_id)
        self.assertEqual((0, 0), location.location)
        self.assertEqual(5, manager.sigma)
        # t = 15
        manager.input_create_node.add(clients[2])
        confluent_advance(manager, 5)
        self.assertEqual(1, len(manager.output_new_location))
        location = manager.output_new_location.get()
        self.assertEqual('client_2', location.node_id)
        self.assertEqual((10, 0), location.location)
        self.assertEqual(0, manager.sigma)
        internal_advance(manager)
        self.assertEqual(1, len(manager.output_new_location))
        location = manager.output_new_location.get()
        self.assertEqual('client_3', location.node_id)
        self.assertEqual((0, 0), location.location)
        self.assertEqual(5, manager.sigma)
        # t = 20
        manager.input_create_node.add(clients[3])
        manager.input_remove_node.add('client_2')
        confluent_advance(manager, 5)
        self.assertEqual(1, len(manager.output_new_location))
        location = manager.output_new_location.get()
        self.assertEqual('client_3', location.node_id)
        self.assertEqual((10, 0), location.location)
        self.assertEqual(0, manager.sigma)
        internal_advance(manager)
        self.assertEqual(1, len(manager.output_new_location))
        location = manager.output_new_location.get()
        self.assertEqual('client_4', location.node_id)
        self.assertEqual((0, 0), location.location)
        self.assertEqual(5, manager.sigma)
        # t = 25
        internal_advance(manager)
        self.assertEqual(2, len(manager.output_new_location))
        self.assertEqual(5, manager.sigma)
        # t = 30
        manager.input_remove_node.add('client_3')
        confluent_advance(manager, 5)
        self.assertEqual(1, len(manager.output_new_location))
        location = manager.output_new_location.get()
        self.assertEqual('client_4', location.node_id)
        self.assertEqual((20, 0), location.location)
        self.assertEqual(5, manager.sigma)
        # t = 35
        internal_advance(manager)
        self.assertEqual(1, len(manager.output_new_location))
        location = manager.output_new_location.get()
        self.assertEqual('client_4', location.node_id)
        self.assertEqual((30, 0), location.location)
        self.assertEqual(inf, manager.sigma)
        # t = 40
        manager.input_remove_node.add('client_4')
        external_advance(manager, 5)
        self.assertFalse(manager.wireless_nodes)
        self.assertEqual(inf, manager.sigma)


if __name__ == '__main__':
    unittest.main()
