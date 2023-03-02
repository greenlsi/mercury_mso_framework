from __future__ import annotations
import unittest
from mercury.config.client import ServicesConfig
from mercury.config.edcs import EdgeDataCenterConfig, ProcessingUnitConfig, RManagerConfig
from mercury.model.edcs.edc.r_manager.slicer import EDCResourceSlicer

edc_config: EdgeDataCenterConfig | None = None
REQ_DEADLINE: float = 2


class SlicerTestCase(unittest.TestCase):
    @staticmethod
    def prepare_scenario():
        global edc_config
        if edc_config is None:
            # First, we define the services
            ServicesConfig.add_service('sess', 1, 'periodic', {'period': 1}, 'constant', {}, 'periodic', {'period': 1})
            ServicesConfig.add_sess_config('sess', 1, True)
            ServicesConfig.add_service('req', REQ_DEADLINE, 'periodic', {'period': 1}, 'constant', {}, 'periodic', {'period': 1})
            # Second, we define the processing units
            pu_1_config = ProcessingUnitConfig('pu_1')
            pu_1_config.add_service('sess', 2)
            pu_1_config.add_service('req', 1, proc_t_config={'proc_t': 2})
            pu_2_config = ProcessingUnitConfig('pu_2')
            pu_2_config.add_service('sess', 1)
            pu_2_config.add_service('req', 2, proc_t_config={'proc_t': 1})
            # Fourth, we define the resource manager configuration
            r_manager_config = RManagerConfig()
            # Finally, we define the edge data center configuration
            edc_config = EdgeDataCenterConfig('edc', (0, 0))
            for i in range(5):
                edc_config.add_pu(f'pu_1_{i}', pu_1_config)
                edc_config.add_pu(f'pu_2_{i}', pu_2_config)

    def test_slicer(self):
        srv_priority: list[str] = ['sess', 'req']
        self.prepare_scenario()
        slicer = EDCResourceSlicer(edc_config, srv_priority)

        slice = slicer.slice_resources({'sess': 1, 'req': 1})
        slice_size_1, pus_1 = slice['sess']
        self.assertEqual(slice_size_1, 2)
        self.assertEqual(1, len(pus_1))
        slice_size_2, pus_2 = slice['req']
        self.assertEqual(slice_size_2, 4)
        self.assertEqual(1, len(pus_2))
        _, pus_unassigned = slice[None]
        self.assertEqual(8, len(pus_unassigned))

        slice = slicer.slice_resources({'sess': 3, 'req': 5})
        slice_size_1, pus_1 = slice['sess']
        self.assertEqual(slice_size_1, 4)
        self.assertEqual(2, len(pus_1))
        slice_size_2, pus_2 = slice['req']
        self.assertEqual(slice_size_2, 8)
        self.assertEqual(2, len(pus_2))
        _, pus_unassigned = slice[None]
        self.assertEqual(6, len(pus_unassigned))

        slice = slicer.slice_resources({'sess': 11, 'req': 5})
        slice_size_1, pus_1 = slice['sess']
        self.assertEqual(slice_size_1, 11)
        self.assertEqual(6, len(pus_1))
        slice_size_2, pus_2 = slice['req']
        self.assertEqual(slice_size_2, 8)
        self.assertEqual(2, len(pus_2))
        _, pus_unassigned = slice[None]
        self.assertEqual(2, len(pus_unassigned))

        slice = slicer.slice_resources({'sess': 11, 'req': 10})
        slice_size_1, pus_1 = slice['sess']
        self.assertEqual(slice_size_1, 11)
        self.assertEqual(6, len(pus_1))
        slice_size_2, pus_2 = slice['req']
        self.assertEqual(slice_size_2, 12)
        self.assertEqual(3, len(pus_2))
        _, pus_unassigned = slice[None]
        self.assertEqual(1, len(pus_unassigned))

        slice = slicer.slice_resources({'sess': 11, 'req': 13})
        slice_size_1, pus_1 = slice['sess']
        self.assertEqual(slice_size_1, 11)
        self.assertEqual(6, len(pus_1))
        slice_size_2, pus_2 = slice['req']
        self.assertEqual(slice_size_2, 16)
        self.assertEqual(4, len(pus_2))
        _, pus_unassigned = slice[None]
        self.assertEqual(0, len(pus_unassigned))

        slice = slicer.slice_resources({'sess': 11, 'req': 13})
        slice_size_1, pus_1 = slice['sess']
        self.assertEqual(slice_size_1, 11)
        self.assertEqual(6, len(pus_1))
        slice_size_2, pus_2 = slice['req']
        self.assertEqual(slice_size_2, 16)
        self.assertEqual(4, len(pus_2))
        _, pus_unassigned = slice[None]
        self.assertEqual(0, len(pus_unassigned))

        slice = slicer.slice_resources({'sess': 11, 'req': 17})
        slice_size_1, pus_1 = slice['sess']
        self.assertEqual(slice_size_1, 11)
        self.assertEqual(6, len(pus_1))
        slice_size_2, pus_2 = slice['req']
        self.assertEqual(slice_size_2, 16)
        self.assertEqual(4, len(pus_2))
        _, pus_unassigned = slice[None]
        self.assertEqual(0, len(pus_unassigned))

        slice = slicer.slice_resources({'sess': 10, 'req': 17})
        slice_size_1, pus_1 = slice['sess']
        self.assertEqual(slice_size_1, 10)
        self.assertEqual(5, len(pus_1))
        slice_size_2, pus_2 = slice['req']
        self.assertEqual(slice_size_2, 20)
        self.assertEqual(5, len(pus_2))
        _, pus_unassigned = slice[None]
        self.assertEqual(0, len(pus_unassigned))

        slice = slicer.slice_resources({'sess': 7, 'req': 21})
        slice_size_1, pus_1 = slice['sess']
        self.assertEqual(slice_size_1, 8)
        self.assertEqual(4, len(pus_1))
        slice_size_2, pus_2 = slice['req']
        self.assertEqual(slice_size_2, 21)
        self.assertEqual(6, len(pus_2))
        _, pus_unassigned = slice[None]
        self.assertEqual(0, len(pus_unassigned))

        slice = slicer.slice_resources({'sess': 7, 'req': 22})
        slice_size_1, pus_1 = slice['sess']
        self.assertEqual(slice_size_1, 8)
        self.assertEqual(4, len(pus_1))
        slice_size_2, pus_2 = slice['req']
        self.assertEqual(slice_size_2, 21)
        self.assertEqual(6, len(pus_2))
        _, pus_unassigned = slice[None]
        self.assertEqual(0, len(pus_unassigned))


if __name__ == '__main__':
    unittest.main()
