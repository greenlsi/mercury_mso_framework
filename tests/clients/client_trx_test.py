import unittest
import mercury.logger as logger
from math import inf
from mercury.config.client import ServicesConfig
from mercury.model.clients.client.acc_trx import ClientAccessTransceiver
from mercury.msg.client import GatewayConnection
from mercury.msg.packet import NetworkPacket
from mercury.msg.packet.app_packet.acc_packet import ConnectRequest, ConnectResponse
from mercury.msg.packet.app_packet.srv_packet import SrvRequest, SrvResponse
from mercury.msg.packet.phys_packet import RadioPacket
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


class ClientTransceiverTest(unittest.TestCase):
    def test(self):
        client_id = 'client'
        gateway_id = 'gateway'
        service_id = 'service'
        ServicesConfig.add_service(service_id, 0, 'periodic', {}, 'constant', {}, 'periodic', {})

        app_srv_req = SrvRequest(service_id, client_id, 0, gateway_id, None, 0)
        app_srv_req.send(0)
        net_srv_req = NetworkPacket(app_srv_req, client_id)
        net_srv_req.send(0)
        app_acc_req = ConnectRequest(client_id, gateway_id, 0)
        app_acc_req.send(0)
        net_acc_req = NetworkPacket(app_acc_req, client_id)
        net_acc_req.send(0)

        app_srv_res = SrvResponse(app_srv_req, True, 0)
        app_srv_res.send(0)
        net_srv_res = NetworkPacket(app_srv_res, gateway_id)
        net_srv_res.send(0)
        phys_srv_res = RadioPacket(gateway_id, client_id, net_srv_res, True)
        phys_srv_res.send(0)
        app_acc_res = ConnectResponse(app_acc_req, True, 0)
        app_acc_res.send(0)
        net_acc_res = NetworkPacket(app_acc_res, gateway_id)
        net_acc_res.send(0)
        phys_acc_res = RadioPacket(gateway_id, client_id, net_acc_res, True)
        phys_acc_res.power = 1
        phys_acc_res.noise = 0
        phys_acc_res.send(0)

        trx = ClientAccessTransceiver(client_id, True)
        trx.initialize()
        self.assertIsNone(trx.gateway_id)
        self.assertEqual(inf, trx.sigma)

        trx.input_net.add(net_acc_req)
        trx.input_net.add(net_srv_req)
        trx.input_phys.add(phys_acc_res)
        trx.input_phys.add(phys_srv_res)
        external_advance(trx, 1)
        self.assertIsNone(trx.gateway_id)
        self.assertEqual(0, trx.sigma)
        self.assertEqual(3, len(trx._message_queue))
        internal_advance(trx)
        self.assertEqual(inf, trx.sigma)
        self.assertEqual(1, len(trx.output_phys_acc))
        self.assertEqual(net_acc_req, trx.output_phys_acc.get().data)
        self.assertEqual(0, len(trx.output_phys_srv))
        self.assertEqual(1, len(trx.output_net_acc))
        self.assertEqual(1, trx.output_net_acc.get().data.snr)
        self.assertEqual(net_acc_res, trx.output_net_acc.get())
        self.assertEqual(1, len(trx.output_net_srv))
        self.assertEqual(net_srv_res, trx.output_net_srv.get())


        phys_acc_res.power = 2
        trx.input_gateway.add(GatewayConnection(client_id, gateway_id))
        trx.input_net.add(net_acc_req)
        trx.input_net.add(net_srv_req)
        trx.input_phys.add(phys_acc_res)
        trx.input_phys.add(phys_srv_res)
        external_advance(trx, 1)
        self.assertEqual(gateway_id, trx.gateway_id)
        self.assertEqual(0, trx.sigma)
        self.assertEqual(4, len(trx._message_queue))
        internal_advance(trx)
        self.assertEqual(inf, trx.sigma)
        self.assertEqual(1, len(trx.output_phys_acc))
        self.assertEqual(net_acc_req, trx.output_phys_acc.get().data)
        self.assertEqual(1, len(trx.output_phys_srv))
        self.assertEqual(net_srv_req, trx.output_phys_srv.get().data)
        self.assertEqual(gateway_id, trx.output_phys_acc.get().node_to)
        self.assertEqual(1, len(trx.output_net_acc))
        self.assertEqual(net_acc_res, trx.output_net_acc.get())
        self.assertEqual(2, trx.output_net_acc.get().data.snr)
        self.assertEqual(1, len(trx.output_net_srv))
        self.assertEqual(net_srv_res, trx.output_net_srv.get())

        trx.input_gateway.add(GatewayConnection(client_id, None))
        trx.input_net.add(net_acc_req)
        trx.input_net.add(net_srv_req)
        trx.input_phys.add(phys_acc_res)
        trx.input_phys.add(phys_srv_res)
        external_advance(trx, 1)
        self.assertIsNone(trx.gateway_id)
        self.assertEqual(0, trx.sigma)
        self.assertEqual(3, len(trx._message_queue))
        internal_advance(trx)
        self.assertEqual(inf, trx.sigma)
        self.assertEqual(1, len(trx.output_phys_acc))
        self.assertEqual(net_acc_req, trx.output_phys_acc.get().data)
        self.assertEqual(0, len(trx.output_phys_srv))
        self.assertEqual(1, len(trx.output_net_acc))
        self.assertEqual(net_acc_res, trx.output_net_acc.get())
        self.assertEqual(1, len(trx.output_net_srv))
        self.assertEqual(net_srv_res, trx.output_net_srv.get())
