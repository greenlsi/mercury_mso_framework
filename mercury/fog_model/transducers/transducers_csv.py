import os
import csv
import pandas as pd
from .transducers import TransducerBuilder, UEDelayTransducer, RadioTransducer, EdgeDataCenterTransducer


class CSVEdgeDataCenterTransducer(EdgeDataCenterTransducer):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def process_edc_reports(self):
        with open(self.file_path, 'a') as file:
            writer = csv.writer(file, delimiter=';')
            for job in self.input_edc_report.values:
                writer.writerow([self._clock, job.edc_id, job.overall_std_u, job.max_std_u, job.pue,
                                 job.power_demand, job.it_power, job.cooling_power])

    def get_edc_utilization_data(self):
        return self._get_edc_data('overall_std_u')

    def get_edc_power_demand_data(self):
        return self._get_edc_data('power_demand')

    def get_edc_it_power_data(self):
        return self._get_edc_data('it_power')

    def get_edc_cooling_power_data(self):
        return self._get_edc_data('cooling_power')

    def _get_edc_data(self, y_label):
        data = pd.read_csv(self.file_path, delimiter=';')
        time = data['time'].values.tolist()
        edc_id = data['edc_id'].values.tolist()
        y_values = data[y_label].values.tolist()
        return time, edc_id, y_values


class CSVRadioTransducer(RadioTransducer):
    def __init__(self, ul_file_path, dl_file_path):
        super().__init__()
        self.ul_file_path = ul_file_path
        self.dl_file_path = dl_file_path

    def process_ul_reports(self):
        self.write(self.ul_file_path, self.input_new_ul_mcs)

    def process_dl_reports(self):
        self.write(self.dl_file_path, self.input_new_dl_mcs)

    def write(self, path, port):
        with open(path, 'a') as file:
            writer = csv.writer(file, delimiter=';')
            for job in port.values:
                bandwidth = job.bandwidth
                efficiency = job.spectral_efficiency
                rate = bandwidth * efficiency
                writer.writerow([self._clock, job.node_from, job.node_to, job.mcs_id, efficiency, bandwidth, rate])

    def get_ul_radio_data(self):
        data = pd.read_csv(self.ul_file_path, delimiter=';')
        return self._get_data(data)

    def get_dl_radio_data(self):
        data = pd.read_csv(self.dl_file_path, delimiter=';')
        return self._get_data(data)

    @staticmethod
    def _get_data(data):
        time = data['time'].values.tolist()
        ue_id = data['ue_id'].values.tolist()
        ap_id = data['ap_id'].values.tolist()
        bandwidth = data['bandwidth'].values.tolist()
        rate = data['rate'].values.tolist()
        efficiency = data['efficiency'].values.tolist()
        return time, ue_id, ap_id, bandwidth, rate, efficiency


class CSVUEDelayTransducer(UEDelayTransducer):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def process_ue_delay_reports(self):
        with open(self.file_path, 'a') as file:
            writer = csv.writer(file, delimiter=';')
            for job in self.input_service_delay_report.values:
                writer.writerow([self._clock, job.ue_id, job.service_id, job.instant_generated, job.instant_sent,
                                 job.instant_received, job.delay, job.times_sent])

    def get_delay_data(self):
        data = pd.read_csv(self.file_path, delimiter=';')
        time = data['time'].values.tolist()
        ue_id = data['ue_id'].values.tolist()
        delay = data['delay'].values.tolist()
        return time, ue_id, delay


class CSVTransducerBuilder(TransducerBuilder):
    def __init__(self, scenario_config, **kwargs):
        super().__init__(scenario_config, **kwargs)

        dir_path = kwargs.get('dir_path', "./res/")
        # TODO meter funcionalidad de escribir la configuración del escenario en directorio base
        self.dir_path = dir_path if dir_path[-1] == '/' else dir_path + '/'
        self.edc_extension = kwargs.get('edc_extension', 'edc_report.csv')
        self.radio_ul_extension = kwargs.get('radio_ul_extension', 'radio_ul.csv')
        self.radio_dl_extension = kwargs.get('radio_dl_extension', 'radio_dl.csv')
        self.ue_delay_extension = kwargs.get('ue_delay_extension', 'ue_delay.csv')

        self.prepare_edc_transceiver()
        self.prepare_radio_transceiver()
        self.prepare_delay_transceiver()

    def prepare_edc_transceiver(self):
        file_path = self.dir_path + self.edc_extension
        if os.path.isfile(file_path):
            raise Exception("File already exists")
        with open(file_path, 'w') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(['time', 'edc_id', 'overall_std_u', 'max_std_u', 'PUE', 'power_demand',
                             'it_power', 'cooling_power'])

    def prepare_radio_transceiver(self):
        file_path = self.dir_path + self.radio_ul_extension
        if os.path.isfile(file_path):
            raise Exception("File already exists")
        with open(file_path, 'w') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(['time', 'ue_id', 'ap_id', 'mcs_index', 'efficiency', 'bandwidth', 'rate'])

        file_path = self.dir_path + self.radio_dl_extension
        if os.path.isfile(file_path):
            raise Exception("File already exists")
        with open(file_path, 'w') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(['time', 'ap_id', 'ue_id', 'mcs_index', 'efficiency', 'bandwidth', 'rate'])

    def prepare_delay_transceiver(self):
        file_path = self.dir_path + self.ue_delay_extension
        if os.path.isfile(file_path):
            raise Exception("File already exists")
        with open(file_path, 'w') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(['time', 'ue_id', 'service_id', 'generated', 'first_sent', 'processed', 'delay',
                             'times_sent'])

    def create_edc_transducer(self) -> CSVEdgeDataCenterTransducer:
        file_path = self.dir_path + self.edc_extension
        return CSVEdgeDataCenterTransducer(file_path)

    def create_radio_transducer(self) -> CSVRadioTransducer:
        ul_file_path = self.dir_path + self.radio_ul_extension
        dl_file_path = self.dir_path + self.radio_dl_extension
        return CSVRadioTransducer(ul_file_path, dl_file_path)

    def create_ue_delay_transducer(self) -> CSVUEDelayTransducer:
        file_path = self.dir_path + self.ue_delay_extension
        return CSVUEDelayTransducer(file_path)
