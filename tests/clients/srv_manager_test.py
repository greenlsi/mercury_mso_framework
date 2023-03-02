from __future__ import annotations
import unittest
from mercury.model.clients.client.srv.srv_manager import SrvManager, GatewayConnection
import mercury.logger as logger
from mercury.msg.packet.app_packet.srv_packet import *
from xdevs.models import Atomic

REQ_PERIOD = 10
SESS_PERIOD = 100
WINDOW_SIZE = 50
SESS_T = 40
REQ_DEADLINE = 5
SESS_DEADLINE = inf
COOL_DOWN = 1

SCENARIO: bool = False


class SrvManagerTest(unittest.TestCase):

    @staticmethod
    def prepare_scenario():
        global SCENARIO
        if not SCENARIO:
            logger.set_logger_level('INFO')
            logger.add_stream_handler()

            ServicesConfig.add_service('req', REQ_DEADLINE, 'single', {}, 'constant', {'length': inf},
                                       'periodic', {'period': REQ_PERIOD}, cool_down=COOL_DOWN)
            ServicesConfig.add_service('sess', REQ_DEADLINE, 'periodic', {'period': SESS_PERIOD},
                                       'constant', {'length': WINDOW_SIZE}, 'periodic',
                                       {'period': REQ_PERIOD}, cool_down=COOL_DOWN)
            ServicesConfig.add_sess_config('sess', SESS_DEADLINE, True)
            SCENARIO = True

    @staticmethod
    def internal_advance(model: Atomic):
        for port in model.out_ports:
            port.clear()
        model.lambdaf()
        model.deltint()

    @staticmethod
    def external_advance(model: Atomic, e: float):
        for port in model.out_ports:
            port.clear()
        model.deltext(e)
        for port in model.in_ports:
            port.clear()

    def test_req_srv(self):
        self.prepare_scenario()
        manager = SrvManager('test', ServicesConfig.SERVICES['req'], None, t_end=100)
        manager.initialize()

        # check initial configuration
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)  # first request is scheduled at t = 0 (guard time is 0)
        self.assertEqual(1, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(1, manager.req_n)
        self.assertFalse(manager.session)
        self.assertFalse(manager.ready_to_dump)

        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD, manager.sigma)
        self.assertEqual(1, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(1, manager.req_n)

        # Second request generated (no connection yet)
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD, manager.sigma)  # Waiting for connection (inf) or next request generation
        self.assertEqual(2, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(2, manager.req_n)
        for port in manager.out_ports:
            self.assertTrue(port.empty())

        # Client is connected after REQ_PERIOD / 2
        manager.input_gateway.add(GatewayConnection('test', 'gateway'))
        self.external_advance(manager, REQ_PERIOD / 2)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(1, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(2, manager.req_n)
        req_1 = manager.sent_req
        req_1.receive(manager._clock)
        t_sent_1 = manager._clock
        self.assertEqual(1, req_1.n_sent)
        self.assertEqual('gateway', req_1.gateway_id)
        self.assertIsNone(req_1.server_id)
        self.assertEqual(0, req_1.t_gen)
        self.assertEqual(manager._clock, req_1.t_sent[0])
        self.assertIsInstance(req_1, SrvRequest)
        self.assertEqual(manager._clock + REQ_DEADLINE, req_1.t_deadline)
        self.internal_advance(manager)
        self.assertEqual(1, len(manager.output_srv))
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD / 2, manager.sigma)
        self.assertEqual(1, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(2, manager.req_n)

        # Third request generated (no response yet)
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD, manager.sigma)  # Waiting for next request generation
        self.assertEqual(2, len(manager.req_buffer))
        self.assertEqual(req_1, manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(3, manager.req_n)
        for port in manager.out_ports:
            self.assertTrue(port.empty())

        # First request failed -> we need to cool down
        resp_1 = SrvResponse(req_1, False, manager._clock, 'first_failed')
        manager.input_srv.add(resp_1)
        self.external_advance(manager, REQ_PERIOD / 2)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(COOL_DOWN, manager.sigma)
        self.assertEqual(3, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertEqual(req_1, manager.req_buffer[0])
        self.assertIsNone(manager.aux_req)
        self.assertEqual(3, manager.req_n)

        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)  # Waiting for next request generation
        self.assertEqual(2, len(manager.req_buffer))
        self.assertEqual(req_1, manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(3, manager.req_n)
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD / 2 - COOL_DOWN, manager.sigma)  # Waiting for next request generation
        self.assertEqual(2, len(manager.req_buffer))
        self.assertEqual(req_1, manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(3, manager.req_n)
        # Fourth packet created
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD, manager.sigma)  # Waiting for next request generation
        self.assertEqual(3, len(manager.req_buffer))
        self.assertEqual(req_1, manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(4, manager.req_n)

        # First request succeeded
        req_1.receive(req_1.t_sent[-1])
        resp_1 = SrvResponse(req_1, True, manager._clock + REQ_PERIOD / 2, 'first_succeeded')
        manager.input_srv.add(resp_1)
        self.external_advance(manager, REQ_PERIOD / 2)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(2, len(manager.req_buffer))
        req_2 = manager.sent_req
        t_sent_2 = manager._clock
        self.assertIsNotNone(req_2)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(4, manager.req_n)
        self.internal_advance(manager)
        rep_1 = manager.output_report.get()
        self.assertFalse(rep_1.deadline_met)
        self.assertEqual(manager._clock - t_sent_1, rep_1.t_delay)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD / 2, manager.sigma)

        # Fifth packet created; receive response for packet 2
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD, manager.sigma)
        self.assertEqual(3, len(manager.req_buffer))
        req_2.receive(manager._clock)
        resp_2 = SrvResponse(req_2, True, manager._clock, 'second_succeeded')
        manager.input_srv.add(resp_2)
        self.external_advance(manager, 0)
        self.assertEqual(2, len(manager.req_buffer))
        req_3 = manager.sent_req
        self.assertIsNotNone(req_3)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(5, manager.req_n)
        self.internal_advance(manager)
        rep_2 = manager.output_report.get()
        self.assertTrue(rep_2.deadline_met)
        self.assertEqual(manager._clock - t_sent_2, rep_2.t_delay)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD, manager.sigma)

        while manager.sent_req is not None:
            req = manager.sent_req
            req.receive(manager._clock)
            resp = SrvResponse(req, True, manager._clock)
            manager.input_srv.add(resp)
            self.external_advance(manager, 0)
            self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(5, manager.req_n)

        # Generate sixth packet
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        req_6 = manager.sent_req
        self.assertIsNone(manager.aux_req)
        self.assertEqual(6, manager.req_n)
        self.internal_advance(manager)
        self.assertEqual(manager.output_srv.get(), req_6)
        self.assertEqual(REQ_PERIOD, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        # Client disconnects after REQ_PERIOD / 2
        manager.input_gateway.add(GatewayConnection('test', None))
        self.external_advance(manager, REQ_PERIOD / 2)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD / 2, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        prev_req_len = 0
        while manager.sigma != inf:
            self.assertEqual(prev_req_len, len(manager.req_buffer))
            self.internal_advance(manager)
            prev_req_len += 1
        self.assertEqual(0, len(manager.req_buffer))
        self.assertEqual(req_6, manager.sent_req)
        self.assertFalse(manager.ready_to_dump)

        # Sixth request failed -> we need remove manager
        resp_6 = SrvResponse(req_6, False, manager._clock, 'sixth_failed')
        manager.input_srv.add(resp_6)
        self.external_advance(manager, REQ_PERIOD / 2)
        self.assertEqual(SrvManager.PHASE_INACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(5, manager.req_n)
        self.internal_advance(manager)
        self.assertFalse(manager.output_active.get().active)
        self.assertEqual(SrvManager.PHASE_INACTIVE, manager.phase)
        self.assertEqual(inf, manager.sigma)
        self.assertTrue(manager.ready_to_dump)

    def test_sess_srv(self):
        self.prepare_scenario()
        manager = SrvManager('test', ServicesConfig.SERVICES['sess'], None, t_end=150)
        manager.initialize()

        # check initial configuration
        self.assertEqual(SrvManager.PHASE_AWAIT_OPEN, manager.phase)
        self.assertEqual(0, manager.sigma)  # first session is scheduled at t = 0 (guard time is 0)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(0, manager.req_n)
        self.assertTrue(manager.session)
        self.assertFalse(manager.ready_to_dump)

        self.internal_advance(manager)
        self.assertTrue(manager.output_active.get().active)
        self.assertFalse(manager.output_srv)
        self.assertEqual(150, manager.sigma)  # first session is scheduled at t = 0 (guard time is 0)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(0, manager.req_n)

        # Client is connected after 10 seconds
        manager.input_gateway.add(GatewayConnection('test', 'gateway'))
        self.external_advance(manager, 10)
        self.assertEqual(SrvManager.PHASE_AWAIT_OPEN, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertEqual(manager.aux_req, manager.sent_req)
        open_req = manager.sent_req
        open_req.receive(manager._clock)
        t_sent_open = manager._clock
        self.assertEqual(1, open_req.n_sent)
        self.assertEqual('gateway', open_req.gateway_id)
        self.assertIsNone(open_req.server_id)
        self.assertEqual(manager._clock, open_req.t_gen)
        self.assertEqual(manager._clock, open_req.t_sent[0])
        self.assertIsInstance(open_req, OpenSessRequest)
        self.internal_advance(manager)
        self.assertEqual(1, len(manager.output_srv))
        self.assertEqual(SrvManager.PHASE_AWAIT_OPEN, manager.phase)
        self.assertEqual(150 - manager._clock, manager.sigma)
        self.assertEqual(open_req, manager.sent_req)

        # First open session request failed
        open_res = OpenSessResponse(open_req, None, manager._clock)
        open_res.send(manager._clock)
        manager.input_srv.add(open_res)
        self.external_advance(manager, 1)
        self.assertEqual(SrvManager.PHASE_AWAIT_OPEN, manager.phase)
        self.assertEqual(COOL_DOWN, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertEqual(manager.aux_req, open_req)
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_AWAIT_OPEN, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertEqual(manager.aux_req, manager.sent_req)
        self.assertEqual(manager.aux_req, open_req)
        self.internal_advance(manager)
        self.assertEqual(manager.output_srv.get(), open_req)
        self.assertEqual(2, open_req.n_sent)

        # Second open session request succeeded
        open_res = OpenSessResponse(open_req, "edc", manager._clock)
        open_res.send(manager._clock + 1)
        manager.input_srv.add(open_res)
        self.external_advance(manager, 1)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(1, manager.req_n)
        req_1 = manager.sent_req
        req_1.receive(manager._clock)
        t_sent_1 = manager._clock
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(1, manager.req_n)
        self.assertEqual(req_1, manager.output_srv.get())

        # Second request generated before receiving first response
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD, manager.sigma)  # Waiting for connection (inf) or next request generation
        self.assertEqual(1, len(manager.req_buffer))
        self.assertEqual(req_1, manager.sent_req)
        self.assertEqual(2, manager.req_n)

        # First request succeeded
        req_1.receive(manager._clock)
        resp_1 = SrvResponse(req_1, True, manager._clock + REQ_PERIOD / 2)
        resp_1.send(manager._clock + REQ_PERIOD / 2)
        manager.input_srv.add(resp_1)
        self.external_advance(manager, REQ_PERIOD / 2)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        req_2 = manager.sent_req
        t_sent_2 = manager._clock
        self.assertIsNotNone(req_2)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(2, manager.req_n)
        self.internal_advance(manager)
        rep_1 = manager.output_report.get()
        self.assertFalse(rep_1.deadline_met)
        self.assertEqual(manager._clock - t_sent_1, rep_1.t_delay)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD / 2, manager.sigma)

        while manager.sigma != inf:
            self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertEqual(req_2, manager.sent_req)
        self.assertEqual(2, manager.req_n)

        # Second request failed
        req_2.receive(manager._clock)
        self.assertEqual("edc", req_2.server_id)
        resp_2 = SrvResponse(req_2, False, manager._clock)
        manager.input_srv.add(resp_2)
        self.external_advance(manager, REQ_PERIOD / 2)
        self.assertEqual(SrvManager.PHASE_AWAIT_CLOSE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertEqual(manager.aux_req, manager.sent_req)
        self.assertEqual(1, manager.req_n)
        close_req = manager.aux_req
        close_req.receive(manager._clock)
        self.assertEqual(manager._clock, close_req.t_sent[0])

        self.internal_advance(manager)
        self.assertEqual(manager.output_srv.get(), close_req)
        self.assertEqual(inf, manager.sigma)

        # First close session request failed
        close_res = CloseSessResponse(close_req, -1, manager._clock + 1)
        close_res.send(manager._clock + 1)
        manager.input_srv.add(close_res)
        self.external_advance(manager, 1)
        self.assertEqual(SrvManager.PHASE_AWAIT_CLOSE, manager.phase)
        self.assertEqual(COOL_DOWN, manager.sigma)
        self.assertIsNone(manager.sent_req)
        self.assertEqual(manager.aux_req, close_req)
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_AWAIT_CLOSE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertIsNotNone(manager.sent_req)
        self.assertEqual(manager.aux_req, manager.sent_req)
        self.assertEqual(manager.aux_req, close_req)
        self.internal_advance(manager)
        self.assertEqual(manager.output_srv.get(), close_req)
        self.assertEqual(2, close_req.n_sent)

        # Second close session request succeeded
        close_res = CloseSessResponse(close_req, 5, manager._clock)
        close_res.send(manager._clock)
        manager.input_srv.add(close_res)
        self.external_advance(manager, 1)
        self.assertEqual(SrvManager.PHASE_INACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(1, manager.req_n)
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_INACTIVE, manager.phase)
        self.assertFalse(manager.output_active.get().active)
        self.assertEqual(close_res, manager.output_report.get().response)
        self.assertEqual(manager.sigma, SESS_PERIOD - manager._clock)

        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_AWAIT_OPEN, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertIsNotNone(manager.sent_req)
        self.assertEqual(manager.aux_req, manager.sent_req)
        open_req = manager.sent_req
        open_req.receive(manager._clock)
        self.assertEqual(manager._clock, open_req.t_gen)
        self.assertEqual(manager._clock, open_req.t_sent[0])

        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_AWAIT_OPEN, manager.phase)
        self.assertEqual(150 - manager._clock, manager.sigma)
        self.assertEqual(open_req, manager.output_srv.get())

        open_res = OpenSessResponse(open_req, "edc", 150 - 11)
        manager.input_srv.add(open_res)
        self.external_advance(manager, manager.sigma - 11)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(2, manager.req_n)
        req_2 = manager.sent_req
        req_2.receive(manager._clock)
        t_sent_2 = manager._clock
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(REQ_PERIOD, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(2, manager.req_n)
        self.assertEqual(req_2, manager.output_srv.get())

        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_ACTIVE, manager.phase)
        self.assertEqual(1, manager.sigma)
        self.assertEqual(1, len(manager.req_buffer))
        self.assertIsNotNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(3, manager.req_n)

        resp_2 = SrvResponse(req_2, True, manager._clock)
        manager.input_srv.add(resp_2)
        self.external_advance(manager, 1)
        self.assertEqual(SrvManager.PHASE_AWAIT_CLOSE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertIsNotNone(manager.sent_req)
        self.assertEqual(manager.aux_req, manager.sent_req)

        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_AWAIT_CLOSE, manager.phase)
        self.assertEqual(inf, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertEqual(2, manager.req_n)
        self.assertFalse(manager.ready_to_dump)
        self.assertEqual(manager.aux_req, manager.output_srv.get())

        manager.aux_req.receive(manager._clock)
        close_res = CloseSessResponse(manager.aux_req, 1, manager._clock)
        close_res.send(manager._clock)
        manager.input_srv.add(close_res)
        self.external_advance(manager, 1)
        self.assertFalse(manager.ready_to_dump)
        self.assertEqual(SrvManager.PHASE_INACTIVE, manager.phase)
        self.assertEqual(0, manager.sigma)
        self.assertEqual(0, len(manager.req_buffer))
        self.assertIsNone(manager.sent_req)
        self.assertIsNone(manager.aux_req)
        self.assertEqual(2, manager.req_n)
        self.internal_advance(manager)
        self.assertEqual(SrvManager.PHASE_INACTIVE, manager.phase)
        self.assertFalse(manager.output_active.get().active)
        self.assertEqual(close_res, manager.output_report.get().response)
        self.assertEqual(manager.sigma, inf)
        self.assertTrue(manager.ready_to_dump)


if __name__ == '__main__':
    unittest.main()
