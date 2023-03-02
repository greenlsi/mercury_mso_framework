from __future__ import annotations
import unittest
import mercury.logger as logger
from mercury.model.clients import Clients, ClientsShortcut, ClientsLite
from mercury.config.client import ClientsConfig
from mercury.config.gateway import GatewaysConfig
from mercury.msg.packet.net_packet import NetworkPacket
from mercury.msg.packet.phys_packet import RadioPacket
from mercury.msg.packet.app_packet.acc_packet import *
from mercury.msg.packet.app_packet.srv_packet import *
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


clients_config: ClientsConfig | None = None


class ClientsTestCase(unittest.TestCase):
    @staticmethod
    def prepare_scenario():
        global clients_config
        if clients_config is None:
            packaging_time = 2
            PacketConfig.SESSION_TIMEOUT = 2
            GatewaysConfig.PSS_WINDOW = 2  # so window is equal to packaging_time
            ServicesConfig.add_service('service_1', 10, 'single', {}, 'constant',
                                       {'length': inf}, 'periodic', {'period': packaging_time})

            clients_config = ClientsConfig()
            clients_config.add_client_generator('list', {
                'services': {'service_1'},
                'clients': {
                    'client_1': {
                        't_start': 0,
                        't_end': inf,
                        'gateway': 'OLT',
                        'location': (0, 0),
                    },
                    'client_2': {
                        't_start': 0,
                        't_end': 6,
                        'mob_config': {
                            'location': (0, 0),
                        }
                    },
                    'client_3': {
                        't_start': 4,
                        't_end': inf,
                        'mob_config': {
                            'location': (0, 0),
                        }
                    },
                    'client_4': {
                        't_start': 6,
                        't_end': 10,
                        'mob_config': {
                            'location': (0, 0),
                        }
                    }
                },
            })

    def test_client(self):
        self.prepare_scenario()
        clients = Clients(clients_config)
        clients.initialize()
        # Check initial status
        self.assertEqual(clients.sigma, 0)
        self.assertEqual(len(clients.events), 3)

        internal_advance(clients)
        self.assertEqual(len(clients.events), 2)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)
        self.assertEqual(len(clients.clients), 2)
        self.assertTrue('client_1' in clients.clients)
        self.assertTrue('client_2' in clients.clients)

        conn_reqs: dict[str, ConnectRequest] = dict()

        internal_advance(clients)
        self.assertEqual(len(clients.events), 2)
        self.assertEqual(len(list(clients.output_create_client.values)), 2)
        clients.output_create_client.clear()
        self.assertEqual(len(list(clients.output_phys_wired.values)), 1)
        phys_packet = clients.output_phys_wired.get()
        self.assertEqual('client_1', phys_packet.node_from)
        self.assertEqual('OLT', phys_packet.node_to)
        self.assertIsInstance(phys_packet.data.data, ConnectRequest)
        conn_reqs['client_1'] = phys_packet.data.data
        clients.output_phys_wired.clear()
        self.assertEqual(len(list(clients.output_send_pss.values)), 1)
        self.assertEqual('client_2', clients.output_send_pss.get().client_id)
        clients.output_send_pss.clear()
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, min(GatewaysConfig.PSS_WINDOW, PacketConfig.SESSION_TIMEOUT))

        # We introduce deceptive PSS messages
        for client_id in ('client_1', 'client_2', 'client_3', 'client_4'):
            app_msg = PSSMessage('AP', client_id, clients._clock)
            app_msg.send(clients._clock)
            net_msg = NetworkPacket(app_msg, 'AP')
            net_msg.send(clients._clock)
            phys_packet = RadioPacket('AP', client_id, net_msg, True)
            phys_packet.send(clients._clock)
            clients.input_phys.add(phys_packet)
        external_advance(clients, 0)
        self.assertEqual(clients.sigma, 0)
        self.assertEqual(2, len(clients._message_queue))  # Two ACKs for the two alive clients
        internal_advance(clients)
        self.assertEqual(1, len(list(clients.output_phys_wired.values)))
        self.assertIsInstance(clients.output_phys_wired.get().data.data, NetworkPacket)
        self.assertEqual(1, len(list(clients.output_phys_wireless_acc.values)))
        self.assertIsInstance(clients.output_phys_wireless_acc.get().data.data, NetworkPacket)
        self.assertEqual(clients.sigma, 2)

        internal_advance(clients)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)
        internal_advance(clients)
        self.assertEqual(1, len(list(clients.output_phys_wired.values)))  # Two connection requests
        self.assertEqual(1, len(list(clients.output_phys_wireless_acc.values)))  # Two connection requests
        for port in (clients.output_phys_wired, clients.output_phys_wireless_acc):
            for phy_msg in port.values:
                if isinstance(phy_msg.data.data, ConnectRequest):
                    conn_reqs[phy_msg.data.data.node_from] = phy_msg.data.data
                    phy_msg.data.receive(clients._clock)
                    net_ack = NetworkPacket(phy_msg.data, phy_msg.node_to)
                    net_ack.send(clients._clock)
                    net_ack.data.ack = None  # little trap to avoid stuff
                    phys_ack = RadioPacket(net_ack.node_from, net_ack.node_to, net_ack, True)
                    phys_ack.send(clients._clock)
                    clients.input_phys.add(phys_ack)
            port.clear()
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 2)

        # A new client must be created. Already created UEs should try to connect again
        internal_advance(clients)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(0, clients.sigma)
        internal_advance(clients)
        self.assertEqual(1, len(list(clients.output_create_client.values)))  # One new client
        self.assertEqual(1, len(list(clients.output_send_pss.values)))
        self.assertEqual('client_3', clients.output_send_pss.get().client_id)
        self.assertEqual(1, len(list(clients.output_phys_wired.values)))  # Two connection requests
        self.assertEqual(1, len(list(clients.output_phys_wireless_acc.values)))  # Two connection requests
        clients.output_create_client.clear()
        clients.output_send_pss.clear()
        clients.output_phys_wired.clear()
        clients.output_phys_wireless_acc.clear()
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 2)

        # UEs receive connection response
        for client_id, conn_req in conn_reqs.items():
            app_msg = ConnectResponse(conn_req, True, clients._clock)
            app_msg.send(clients._clock)
            net_msg = NetworkPacket(app_msg, app_msg.node_from)
            net_msg.send(clients._clock)
            phys_packet = RadioPacket(app_msg.node_from, client_id, net_msg, True)
            phys_packet.send(clients._clock)
            clients.input_phys.add(phys_packet)
        external_advance(clients, 0)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)  # Messages in queue
        internal_advance(clients)
        self.assertEqual(len(clients.output_phys_wireless_acc), 1)  # RRC messages
        self.assertEqual(len(clients.output_phys_wired), 2)  # RRC messages, service request
        self.assertEqual(len(clients.output_phys_wireless_srv), 1)  # Service requests
        self.assertEqual(clients.sigma, 2)

        for _ in range(2):
            for port in (clients.output_phys_wired, clients.output_phys_wireless_acc, clients.output_phys_wireless_srv):
                for phy_msg in port.values:
                    phy_msg.data.receive(clients._clock)
                    net_ack = NetworkPacket(phy_msg.data, phy_msg.node_from)
                    net_ack.send(clients._clock)
                    phys_ack = RadioPacket(net_ack.node_from, net_ack.node_to, net_ack, True)
                    phys_ack.send(clients._clock)
                    clients.input_phys.add(phys_ack)
                    if isinstance(phy_msg.data.data, SrvRequest):
                        phy_msg.data.data.receive(clients._clock)
                        app_msg = SrvResponse(phy_msg.data.data, True, clients._clock)
                        app_msg.send(clients._clock)
                        net_msg = NetworkPacket(app_msg, app_msg.node_from)
                        net_msg.send(clients._clock)
                        phys_packet = RadioPacket(app_msg.node_from, app_msg.node_to, net_msg, True)
                        phys_packet.send(clients._clock)
                        clients.input_phys.add(phys_packet)
            external_advance(clients, 0)
            for out_port in clients.out_ports:
                self.assertTrue(out_port.empty())
            self.assertEqual(clients.sigma, 0)  # Messages in queue
            internal_advance(clients)
            self.assertEqual(2, len(clients.output_srv_report))  # service reports
            clients.output_srv_report.clear()
            self.assertEqual(2, len(clients.output_phys_wired))  # 2, acks, 2 new service requests
            self.assertEqual(2, len(clients.output_phys_wireless_srv))  # 2, acks, 2 new service requests
            self.assertEqual(clients.sigma, 2)
        internal_advance(clients)
        self.assertEqual(0, clients.sigma)  # messages in queue
        internal_advance(clients)
        self.assertEqual(1, len(list(clients.output_create_client.values)))  # client 4 is created at t = 6
        self.assertEqual(0, len(list(clients.output_remove_client.values)))
        self.assertEqual(1, len(list(clients.output_phys_wireless_srv.values)))       # 2 new service requests
        self.assertEqual(1, len(list(clients.output_phys_wired.values)))       # 2 new service requests
        self.assertEqual(2, len(list(clients.output_send_pss.values)))     # clients 3 (timed out) and 4 (new)
        self.assertEqual(clients.sigma, 2)
        for port in (clients.output_phys_wired, clients.output_phys_wireless_srv):
            for phy_msg in port.values:
                if isinstance(phy_msg.data.data, SrvRequest):
                    phy_msg.data.receive(clients._clock)
                    phy_msg.data.data.receive(clients._clock)
                    net_ack = NetworkPacket(phy_msg.data, phy_msg.node_from)
                    net_ack.send(clients._clock)
                    phys_ack = RadioPacket(net_ack.node_from, net_ack.node_to, net_ack, True)
                    phys_ack.send(clients._clock)
                    clients.input_phys.add(phys_ack)
                    app_msg = SrvResponse(phy_msg.data.data, True, clients._clock)
                    app_msg.send(clients._clock)
                    net_msg = NetworkPacket(app_msg, app_msg.node_from)
                    net_msg.send(clients._clock)
                    phys_packet = RadioPacket(app_msg.node_from, app_msg.node_to, net_msg, True)
                    phys_packet.send(clients._clock)
                    clients.input_phys.add(phys_packet)
        # We introduce deceptive PSS messages
        for client_id in ('client_1', 'client_2', 'client_3', 'client_4'):
            app_msg = PSSMessage('AP', client_id, clients._clock)
            app_msg.send(clients._clock)
            net_msg = NetworkPacket(app_msg, app_msg.node_from)
            net_msg.send(clients._clock)
            phys_packet = RadioPacket('AP', client_id, net_msg, True)
            phys_packet.send(clients._clock)
            clients.input_phys.add(phys_packet)
        external_advance(clients, 0)
        self.assertEqual(0, clients.sigma)  # messages in queue

        internal_advance(clients)
        self.assertEqual(2, len(clients.output_srv_report))  # 2 reports
        self.assertEqual(3, len(clients.output_phys_wired))  # 2 ACKs, fourth srv request from client 1
        self.assertEqual(1, len(clients.output_phys_wireless_srv))  # 2 ACKs, fourth srv request from client 1
        self.assertEqual(4, len(clients.output_phys_wireless_acc))  # 4 PSS ACKs, 1 disconnect request (client 2)
        self.assertEqual(2, clients.sigma)

        for port in (clients.output_phys_wired, clients.output_phys_wireless_srv):
            for phy_msg in port.values:
                if isinstance(phy_msg.data.data, SrvRequest):
                    phy_msg.data.receive(clients._clock)
                    phy_msg.data.data.receive(clients._clock)
                    net_ack = NetworkPacket(phy_msg.data, phy_msg.node_from)
                    net_ack.send(clients._clock)
                    phys_ack = RadioPacket(net_ack.node_from, net_ack.node_to, net_ack, True)
                    phys_ack.send(clients._clock)
                    clients.input_phys.add(phys_ack)
                    app_msg = SrvResponse(phy_msg.data.data, True, clients._clock)
                    app_msg.send(clients._clock)
                    net_msg = NetworkPacket(app_msg, app_msg.node_from)
                    net_msg.send(clients._clock)
                    phys_packet = RadioPacket(app_msg.node_from, app_msg.node_to, net_msg, True)
                    phys_packet.send(clients._clock)
                    clients.input_phys.add(phys_packet)

        for port in (clients.output_phys_wired, clients.output_phys_wireless_acc):
            for phy_msg in port.values:
                if isinstance(phy_msg.data.data, DisconnectRequest):
                    phy_msg.data.receive(clients._clock)
                    net_ack = NetworkPacket(phy_msg.data, phy_msg.node_from)
                    net_ack.send(clients._clock)
                    phys_ack = RadioPacket(net_ack.node_from, net_ack.node_to, net_ack, True)
                    phys_ack.send(clients._clock)
                    clients.input_phys.add(phys_ack)
                    app_msg = DisconnectResponse(phy_msg.data.data, True, clients._clock)
                    app_msg.send(clients._clock)
                    net_msg = NetworkPacket(app_msg, app_msg.node_from)
                    net_msg.send(clients._clock)
                    phys_packet = RadioPacket(app_msg.node_from, app_msg.node_to, net_msg, True)
                    phys_packet.send(clients._clock)
                    clients.input_phys.add(phys_packet)
        external_advance(clients, 0)
        self.assertEqual(0, clients.sigma)

        internal_advance(clients)
        self.assertEqual(1, len(clients.output_remove_client))
        self.assertEqual('client_2', clients.output_remove_client.get())
        self.assertEqual(1, len(clients.output_srv_report))
        self.assertEqual(1, len(clients.output_phys_wireless_acc))  # ACKs
        self.assertEqual(1, len(clients.output_phys_wired))  # ACKs
        self.assertEqual(2, clients.sigma)

    def test_shortcut_net(self):
        self.prepare_scenario()
        clients = ClientsShortcut(NetworkPacket, clients_config)
        clients.initialize()
        # Check initial status
        self.assertEqual(clients.sigma, 0)
        self.assertEqual(len(clients.events), 3)

        internal_advance(clients)
        self.assertEqual(len(clients.events), 2)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)
        self.assertEqual(len(clients.clients), 2)
        self.assertTrue('client_1' in clients.clients)
        self.assertTrue('client_2' in clients.clients)

        conn_reqs: dict[str, ConnectRequest] = dict()

        internal_advance(clients)
        self.assertEqual(len(clients.events), 2)
        self.assertEqual(len(list(clients.output_create_client.values)), 2)
        clients.output_create_client.clear()
        self.assertEqual(len(list(clients.output_data.values)), 1)
        net_packet = clients.output_data.get()
        self.assertEqual('client_1', net_packet.node_from)
        self.assertEqual('OLT', net_packet.node_to)
        self.assertIsInstance(net_packet.data, ConnectRequest)
        conn_reqs['client_1'] = net_packet.data
        clients.output_data.clear()
        self.assertEqual(len(clients.output_send_pss), 1)
        self.assertEqual('client_2', clients.output_send_pss.get().client_id)
        clients.output_send_pss.clear()
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, min(GatewaysConfig.PSS_WINDOW, PacketConfig.SESSION_TIMEOUT))
        # We introduce deceptive PSS messages
        for client_id in ('client_1', 'client_2', 'client_3', 'client_4'):
            app_msg = PSSMessage('AP', client_id, clients._clock)
            app_msg.send(clients._clock)
            net_msg = NetworkPacket(app_msg, app_msg.node_from)
            net_msg.send(clients._clock)
            phys_packet = RadioPacket('AP', client_id, net_msg, True)
            clients.input_phys_pss.add(phys_packet)
        external_advance(clients, 0)
        self.assertEqual(clients.sigma, 2)

        internal_advance(clients)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)
        internal_advance(clients)
        self.assertEqual(2, len(clients.output_data))  # Two connection requests
        for net_msg in clients.output_data.values:
            if isinstance(net_msg.data, ConnectRequest):
                conn_reqs[net_msg.data.node_from] = net_msg.data
                net_msg.receive(clients._clock)
                net_ack = NetworkPacket(net_msg, net_msg.node_to)
                net_ack.send(clients._clock)
                net_ack.data.ack = None  # little trap to avoid stuff
                clients.input_data.add(net_ack)
        clients.output_data.clear()
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 2)
        # A new client must be created. Already created UEs should try to connect again
        internal_advance(clients)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(0, clients.sigma)
        internal_advance(clients)
        self.assertEqual(1, len(list(clients.output_create_client.values)))  # One new client
        self.assertEqual(1, len(list(clients.output_send_pss.values)))
        self.assertEqual('client_3', clients.output_send_pss.get().client_id)
        self.assertEqual(2, len(clients.output_data))  # Two connection requests
        clients.output_create_client.clear()
        clients.output_send_pss.clear()
        clients.output_data.clear()
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 2)

        # UEs receive connection response
        for client_id, conn_req in conn_reqs.items():
            app_msg = ConnectResponse(conn_req, True, clients._clock)
            app_msg.send(clients._clock)
            net_msg = NetworkPacket(app_msg, app_msg.node_from)
            net_msg.send(clients._clock)
            clients.input_data.add(net_msg)
        external_advance(clients, 0)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)  # Messages in queue
        internal_advance(clients)
        self.assertEqual(len(clients.output_data), 4)  # ACK messages and service requests
        self.assertEqual(clients.sigma, 2)

        for _ in range(2):
            for net_msg in clients.output_data.values:
                net_msg.receive(clients._clock)
                net_ack = NetworkPacket(net_msg, net_msg.node_to)
                net_ack.send(clients._clock)
                clients.input_data.add(net_ack)
                if isinstance(net_msg.data, SrvRequest):
                    net_msg.data.receive(clients._clock)
                    app_msg = SrvResponse(net_msg.data, True, clients._clock)
                    app_msg.send(clients._clock)
                    net_msg = NetworkPacket(app_msg, app_msg.node_from)
                    net_msg.send(clients._clock)
                    clients.input_data.add(net_msg)
            external_advance(clients, 0)
            for out_port in clients.out_ports:
                self.assertTrue(out_port.empty())
            self.assertEqual(clients.sigma, 0)  # Messages in queue
            internal_advance(clients)
            self.assertEqual(2, len(list(clients.output_srv_report.values)))  # service reports
            clients.output_srv_report.clear()
            self.assertEqual(4, len(list(clients.output_data.values)))  # 2, acks, 2 new service requests
            self.assertEqual(clients.sigma, 2)
        internal_advance(clients)
        self.assertEqual(0, clients.sigma)  # messages in queue
        internal_advance(clients)
        self.assertEqual(1, len(clients.output_create_client))  # client 4 is created at t = 6
        self.assertEqual(0, len(clients.output_remove_client))
        self.assertEqual(2, len(clients.output_data))  # 2 new service requests
        self.assertEqual(2, len(clients.output_send_pss))  # clients 3 (timed out) and 4 (new)
        self.assertEqual(clients.sigma, 2)

        for net_msg in clients.output_data.values:
            if isinstance(net_msg.data, SrvRequest):
                net_msg.receive(clients._clock)
                net_msg.data.receive(clients._clock)
                net_ack = NetworkPacket(net_msg, net_msg.node_to)
                net_ack.send(clients._clock)
                clients.input_data.add(net_ack)
                app_msg = SrvResponse(net_msg.data, True, clients._clock)
                app_msg.send(clients._clock)
                net_msg = NetworkPacket(app_msg, app_msg.node_from)
                net_msg.send(clients._clock)
                clients.input_data.add(net_msg)
        # We introduce deceptive PSS messages
        for client_id in ('client_1', 'client_2', 'client_3', 'client_4'):
            app_msg = PSSMessage('AP', client_id, clients._clock)
            app_msg.send(clients._clock)
            net_msg = NetworkPacket(app_msg, app_msg.node_from)
            net_msg.send(clients._clock)
            phys_packet = RadioPacket('AP', client_id, net_msg, True)
            clients.input_phys_pss.add(phys_packet)
        external_advance(clients, 0)
        self.assertEqual(0, clients.sigma)  # messages in queue
        internal_advance(clients)
        self.assertEqual(2, len(clients.output_srv_report))  # 2 reports
        self.assertEqual(4, len(clients.output_data))  # 2 ACKs, fourth srv request from client 1, 1 disconnect request (client 2)
        self.assertEqual(2, clients.sigma)
        for net_msg in clients.output_data.values:
            if isinstance(net_msg.data, SrvRequest):
                net_msg.receive(clients._clock)
                net_msg.data.receive(clients._clock)
                net_ack = NetworkPacket(net_msg, net_msg.node_to)
                net_ack.send(clients._clock)
                clients.input_data.add(net_ack)
                app_msg = SrvResponse(net_msg.data, True, clients._clock)
                app_msg.send(clients._clock)
                net_msg = NetworkPacket(app_msg, app_msg.node_from)
                net_msg.send(clients._clock)
                clients.input_data.add(net_msg)
            elif isinstance(net_msg.data, DisconnectRequest):
                net_msg.receive(clients._clock)
                net_ack = NetworkPacket(net_msg, net_msg.node_to)
                net_ack.send(clients._clock)
                clients.input_data.add(net_ack)
                app_msg = DisconnectResponse(net_msg.data, True, clients._clock)
                app_msg.send(clients._clock)
                net_msg = NetworkPacket(app_msg, app_msg.node_from)
                net_msg.send(clients._clock)
                clients.input_data.add(net_msg)
        external_advance(clients, 0)
        self.assertEqual(0, clients.sigma)

        internal_advance(clients)
        self.assertEqual(1, len(clients.output_remove_client))
        self.assertEqual('client_2', clients.output_remove_client.get())
        self.assertEqual(1, len(clients.output_srv_report))
        self.assertEqual(2, len(clients.output_data))  # ACKs
        self.assertEqual(2, clients.sigma)

    def test_shortcut_app(self):
        self.prepare_scenario()
        clients = ClientsShortcut(AppPacket, clients_config)
        clients.initialize()
        # Check initial status
        self.assertEqual(clients.sigma, 0)
        self.assertEqual(len(clients.events), 3)

        internal_advance(clients)
        self.assertEqual(len(clients.events), 2)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)
        self.assertEqual(len(clients.clients), 2)
        self.assertTrue('client_1' in clients.clients)
        self.assertTrue('client_2' in clients.clients)

        conn_reqs: dict[str, ConnectRequest] = dict()

        internal_advance(clients)
        self.assertEqual(len(clients.events), 2)
        self.assertEqual(len(list(clients.output_create_client.values)), 2)
        clients.output_create_client.clear()
        self.assertEqual(len(list(clients.output_data.values)), 1)
        app_packet = clients.output_data.get()
        self.assertEqual('client_1', app_packet.node_from)
        self.assertEqual('OLT', app_packet.node_to)
        self.assertIsInstance(app_packet, ConnectRequest)
        conn_reqs['client_1'] = app_packet
        clients.output_data.clear()
        self.assertEqual(len(clients.output_send_pss), 1)
        self.assertEqual('client_2', clients.output_send_pss.get().client_id)
        clients.output_send_pss.clear()
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, min(GatewaysConfig.PSS_WINDOW, PacketConfig.SESSION_TIMEOUT))
        # We introduce deceptive PSS messages
        for client_id in ('client_1', 'client_2', 'client_3', 'client_4'):
            app_msg = PSSMessage('AP', client_id, clients._clock)
            app_msg.send(clients._clock)
            net_msg = NetworkPacket(app_msg, app_msg.node_from)
            net_msg.send(clients._clock)
            phys_packet = RadioPacket('AP', client_id, net_msg, True)
            clients.input_phys_pss.add(phys_packet)
        external_advance(clients, 0)
        self.assertEqual(clients.sigma, 2)

        internal_advance(clients)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)
        internal_advance(clients)
        self.assertEqual(1, len(clients.output_data))  # Two connection requests
        app_msg = clients.output_data.get()
        self.assertIsInstance(app_msg, ConnectRequest)
        conn_reqs[app_msg.node_from] = app_msg
        clients.output_data.clear()
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 2)
        # A new client must be created
        internal_advance(clients)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(0, clients.sigma)
        internal_advance(clients)
        self.assertEqual(1, len(clients.output_create_client))  # One new client
        self.assertEqual(1, len(clients.output_send_pss))
        self.assertEqual('client_3', clients.output_send_pss.get().client_id)
        self.assertEqual(0, len(clients.output_data))  # Two connection requests
        clients.output_create_client.clear()
        clients.output_send_pss.clear()
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 2)

        # UEs receive connection response
        for client_id, conn_req in conn_reqs.items():
            app_msg = ConnectResponse(conn_req, True, clients._clock)
            app_msg.send(clients._clock)
            clients.input_data.add(app_msg)
        external_advance(clients, 0)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)  # Messages in queue
        internal_advance(clients)
        self.assertEqual(len(clients.output_data), 2)  # service requests
        self.assertEqual(clients.sigma, 2)
        for _ in range(2):
            for app_msg in clients.output_data.values:
                if isinstance(app_msg, SrvRequest):
                    app_msg.receive(clients._clock)
                    app_msg = SrvResponse(app_msg, True, clients._clock)
                    app_msg.send(clients._clock)
                    clients.input_data.add(app_msg)
            external_advance(clients, 0)
            for out_port in clients.out_ports:
                self.assertTrue(out_port.empty())
            self.assertEqual(clients.sigma, 0)  # Messages in queue
            internal_advance(clients)
            self.assertEqual(2, len(clients.output_srv_report))  # service reports
            clients.output_srv_report.clear()
            self.assertEqual(2, len(clients.output_data))  # 2 new service requests
            self.assertEqual(clients.sigma, 2)
        reqs = [req for req in clients.output_data.values]
        internal_advance(clients)
        self.assertEqual(0, clients.sigma)  # messages in queue
        internal_advance(clients)
        self.assertEqual(1, len(clients.output_create_client))  # client 4 is created at t = 6
        self.assertEqual(0, len(clients.output_remove_client))
        self.assertEqual(0, len(clients.output_data))  # 2 new service requests
        self.assertEqual(2, len(clients.output_send_pss))  # clients 3 (timed out) and 4 (new)
        self.assertEqual(clients.sigma, 2)

        for app_msg in reqs:
            if isinstance(app_msg, SrvRequest):
                app_msg.receive(clients._clock)
                app_msg = SrvResponse(app_msg, True, clients._clock)
                app_msg.send(clients._clock)
                clients.input_data.add(app_msg)
        # We introduce deceptive PSS messages
        for client_id in ('client_1', 'client_2', 'client_3', 'client_4'):
            app_msg = PSSMessage('AP', client_id, clients._clock)
            app_msg.send(clients._clock)
            net_msg = NetworkPacket(app_msg, app_msg.node_from)
            net_msg.send(clients._clock)
            phys_packet = RadioPacket('AP', client_id, net_msg, True)
            clients.input_phys_pss.add(phys_packet)
        external_advance(clients, 0)
        self.assertEqual(0, clients.sigma)

        internal_advance(clients)
        self.assertEqual(2, len(clients.output_srv_report))
        self.assertEqual(2, len(clients.output_data))
        self.assertEqual(2, clients.sigma)

        for app_msg in clients.output_data.values:
            if isinstance(app_msg, SrvRequest):
                app_msg.receive(clients._clock)
                app_msg = SrvResponse(app_msg, True, clients._clock)
                app_msg.send(clients._clock)
                clients.input_data.add(app_msg)
            elif isinstance(app_msg, DisconnectRequest):
                app_msg = DisconnectResponse(app_msg, True, clients._clock)
                app_msg.send(clients._clock)
                clients.input_data.add(app_msg)
        external_advance(clients, 0)
        self.assertEqual(0, clients.sigma)

        internal_advance(clients)
        self.assertEqual(1, len(clients.output_remove_client))
        self.assertEqual('client_2', clients.output_remove_client.get())
        self.assertEqual(1, len(clients.output_srv_report))
        self.assertEqual(2, clients.sigma)

    def test_lite(self):
        self.prepare_scenario()
        clients = ClientsLite(clients_config)
        clients.initialize()
        # Check initial status
        self.assertEqual(clients.sigma, 0)
        self.assertEqual(len(clients.events), 3)

        internal_advance(clients)
        self.assertEqual(len(clients.events), 2)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)
        self.assertEqual(len(clients.clients), 2)
        self.assertTrue('client_1' in clients.clients)
        self.assertTrue('client_2' in clients.clients)

        internal_advance(clients)
        self.assertEqual(len(clients.events), 2)
        self.assertEqual(len(clients.output_create_client), 2)
        clients.output_create_client.clear()
        self.assertEqual(len(clients.output_data), 2)  # 2 service requests
        srv_reqs: list[SrvRequest] = list()
        for app_msg in clients.output_data.values:
            self.assertIsInstance(app_msg, SrvRequest)
            srv_reqs.append(app_msg)
        self.assertEqual(clients.sigma, 2)  # create new request

        internal_advance(clients)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 2)  # create new request, create new client

        # A new client must be created
        internal_advance(clients)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(0, clients.sigma)
        internal_advance(clients)
        self.assertEqual(1, len(clients.output_create_client))  # One new client
        self.assertEqual(1, len(clients.output_data))  # One service request
        srv_reqs.append(clients.output_data.get())
        clients.output_create_client.clear()
        clients.output_data.clear()
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 2)

        for app_msg in srv_reqs:
            app_msg.receive(clients._clock)
            app_msg = SrvResponse(app_msg, True, clients._clock)
            app_msg.send(clients._clock)
            clients.input_data.add(app_msg)
        external_advance(clients, 0)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)  # Messages in queue
        internal_advance(clients)
        self.assertEqual(3, len(clients.output_srv_report))  # service reports
        clients.output_srv_report.clear()
        self.assertEqual(2, len(clients.output_data))  # 2 new service requests
        self.assertEqual(clients.sigma, 2)

        for app_msg in clients.output_data.values:
            if isinstance(app_msg, SrvRequest):
                app_msg.receive(clients._clock)
                app_msg = SrvResponse(app_msg, True, clients._clock)
                app_msg.send(clients._clock)
                clients.input_data.add(app_msg)
        external_advance(clients, 0)
        for out_port in clients.out_ports:
            self.assertTrue(out_port.empty())
        self.assertEqual(clients.sigma, 0)  # Messages in queue
        internal_advance(clients)
        self.assertEqual(2, len(clients.output_srv_report))  # service reports
        clients.output_srv_report.clear()
        self.assertEqual(2, len(clients.output_data))  # 2 new service requests
        self.assertEqual(clients.sigma, 2)

        reqs = [req for req in clients.output_data.values]
        internal_advance(clients)
        self.assertEqual(0, clients.sigma)  # messages in queue
        internal_advance(clients)
        self.assertEqual(1, len(clients.output_create_client))  # client 4 is created at t = 6
        self.assertEqual(0, len(clients.output_remove_client))
        self.assertEqual(2, len(clients.output_data))  # 2 new service requests
        self.assertEqual(clients.sigma, 2)

        for app_msg in reqs:
            if isinstance(app_msg, SrvRequest):
                app_msg.receive(clients._clock)
                app_msg = SrvResponse(app_msg, True, clients._clock)
                app_msg.send(clients._clock)
                clients.input_data.add(app_msg)
        external_advance(clients, 0)
        self.assertEqual(0, clients.sigma)
        internal_advance(clients)
        self.assertEqual(1, len(clients.output_remove_client))
        self.assertEqual('client_2', clients.output_remove_client.get())
        self.assertEqual(2, len(clients.output_srv_report))
        self.assertEqual(1, len(clients.output_data))
        self.assertEqual(2, clients.sigma)
        for app_msg in clients.output_data.values:
            if isinstance(app_msg, SrvRequest):
                app_msg.receive(clients._clock)
                app_msg = SrvResponse(app_msg, True, clients._clock)
                app_msg.send(clients._clock)
                clients.input_data.add(app_msg)
        external_advance(clients, 0)
        self.assertEqual(0, clients.sigma)

        internal_advance(clients)
        self.assertEqual(1, len(clients.output_srv_report))
        self.assertEqual(2, clients.sigma)
