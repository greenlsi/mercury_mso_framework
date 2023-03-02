from __future__ import annotations
import unittest
import mercury.logger as logger
from mercury.config.edcs import EdgeDataCenterConfig, ProcessingUnitConfig, RManagerConfig
from mercury.model.edcs.edc.r_manager import EDCResourceManager
from mercury.msg.edcs import NewEDCSlicing
from mercury.msg.packet.app_packet.srv_packet import *

REQ_DEADLINE: float = 2
SRV_PRIORITY: list[str] = ['sess', 'req']
edc_config: EdgeDataCenterConfig | None = None


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


class TestResourceManager(unittest.TestCase):
    @staticmethod
    def prepare_scenario(r_manager_config: RManagerConfig):
        global edc_config
        if edc_config is None:
            logger.set_logger_level('INFO')
            logger.add_stream_handler()
            # First, we define the services
            ServicesConfig.add_service('sess', 1, 'periodic', {'period': 1}, 'constant', {}, 'periodic', {'period': 1})
            ServicesConfig.add_sess_config('sess', 1, True)
            ServicesConfig.add_service('req', REQ_DEADLINE, 'periodic', {'period': 1}, 'constant', {}, 'periodic', {'period': 1})
            # Second, we define the processing unit
            pu_config = ProcessingUnitConfig('pu')
            pu_config.add_service('sess', 2)
            pu_config.add_service('req', 1, proc_t_config={'proc_t': 2})
            # Finally, we define the edge data center configuration
            edc_config = EdgeDataCenterConfig('edc', (0, 0), r_manager_config)
            for i in range(5):
                edc_config.add_pu(f'pu_1_{i}', pu_config)

    def test_r_manager_emptiest_pu(self):
        r_manager_config = RManagerConfig(mapping_id='epu', standby=False)
        self.prepare_scenario(r_manager_config)
        r_manager = EDCResourceManager(edc_config, SRV_PRIORITY, cloud_id=None)

        r_manager.initialize()
        self.assertEqual(0, r_manager.sigma)
        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)
        self.assertEqual(len(r_manager.output_report), 1)
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        for srv_id in SRV_PRIORITY:
            self.assertEqual(report.srv_slice_u(srv_id), 1)

        r_manager.input_config.add(NewEDCSlicing('edc', {'sess': 1, 'req': 1}))
        external_advance(r_manager, 0)
        self.assertEqual(0, r_manager.sigma)
        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)
        self.assertEqual(len(r_manager.output_report), 1)
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        for srv_id in SRV_PRIORITY:
            self.assertEqual(report.srv_slice_u(srv_id), 0)

        # Add first session
        sess_req = OpenSessRequest('sess', 'client_1', 0, 'gateway', 'edc', 0)
        sess_req.send(0)
        srv_req = SrvRequest('sess', 'client_1', 0, 'gateway', 'edc', 0)
        srv_req.send(0)
        r_manager.input_srv.add(sess_req)
        r_manager.input_srv.add(srv_req)
        external_advance(r_manager, 0)
        self.assertEqual(0, r_manager.sigma)
        self.assertEqual('pu_1_0', r_manager.req_map['sess']['client_1'].pu_id)

        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)
        self.assertEqual(2, len(r_manager.output_srv_response))
        for msg in r_manager.output_srv_response.values:
            self.assertTrue(msg.response in ["edc", False])
        self.assertEqual(1, len(r_manager.output_report))
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        self.assertEqual(report.srv_slice_u('sess'), 0.5)
        self.assertEqual(report.srv_slice_u('req'), 0)

        sess_req = OpenSessRequest('sess', 'client_1', 0, 'gateway', 'edc', 0)
        sess_req.send(0)
        srv_req = SrvRequest('sess', 'client_1', 0, 'gateway', 'edc', 0)
        srv_req.send(0)
        r_manager.input_srv.add(sess_req)
        r_manager.input_srv.add(srv_req)
        external_advance(r_manager, 0)
        self.assertEqual(0, r_manager.sigma)
        self.assertEqual('pu_1_0', r_manager.req_map['sess']['client_1'].pu_id)

        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)
        self.assertEqual(2, len(r_manager.output_srv_response))
        for msg in r_manager.output_srv_response.values:
            self.assertTrue(msg.response in ["edc", True])
        self.assertEqual(1, len(r_manager.output_report))
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        self.assertEqual(report.srv_slice_u('sess'), 0.5)
        self.assertEqual(report.srv_slice_u('req'), 0)

        # Add second session
        sess_req = OpenSessRequest('sess', 'client_2', 0, 'gateway', 'edc', 0)
        sess_req.send(0)
        r_manager.input_srv.add(sess_req)
        external_advance(r_manager, 0)
        self.assertEqual(0, r_manager.sigma)
        self.assertEqual('pu_1_0', r_manager.req_map['sess']['client_1'].pu_id)
        self.assertEqual('pu_1_0', r_manager.req_map['sess']['client_2'].pu_id)

        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)
        self.assertEqual(1, len(r_manager.output_srv_response))
        self.assertEqual(r_manager.output_srv_response.get().response, "edc")
        self.assertEqual(1, len(r_manager.output_report))
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        self.assertEqual(report.srv_slice_u('sess'), 1)
        self.assertEqual(report.srv_slice_u('req'), 0)

        # Add third session (it does not have space in the slice, it will be allocated in on of the free PUs)
        sess_req = OpenSessRequest('sess', 'client_3', 0, 'gateway', 'edc', 0)
        sess_req.send(0)
        r_manager.input_srv.add(sess_req)
        external_advance(r_manager, 0)
        self.assertEqual(0, r_manager.sigma)
        self.assertEqual('pu_1_0', r_manager.req_map['sess']['client_1'].pu_id)
        self.assertEqual('pu_1_0', r_manager.req_map['sess']['client_2'].pu_id)
        self.assertEqual('pu_1_2', r_manager.req_map['sess']['client_3'].pu_id)

        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)
        self.assertEqual(1, len(r_manager.output_srv_response))
        self.assertEqual(r_manager.output_srv_response.get().response, "edc")
        self.assertEqual(1, len(r_manager.output_report))
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        self.assertEqual(report.srv_slice_u('sess'), 1)
        self.assertAlmostEqual(report.srv_free_u('sess'), 1 / 6)
        self.assertEqual(report.srv_slice_u('req'), 0)

        # New slicing will assign resources used by service sess to service req
        r_manager.input_config.add(NewEDCSlicing('edc', {'sess': 1, 'req': 2}))
        external_advance(r_manager, 0)
        self.assertEqual(0, r_manager.sigma)
        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)
        self.assertEqual(len(r_manager.output_report), 1)
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        self.assertEqual(report.srv_slice_u('sess'), 1)
        self.assertEqual(report.srv_free_u('sess'), 0)
        self.assertEqual(report.srv_slice_u('req'), 1 / 2)

        # Add req request
        srv_req = SrvRequest('req', 'client_1', 0, 'gateway', 'edc', 0)
        srv_req.send(0)
        r_manager.input_srv.add(srv_req)
        external_advance(r_manager, 0)
        self.assertEqual(0, r_manager.sigma)
        self.assertEqual('pu_1_0', r_manager.req_map['sess']['client_1'].pu_id)
        self.assertEqual('pu_1_0', r_manager.req_map['sess']['client_2'].pu_id)
        self.assertEqual('pu_1_1', r_manager.req_map['req']['client_1'].pu_id)
        self.assertEqual('pu_1_2', r_manager.req_map['sess']['client_3'].pu_id)

        internal_advance(r_manager)
        self.assertEqual(2, r_manager.sigma)  # processing time for req requests
        self.assertEqual(0, len(r_manager.output_srv_response))
        self.assertEqual(1, len(r_manager.output_report))
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        self.assertEqual(report.srv_slice_u('sess'), 1)
        self.assertEqual(report.srv_free_u('sess'), 0)
        self.assertEqual(report.srv_slice_u('req'), 1)

        # Close first two sessions
        sess_req_1 = CloseSessRequest('sess', 'client_1', 0, 'gateway', 'edc', 0)
        sess_req_1.send(0)
        r_manager.input_srv.add(sess_req_1)
        sess_req_2 = CloseSessRequest('sess', 'client_2', 0, 'gateway', 'edc', 0)
        sess_req_2.send(0)
        r_manager.input_srv.add(sess_req_2)
        external_advance(r_manager, 1)
        self.assertEqual(0, r_manager.sigma)
        self.assertTrue('client_1' not in r_manager.req_map['sess'])
        self.assertTrue('client_2' not in r_manager.req_map['sess'])
        self.assertEqual('pu_1_1', r_manager.req_map['req']['client_1'].pu_id)
        self.assertEqual('pu_1_2', r_manager.req_map['sess']['client_3'].pu_id)

        internal_advance(r_manager)
        self.assertEqual(1, r_manager.sigma)  # processing time for req requests
        self.assertEqual(2, len(r_manager.output_srv_response))
        for msg in r_manager.output_srv_response.values:
            self.assertEqual(1, msg.response)
        self.assertEqual(1, len(r_manager.output_report))
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        self.assertEqual(report.srv_slice_u('sess'), 0)
        self.assertAlmostEqual(report.srv_free_u('sess'), 0)
        self.assertEqual(report.srv_slice_u('req'), 1)

        # req request finishes from processing
        internal_advance(r_manager)
        self.assertEqual(0, r_manager.sigma)
        self.assertEqual(0, len(r_manager.output_srv_response))
        self.assertEqual(0, len(r_manager.output_report))
        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)
        self.assertTrue('req' not in r_manager.req_map)
        self.assertEqual('pu_1_2', r_manager.req_map['sess']['client_3'].pu_id)
        self.assertEqual(1, len(r_manager.output_srv_response))
        self.assertTrue(r_manager.output_srv_response.get().response)
        self.assertEqual(1, len(r_manager.output_report))
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        self.assertEqual(report.srv_slice_u('sess'), 0)
        self.assertAlmostEqual(report.srv_free_u('sess'), 0)
        self.assertEqual(report.srv_slice_u('req'), 1 / 2)

        # Close the last session
        sess_req = CloseSessRequest('sess', 'client_3', 2, 'gateway', 'edc', 0)
        sess_req.send(0)
        r_manager.input_srv.add(sess_req)
        external_advance(r_manager, 1)
        self.assertEqual(0, r_manager.sigma)
        self.assertFalse(r_manager.req_map)

        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)  # processing time for req requests
        self.assertEqual(1, len(r_manager.output_srv_response))
        self.assertEqual(3, r_manager.output_srv_response.get().response)
        self.assertEqual(1, len(r_manager.output_report))
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        self.assertEqual(report.srv_slice_u('sess'), 0)
        self.assertAlmostEqual(report.srv_free_u('sess'), 0)
        self.assertEqual(report.srv_slice_u('req'), 0)

        # New slicing will congest the service sess
        r_manager.input_config.add(NewEDCSlicing('edc', {'sess': 1, 'req': 5}))
        external_advance(r_manager, 0)
        self.assertEqual(0, r_manager.sigma)
        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)
        self.assertEqual(len(r_manager.output_report), 1)
        report = r_manager.output_report.get()
        self.assertTrue(report.congested)
        self.assertFalse(report.srv_congested('sess'))
        self.assertTrue(report.srv_congested('req'))
        self.assertEqual(report.srv_slice_u('sess'), 0)
        self.assertEqual(report.srv_free_u('sess'), 1)  # there are no free resources
        self.assertEqual(report.srv_slice_u('req'), 0)
        self.assertEqual(report.srv_free_u('req'), 1)  # there are no free resources

        # New slicing will free all the resources
        r_manager.input_config.add(NewEDCSlicing('edc', {'sess': 0, 'req': 0}))
        external_advance(r_manager, 0)
        self.assertEqual(0, r_manager.sigma)
        internal_advance(r_manager)
        self.assertEqual(inf, r_manager.sigma)
        self.assertEqual(len(r_manager.output_report), 1)
        report = r_manager.output_report.get()
        self.assertFalse(report.congested)
        self.assertEqual(report.srv_slice_u('sess'), 1)  # there are no sliced resources
        self.assertEqual(report.srv_free_u('sess'), 0)
        self.assertEqual(report.srv_slice_u('req'), 1)  # there are no sliced resources
        self.assertEqual(report.srv_free_u('req'), 0)
