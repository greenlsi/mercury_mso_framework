import unittest
from mercury.model.edcs.edc.profiler import EDCProfiler
from mercury.msg.packet.app_packet.srv_packet import *
from typing import Type


REQ_PERIOD = 10
SESS_PERIOD = 100
WINDOW_SIZE = 50
SESS_T = 40
REQ_DEADLINE = 2
SESS_DEADLINE = 1
COOL_DOWN = 1
SCENARIO: bool = False


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


def new_res(req_type: Type[SrvRelatedRequest], srv_id: str, client_id: str,
            t: float, res_type: Type[SrvRelatedResponse], response, delay: float) -> SrvRelatedResponse:
    req = req_type(srv_id, client_id, 0, 'gateway', 'edc_id', t)
    req.send(t)
    req.receive(t)
    return res_type(req, response, t + delay)


class EDCProfilerTestCase(unittest.TestCase):
    @staticmethod
    def prepare_scenario():
        global SCENARIO
        if not SCENARIO:
            ServicesConfig.add_service('req', REQ_DEADLINE, 'single', {}, 'constant', {'length': inf},
                                       'periodic', {'period': REQ_PERIOD}, cool_down=COOL_DOWN)
            ServicesConfig.add_service('sess', REQ_DEADLINE, 'periodic', {'period': SESS_PERIOD},
                                       'constant', {'length': WINDOW_SIZE}, 'periodic',
                                       {'period': REQ_PERIOD}, cool_down=COOL_DOWN)
            ServicesConfig.add_sess_config('sess', SESS_DEADLINE, True)
            SCENARIO = True

    def test_profiler(self):
        self.prepare_scenario()
        edc_id = 'edc'
        cool_down = 1
        srv_profiling_windows = {'req': 5, 'sess': 10}
        profiler = EDCProfiler(edc_id, srv_profiling_windows)
        profiler.initialize()
        self.assertEqual(profiler.sigma, inf)
        self.assertEqual(profiler._clock, 0)

        res_1 = new_res(SrvRequest, 'req', 'client_1', 0, SrvResponse, True, 1)  #  exit -> 1 + 5 = 6
        profiler.input_srv.add(res_1)
        external_advance(profiler, 1)
        self.assertEqual(1, profiler._clock)
        self.assertEqual(1, profiler.edc_profile.profiles['req'].n_clients)
        self.assertEqual(0, profiler.sigma)
        self.assertEqual(1, profiler.edc_profile.total_n)
        self.assertEqual(1, profiler.edc_profile.total_acc_delay)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_n)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_acc_delay)
        internal_advance(profiler)
        self.assertEqual(1, profiler._clock)
        self.assertEqual(5, profiler.sigma)  # req window
        self.assertEqual(3, len(profiler.output_profile_report))  # req x3

        res_2 = new_res(OpenSessRequest, 'sess', 'client_1', 0, OpenSessResponse, edc_id, 2)  # exit -> 1 + 10 = 11
        profiler.input_srv.add(res_2)
        external_advance(profiler, 0)
        self.assertEqual(1, profiler._clock)
        self.assertEqual(0, profiler.sigma)  # Cool down
        self.assertEqual(1, profiler.edc_profile.profiles['req'].n_clients)
        self.assertEqual(1, profiler.edc_profile.profiles['sess'].n_clients)
        self.assertEqual(2, profiler.edc_profile.total_n)
        self.assertEqual(3, profiler.edc_profile.total_acc_delay)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_n)
        self.assertEqual(1, profiler.edc_profile.missed_deadline_total_n)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_acc_delay)
        self.assertEqual(2, profiler.edc_profile.missed_deadline_total_acc_delay)

        internal_advance(profiler)
        self.assertEqual(1, profiler._clock)
        self.assertEqual(5, profiler.sigma)  # req window
        self.assertEqual(3, len(profiler.output_profile_report))  # sess x3

        res_3 = new_res(SrvRequest, 'req', 'client_1', profiler._clock, SrvResponse, True, 3)  # exit ->5 + 5 = 10
        profiler.input_srv.add(res_3)
        external_advance(profiler, 4)
        self.assertEqual(5, profiler._clock)
        self.assertEqual(1, profiler.edc_profile.profiles['req'].n_clients)
        self.assertEqual(1, profiler.edc_profile.profiles['sess'].n_clients)
        self.assertEqual(0, profiler.sigma)
        self.assertEqual(3, profiler.edc_profile.total_n)
        self.assertEqual(6, profiler.edc_profile.total_acc_delay)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_n)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_acc_delay)
        self.assertEqual(5, profiler.edc_profile.missed_deadline_total_acc_delay)

        internal_advance(profiler)
        self.assertEqual(5, profiler._clock)
        self.assertEqual(3, profiler.edc_profile.total_n)
        self.assertEqual(6, profiler.edc_profile.total_acc_delay)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_n)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_acc_delay)
        self.assertEqual(5, profiler.edc_profile.missed_deadline_total_acc_delay)
        self.assertEqual(1, profiler.sigma)  # req window
        self.assertEqual(1, len(profiler.output_profile_report))  # only changes in req

        internal_advance(profiler)
        self.assertEqual(6, profiler._clock)
        self.assertEqual(1, profiler.edc_profile.profiles['req'].n_clients)
        self.assertEqual(1, profiler.edc_profile.profiles['sess'].n_clients)
        self.assertEqual(3, profiler.edc_profile.total_n)
        self.assertEqual(6, profiler.edc_profile.total_acc_delay)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_n)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_acc_delay)
        self.assertEqual(5, profiler.edc_profile.missed_deadline_total_acc_delay)
        self.assertEqual(2, profiler.edc_profile.window_n)
        self.assertEqual(5, profiler.edc_profile.window_acc_delay)
        self.assertEqual(0, profiler.edc_profile.met_deadline_window_n)
        self.assertEqual(0, profiler.edc_profile.met_deadline_window_acc_delay)
        self.assertEqual(5, profiler.edc_profile.missed_deadline_window_acc_delay)
        self.assertEqual(profiler.sigma, 0)  # message
        self.assertEqual(0, len(profiler.output_profile_report))
        internal_advance(profiler)
        self.assertEqual(6, profiler._clock)
        self.assertEqual(4, profiler.sigma)  # req window
        self.assertEqual(1, len(profiler.output_profile_report))

        internal_advance(profiler)
        self.assertEqual(10, profiler._clock)
        self.assertEqual(0, profiler.edc_profile.profiles['req'].n_clients)
        self.assertEqual(1, profiler.edc_profile.profiles['sess'].n_clients)
        self.assertEqual(3, profiler.edc_profile.total_n)
        self.assertEqual(6, profiler.edc_profile.total_acc_delay)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_n)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_acc_delay)
        self.assertEqual(5, profiler.edc_profile.missed_deadline_total_acc_delay)
        self.assertEqual(1, profiler.edc_profile.window_n)
        self.assertEqual(2, profiler.edc_profile.window_acc_delay)
        self.assertEqual(0, profiler.edc_profile.met_deadline_window_n)
        self.assertEqual(0, profiler.edc_profile.met_deadline_window_acc_delay)
        self.assertEqual(2, profiler.edc_profile.missed_deadline_window_acc_delay)
        self.assertEqual(0, profiler.sigma)  # message
        self.assertEqual(0, len(profiler.output_profile_report))

        internal_advance(profiler)
        self.assertEqual(10, profiler._clock)
        self.assertEqual(1, profiler.sigma)  # req window
        self.assertEqual(1, len(profiler.output_profile_report))

        internal_advance(profiler)
        self.assertEqual(11, profiler._clock)
        self.assertEqual(0, profiler.edc_profile.profiles['req'].n_clients)
        self.assertEqual(0, profiler.edc_profile.profiles['sess'].n_clients)
        self.assertEqual(3, profiler.edc_profile.total_n)
        self.assertEqual(6, profiler.edc_profile.total_acc_delay)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_n)
        self.assertEqual(1, profiler.edc_profile.met_deadline_total_acc_delay)
        self.assertEqual(5, profiler.edc_profile.missed_deadline_total_acc_delay)
        self.assertEqual(0, profiler.edc_profile.window_n)
        self.assertEqual(0, profiler.edc_profile.window_acc_delay)
        self.assertEqual(0, profiler.edc_profile.met_deadline_window_n)
        self.assertEqual(0, profiler.edc_profile.met_deadline_window_acc_delay)
        self.assertEqual(0, profiler.edc_profile.missed_deadline_window_acc_delay)
        self.assertEqual(0, profiler.sigma)  # message
        self.assertEqual(0, len(profiler.output_profile_report))

        internal_advance(profiler)
        self.assertEqual(11, profiler._clock)
        self.assertEqual(inf, profiler.sigma)  # req window
        self.assertEqual(1, len(profiler.output_profile_report))


if __name__ == '__main__':
    unittest.main()
