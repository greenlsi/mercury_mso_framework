import os
import csv
from xdevs.models import Port
from ..common import Stateless
from ..common.packet.application.service import ServiceDelayReport


class PerceivedDelayTransducer(Stateless):
    def __init__(self, name, file_path):
        super().__init__(name=name)
        self.file_path = file_path

        self.input_service_delay_report = Port(ServiceDelayReport, name + '_input_delay')
        self.add_in_port(self.input_service_delay_report)

    def check_in_ports(self):
        if self.input_service_delay_report:
            if not os.path.isfile(self.file_path):
                with open(self.file_path, 'a') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow(['time', 'ue_id', 'service_id', 'generated', 'first_sent', 'processed', 'delay',
                                     'times_sent'])
            with open(self.file_path, 'a') as file:
                writer = csv.writer(file, delimiter=';')
                for job in self.input_service_delay_report.values:
                    writer.writerow([self._clock, job.ue_id, job.service_id, job.instant_generated, job.instant_sent,
                                     job.instant_received, job.delay, job.times_sent])

    def process_internal_messages(self):
        pass
