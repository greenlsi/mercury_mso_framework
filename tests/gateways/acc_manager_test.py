import unittest
from math import inf
from mercury.config.client import ServicesConfig
from mercury.model.gateways.acc_manager import *
from mercury.msg.packet.app_packet.srv_packet import SrvRequest, SrvResponse
import mercury.logger as logger

logger.set_logger_level('INFO')
logger.add_stream_handler()


def internal_advance(model):
    for port in model.out_ports:
        port.clear()
    model.lambdaf()
    model.deltint()


def external_advance(model, e):
    for port in model.out_ports:
        port.clear()
    model.deltext(e)
    for port in model.in_ports:
        port.clear()


class GatewayAccessManagerTestCase(unittest.TestCase):
    def test_wired(self):
        # Define initialization parameters
        gateway_id: str = 'gateway'
        default_server: str = 'server'
        wired: bool = True
        amf = AccessManagementFunction(gateways={'gateway', 'other'})
        if 'service' not in ServicesConfig.SERVICES:
            ServicesConfig.add_service('service', 1, 'periodic', {'period': 1}, 'periodic', {'period': 1}, 'periodic', {'period': 1})

        acc: AccessManager = AccessManager(gateway_id, wired, default_server, amf)
        acc.initialize()
        self.assertEqual(inf, acc.sigma)
        self.assertTrue(acc.wired)
        # Client 1 requests to connect
        client_1_req = ConnectRequest('client_1', 'gateway', 0)
        client_1_req.send(0)
        acc.input_app.add(client_1_req)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        self.assertEqual(gateway_id, amf.get_client_gateway('client_1'))
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        connect_resp = acc.output_access_acc.get()
        self.assertIsInstance(connect_resp, ConnectResponse)
        self.assertTrue(connect_resp.response)
        # client repeats the request
        acc.input_app.add(client_1_req)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        self.assertTrue('client_1' in acc.clients)
        self.assertEqual(gateway_id, amf.get_client_gateway('client_1'))
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        connect_resp = acc.output_access_acc.get()
        self.assertIsInstance(connect_resp, ConnectResponse)
        self.assertTrue(connect_resp.response)
        acc.output_access_acc.clear()
        for port in acc.out_ports:
            self.assertTrue(port.empty())
        # client connected to other gateway requests to connect
        amf.connect_client('client_2', 'other')
        client_2_req = ConnectRequest('client_2', 'gateway', 0)
        client_2_req.send(0)
        acc.input_app.add(client_2_req)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        self.assertFalse('client_2' in acc.clients)
        self.assertEqual('other', amf.get_client_gateway('client_2'))
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        connect_resp = acc.output_access_acc.get()
        self.assertIsInstance(connect_resp, ConnectResponse)
        self.assertFalse(connect_resp.response)
        # clients 1 and 2 send app messages
        req_1 = SrvRequest('service', 'client_1', 0, gateway_id, None, 0)
        req_2 = SrvRequest('service', 'client_2', 0, gateway_id, None, 0)
        for req in req_1, req_2:
            req.send(0)
            acc.input_app.add(req)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(1, len(acc.output_xh_app))
        self.assertEqual(req_1, acc.output_xh_app.get())
        self.assertEqual(default_server, acc.output_xh_app.get().node_to)
        acc.output_xh_app.clear()
        for port in acc.out_ports:
            self.assertTrue(port.empty())
        # clients 1 and 2 send net messages
        net_1 = NetworkPacket(req_1, req_1.node_from)
        net_2 = NetworkPacket(req_2, req_2.node_from)
        for req in net_1, net_2:
            acc.input_net.add(req)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(1, len(acc.output_xh_net))
        self.assertEqual(net_1, acc.output_xh_net.get())
        acc.output_xh_net.clear()
        for port in acc.out_ports:
            self.assertTrue(port.empty())
        # Net messages from crosshaul
        resp_1 = SrvResponse(req_1, True, 0)
        resp_2 = SrvResponse(req_2, True, 0)
        for resp in resp_1, resp_2:
            resp.send(0)
            net = NetworkPacket(resp, resp.node_from)
            net.send(0)
            acc.input_net.add(net)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(1, len(acc.output_access_net))
        self.assertEqual(resp_1, acc.output_access_net.get().data)
        acc.output_access_net.clear()
        for port in acc.out_ports:
            self.assertTrue(port.empty())
        # Clients try to disconnect
        req_1 = DisconnectRequest('client_1', 'gateway', 0)
        req_2 = DisconnectRequest('client_2', 'gateway', 0)
        for req in req_1, req_2:
            req.send(0)
            acc.input_app.add(req)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        self.assertIsNone(amf.get_client_gateway('client_1'))
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        for connect_resp in acc.output_access_acc.values:
            self.assertIsInstance(connect_resp, DisconnectResponse)
            self.assertTrue(connect_resp.response)

    def test_wireless(self):
        # Define initialization parameters
        gateway_id: str = 'gateway'
        wired: bool = False
        default_server: str = 'server'
        amf = AccessManagementFunction(gateways={'gateway', 'other'})
        if 'service' not in ServicesConfig.SERVICES:
            ServicesConfig.add_service('service', 1, 'periodic', {'period': 1}, 'periodic', {'period': 1}, 'periodic', {'period': 1})

        acc: AccessManager = AccessManager(gateway_id, wired, default_server, amf)
        acc.initialize()
        self.assertEqual(inf, acc.sigma)
        self.assertFalse(acc.wired)

        acc.input_send_pss.add('client_1')
        acc.input_send_pss.add('client_2')
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        self.assertFalse(acc.clients)
        internal_advance(acc)
        self.assertEqual(2, len(acc.output_access_acc))
        for msg in acc.output_access_acc.values:
            self.assertIsInstance(msg, PSSMessage)
        acc.output_access_acc.clear()
        for port in acc.out_ports:
            self.assertTrue(port.empty())

        # Client 1 requests to connect
        client_1_req = ConnectRequest('client_1', 'gateway', 0)
        client_1_req.send(0)
        acc.input_app.add(client_1_req)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        self.assertEqual(gateway_id, amf.get_client_gateway('client_1'))
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(1, len(acc.output_access_acc))
        connect_resp = acc.output_access_acc.get()
        self.assertIsInstance(connect_resp, ConnectResponse)
        self.assertTrue(connect_resp.response)
        acc.output_access_acc.clear()
        self.assertEqual(1, len(acc.output_channel_share))
        channel_share = acc.output_channel_share.get()
        self.assertEqual(1, len(channel_share.slave_nodes))
        self.assertTrue('client_1' in channel_share.slave_nodes)
        acc.output_channel_share.clear()
        for port in acc.out_ports:
            self.assertTrue(port.empty())
        # client connected to other gateway requests to connect
        amf.connect_client('client_2', 'other')
        client_2_req = ConnectRequest('client_2', 'gateway', 0)
        client_2_req.send(0)
        acc.input_app.add(client_2_req)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        self.assertFalse('client_2' in acc.clients)
        self.assertEqual('other', amf.get_client_gateway('client_2'))
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        connect_resp = acc.output_access_acc.get()
        self.assertIsInstance(connect_resp, ConnectResponse)
        self.assertFalse(connect_resp.response)
        acc.output_access_acc.clear()
        for port in acc.out_ports:
            self.assertTrue(port.empty())
        # clients 1 and 2 send RRC messages
        rrc_1 = RRCMessage('client_1', gateway_id, {gateway_id: 1, 'other': 0}, 0)
        rrc_2 = RRCMessage('client_2', gateway_id, {gateway_id: 0, 'other': 1}, 0)
        for rrc in rrc_1, rrc_2:
            rrc.send(0)
            acc.input_app.add(rrc)
        external_advance(acc, 0)
        self.assertEqual(inf, acc.sigma)
        # clients 1 and 2 send RRC messages
        rrc_1 = RRCMessage('client_1', gateway_id, {gateway_id: 0, 'other': 1}, 0)
        rrc_2 = RRCMessage('client_2', gateway_id, {gateway_id: 1, 'other': 0}, 0)
        for rrc in rrc_1, rrc_2:
            rrc.send(0)
            acc.input_app.add(rrc)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        internal_advance(acc)
        self.assertEqual(1, len(acc.output_access_acc))
        self.assertIsInstance(acc.output_access_acc.get(), StartHandOver)
        self.assertEqual('other', acc.output_access_acc.get().gateway_to)
        ho_response = HandOverResponse(HandOverRequest(acc.output_access_acc.get().ho_data, 0), True, 0)
        acc.output_access_acc.clear()

        ho_data = HandOverData('client_2', 'other', gateway_id)
        ho_req = HandOverRequest(ho_data, 0)
        ho_req.send(0)
        acc.input_app.add(ho_req)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        self.assertEqual(gateway_id, amf.get_client_gateway('client_2'))
        internal_advance(acc)
        self.assertEqual(1, len(acc.output_access_acc))
        self.assertIsInstance(acc.output_access_acc.get(), HandOverResponse)
        self.assertTrue(acc.output_access_acc.get().response)
        self.assertEqual(1, len(acc.output_channel_share))
        self.assertEqual(2, len(acc.output_channel_share.get().slave_nodes))
        self.assertTrue('client_1' in acc.output_channel_share.get().slave_nodes)
        self.assertTrue('client_2' in acc.output_channel_share.get().slave_nodes)

        amf.handover_client('client_1', gateway_id, 'other')
        acc.input_app.add(HandOverFinished(ho_response, 0))
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        self.assertEqual('other', amf.get_client_gateway('client_1'))
        self.assertEqual(gateway_id, amf.get_client_gateway('client_2'))
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        self.assertEqual(1, len(acc.output_channel_share))
        self.assertEqual(1, len(acc.output_channel_share.get().slave_nodes))
        self.assertTrue('client_2' in acc.output_channel_share.get().slave_nodes)
        # Clients try to disconnect
        req_1 = DisconnectRequest('client_1', 'gateway', 0)
        req_2 = DisconnectRequest('client_2', 'gateway', 0)
        for req in req_1, req_2:
            req.send(0)
            acc.input_app.add(req)
        external_advance(acc, 0)
        self.assertEqual(0, acc.sigma)
        self.assertIsNone(amf.get_client_gateway('client_2'))
        internal_advance(acc)
        self.assertEqual(inf, acc.sigma)
        for connect_resp in acc.output_access_acc.values:
            self.assertIsInstance(connect_resp, DisconnectResponse)
            self.assertTrue(connect_resp.response)


if __name__ == '__main__':
    unittest.main()
