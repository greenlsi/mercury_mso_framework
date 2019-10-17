import os
import csv
from xdevs.models import Port
from ..common import Stateless
from ..common.packet.application.ran.ran_access import NewUpLinkMCS, NewDownLinkMCS


class RadioTransducer(Stateless):
    def __init__(self, name, ul_file_path, dl_file_path):
        super().__init__(name=name)

        self.ul_file_path = ul_file_path
        self.dl_file_path = dl_file_path

        self.input_new_ul_mcs = Port(NewUpLinkMCS, name + '_input_new_ul_mcs')
        self.input_new_dl_mcs = Port(NewDownLinkMCS, name + '_input_new_dl_mcs')
        self.add_in_port(self.input_new_ul_mcs)
        self.add_in_port(self.input_new_dl_mcs)

    def check_in_ports(self):
        if self.input_new_ul_mcs:
            if not os.path.isfile(self.ul_file_path):
                with open(self.ul_file_path, 'w') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow(['time', 'ue_id', 'ap_id', 'mcs_index', 'efficiency', 'bandwidth', 'rate'])
            with open(self.ul_file_path, 'a') as file:
                writer = csv.writer(file, delimiter=';')
                for job in self.input_new_ul_mcs.values:
                    bandwidth = job.bandwidth
                    efficiency = job.efficiency
                    rate = bandwidth * efficiency
                    writer.writerow([self._clock, job.ue_id, job.ap_id, job.mcs_index, efficiency, bandwidth, rate])

        if self.input_new_dl_mcs:
            if not os.path.isfile(self.dl_file_path):
                with open(self.dl_file_path, 'w') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow(['time', 'ap_id', 'ue_id', 'mcs_index', 'efficiency', 'bandwidth', 'rate'])
            with open(self.dl_file_path, 'a') as file:
                writer = csv.writer(file, delimiter=';')
                for job in self.input_new_dl_mcs.values:
                    bandwidth = job.bandwidth
                    efficiency = job.efficiency
                    rate = bandwidth * efficiency
                    writer.writerow([self._clock, job.ap_id, job.ue_id, job.mcs_index, efficiency, bandwidth, rate])

    def process_internal_messages(self):
        pass
