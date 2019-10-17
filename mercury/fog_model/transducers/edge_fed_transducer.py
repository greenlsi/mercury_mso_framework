import os
import csv
from xdevs.models import Port
from ..common import Stateless
from ..common.edge_fed import EdgeDataCenterReport


class EdgeFederationTransducer(Stateless):
    def __init__(self, name, file_path):
        super().__init__(name=name)
        self.file_path = file_path

        self.input_edc_report = Port(EdgeDataCenterReport, name + '_input_edc_report')
        self.add_in_port(self.input_edc_report)

    def check_in_ports(self):
        if self.input_edc_report:
            if not os.path.isfile(self.file_path):
                with open(self.file_path, 'w') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow(['time', 'edc_id', 'overall_std_u', 'max_std_u', 'overall_power'])
            with open(self.file_path, 'a') as file:
                writer = csv.writer(file, delimiter=';')
                for job in self.input_edc_report.values:
                    writer.writerow([self._clock, job.edc_id, job.overall_std_u, job.max_std_u, job.overall_power])

    def process_internal_messages(self):
        pass
