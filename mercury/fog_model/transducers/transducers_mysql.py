import pymysql
import numpy as np
from datetime import datetime
from ..network import NetworkLinkReport
from .transducers import TransducerBuilder, UEDelayTransducer, RadioTransducer, EdgeDataCenterTransducer

EDC_TABLE = 'edc'
RACK_TABLE = 'rack_type'  # TODO
RACK_PER_EDC = 'rack_per_edc'  # TODO
PU_TABLE = 'pu_type'  # TODO
PU_PER_RACK = 'pu_per_rack'  # TODO
AP_TABLE = 'ap'
UE_TABLE = 'ue'
SRV_TABLE = 'service'
SRV_PER_UE_TABLE = 'service_per_ue'
SRV_PER_EDC_TABLE = 'service_per_edc'  # TODO

EDC_REPORT_TABLE = 'edc_report'
RACK_REPORT_TABLE = 'rack_report'  # TODO
PU_REPORT_TABLE = 'pu_report'  # TODO
RADIO_UL_REPORT_TABLE = 'radio_ul_report'
RADIO_DL_REPORT_TABLE = 'radio_dl_report'
UE_DELAY_TABLE = 'ue_delay'
UE_LOCATION_TABLE = 'ue_location'


class MySQLEdgeDataCenterTransducer(EdgeDataCenterTransducer):
    def __init__(self, host, port, user, password, db):
        super().__init__()
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db

    def process_edc_reports(self):
        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, db=self.db, password=self.password,
                                     charset='utf8mb4')
        try:
            for job in self.input_edc_report.values:
                sql = """REPLACE INTO {} (t, edc_id, utilization, max_utilization, pue, power_demand, it_power, cooling_power)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""".format(EDC_REPORT_TABLE)
                connection.cursor().execute(sql, (self._clock, job.edc_id, job.overall_std_u, job.max_std_u, job.pue,
                                                  job.power_demand, job.it_power, job.cooling_power))
            connection.commit()
        finally:
            connection.close()

    def get_edc_utilization_data(self):
        return self._get_data('utilization')

    def get_edc_power_demand_data(self):
        return self._get_data('power_demand')

    def get_edc_it_power_data(self):
        return self._get_data('it_power')

    def get_edc_cooling_power_data(self):
        return self._get_data('cooling_power')

    def _get_data(self, column_name):
        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, db=self.db, password=self.password,
                                     charset='utf8mb4')
        try:
            sql = "SELECT t, edc_id, {} FROM {} ORDER BY t".format(column_name, EDC_REPORT_TABLE)
            cur = connection.cursor()
            cur.execute(sql)
            data = np.array(cur.fetchall())
            time = data[:, 0].astype(np.float).tolist()
            edc_id = data[:, 1].tolist()
            values = data[:, 2].astype(np.float).tolist()
            return time, edc_id, values
        finally:
            connection.close()


class MySQLRadioTransducer(RadioTransducer):
    def __init__(self, host, port, user, password, db):
        super().__init__()
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db

    def process_ul_reports(self):
        self.write_rows(RADIO_UL_REPORT_TABLE, 'ue_id', 'ap_id', self.input_new_ul_mcs)

    def process_dl_reports(self):
        self.write_rows(RADIO_DL_REPORT_TABLE, 'ap_id', 'ue_id', self.input_new_dl_mcs)

    def write_rows(self, table, node_from, node_to, port):
        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, db=self.db, password=self.password,
                                     charset='utf8mb4')
        try:
            for job in port.values:
                assert isinstance(job, NetworkLinkReport)
                bandwidth = job.bandwidth
                efficiency = job.spectral_efficiency
                rate = bandwidth * efficiency
                sql = """REPLACE INTO {} (t, {}, {}, mcs_id, efficiency, bandwidth, rate)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)""".format(table, node_from, node_to)
                connection.cursor().execute(sql, (self._clock, job.node_from, job.node_to, str(job.mcs_id), efficiency,
                                                  bandwidth, rate))
            connection.commit()
        finally:
            connection.close()

    def get_ul_radio_data(self):
        return self._get_radio_data(RADIO_UL_REPORT_TABLE)

    def get_dl_radio_data(self):
        return self._get_radio_data(RADIO_DL_REPORT_TABLE)

    def _get_radio_data(self, table_name):
        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, db=self.db, password=self.password,
                                     charset='utf8mb4')
        try:
            sql = "SELECT t, ue_id, ap_id, bandwidth, rate, efficiency FROM {} ORDER BY t".format(table_name)
            cur = connection.cursor()
            cur.execute(sql)
            data = np.array(cur.fetchall())
            time = data[:, 0].astype(np.float).tolist()
            ue_id = data[:, 1].tolist()
            ap_id = data[:, 2].tolist()
            bandwidth = data[:, 3].astype(np.float).tolist()
            rate = data[:, 4].astype(np.float).tolist()
            efficiency = data[:, 5].astype(np.float).tolist()
            return time, ue_id, ap_id, bandwidth, rate, efficiency
        finally:
            connection.close()


class MySQLUEDelayTransducer(UEDelayTransducer):
    def __init__(self, host, port, user, password, db):
        super().__init__()
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db

    def process_ue_delay_reports(self):
        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, db=self.db, password=self.password,
                                     charset='utf8mb4')
        try:
            for job in self.input_service_delay_report.values:
                sql = """REPLACE INTO {} (t, ue_id, service_id, t_generated, t_first_sent, t_processed, delay,
                            times_sent) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""".format(UE_DELAY_TABLE)
                connection.cursor().execute(sql, (self._clock, job.ue_id, job.service_id, job.instant_generated,
                                                  job.instant_sent, job.instant_received, job.delay, job.times_sent))
            connection.commit()
        finally:
            connection.close()

    def get_delay_data(self):
        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, db=self.db, password=self.password,
                                     charset='utf8mb4')
        try:
            sql = "SELECT t, ue_id, delay FROM {} ORDER BY t".format(UE_DELAY_TABLE)
            cur = connection.cursor()
            cur.execute(sql)
            data = np.array(cur.fetchall())
            time = data[:, 0].astype(np.float).tolist()
            ue_id = data[:, 1].tolist()
            delay = data[:, 2].astype(np.float).tolist()
            return time, ue_id, delay
        finally:
            connection.close()


class MySQLTransducerBuilder(TransducerBuilder):
    def __init__(self, scenario_config, **kwargs):
        super().__init__(scenario_config, **kwargs)
        self.description = kwargs.get('description', 'Mercury simulation launched on ' + str(datetime.now()))
        self.host = kwargs.get('host', 'localhost')
        self.port = kwargs.get('port', 3306)
        self.user = kwargs.get('user', 'root')
        self.password = kwargs.get('password', None)
        self.db = kwargs.get('db', 'mercury')

        pymysql.converters.encoders[np.float64] = pymysql.converters.escape_float
        pymysql.converters.conversions = pymysql.converters.encoders.copy()
        pymysql.converters.conversions.update(pymysql.converters.decoders)

        self.create_db()
        self.create_config_tables()
        self.fill_config_tables(scenario_config)
        self.create_simulation_tables()

    def create_db(self):
        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, password=self.password,
                                     charset='utf8mb4')
        # Create database
        sql = "CREATE DATABASE {}".format(self.db)
        connection.cursor().execute(sql)

        connection.commit()
        connection.close()

    def create_config_tables(self):
        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, db=self.db, password=self.password,
                                     charset='utf8mb4')
        try:
            # Create table for EDCs
            sql = """CREATE TABLE {} (`id` VARCHAR(128) NOT NULL, location_x DOUBLE, location_y DOUBLE,
                        PRIMARY KEY (`id`))""".format(EDC_TABLE)
            connection.cursor().execute(sql)
            # Create table for APs
            sql = """CREATE TABLE {} (`id` VARCHAR(128), location_x DOUBLE,
                     location_y DOUBLE, PRIMARY KEY (`id`))""".format(AP_TABLE)
            connection.cursor().execute(sql)
            # Create table for Services
            sql = """CREATE TABLE {} (`id` VARCHAR(128), utilization DOUBLE, header INT, generation_rate DOUBLE,
                        packaging_time DOUBLE, min_closed_t DOUBLE, min_open_t DOUBLE, service_timeout DOUBLE,
                        window_size INT, PRIMARY KEY (`id`))""".format(SRV_TABLE)
            connection.cursor().execute(sql)
            # Create table for UEs
            sql = 'CREATE TABLE {} (`id` VARCHAR(128), PRIMARY KEY (`id`))'.format(UE_TABLE)
            connection.cursor().execute(sql)
            # Create table for Services by UE
            sql = """CREATE TABLE {} (`id` INT NOT NULL AUTO_INCREMENT, ue_id VARCHAR(128), service_id VARCHAR(128),
                        PRIMARY KEY (`id`), UNIQUE KEY (ue_id, service_id), FOREIGN KEY (ue_id) REFERENCES {} (`id`),
                        FOREIGN KEY (service_id) REFERENCES {} (`id`))""".format(SRV_PER_UE_TABLE, UE_TABLE, SRV_TABLE)
            connection.cursor().execute(sql)
            connection.commit()
        finally:
            connection.close()

    def fill_config_tables(self, scenario_config):
        edcs = scenario_config.get('edcs', list())
        aps = scenario_config.get('aps', list())
        services = scenario_config.get('services', list())
        ues = scenario_config.get('ues', list())

        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, db=self.db,
                                     password=self.password, charset='utf8mb4')
        try:
            for edc_config in edcs:
                edc_id = edc_config.edc_id
                edc_location = edc_config.edc_location
                # TODO ¿información de racks, PUs, ... en JSON?
                sql = """INSERT INTO {} (`id`, location_x, location_y) VALUES (%s, %s, %s)""".format(EDC_TABLE)
                connection.cursor().execute(sql, (edc_id, edc_location[0], edc_location[1]))

            for ap_config in aps:
                ap_id = ap_config.ap_id
                ap_location = ap_config.ap_location
                # TODO ¿información de potencia de antenas etc?
                sql = "INSERT INTO {} (`id`, location_x, location_y) VALUES (%s, %s, %s)".format(AP_TABLE)
                connection.cursor().execute(sql, (ap_id, ap_location[0], ap_location[1]))

            # Create table for services and add services
            for service in services:
                service_id = service.service_id
                utilization = service.service_u
                header = service.header
                generation_rate = service.generation_rate
                packaging_time = service.packaging_time
                min_closed_t = service.min_closed_t
                min_open_t = service.min_open_t
                service_timeout = service.service_timeout
                window_size = service.window_size
                sql = """INSERT INTO {} (`id`, utilization, header, generation_rate, packaging_time, min_closed_t,
                        min_open_t, service_timeout, window_size)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""".format(SRV_TABLE)
                connection.cursor().execute(sql, (service_id, utilization, header, generation_rate,
                                                  packaging_time, min_closed_t, min_open_t, service_timeout,
                                                  window_size))

            for ue_config in ues:
                ue_id = ue_config.ue_id
                srv_list = ue_config.service_config_list
                sql = "INSERT INTO {} (`id`) VALUES (%s)".format(UE_TABLE)
                connection.cursor().execute(sql, (ue_id,))
                for service in srv_list:
                    service_id = service.service_id
                    sql = "INSERT INTO {} (ue_id, service_id) VALUES (%s, %s)".format(SRV_PER_UE_TABLE)
                    connection.cursor().execute(sql, (ue_id, service_id))

            connection.commit()
        finally:
            connection.close()

    def create_simulation_tables(self):
        connection = pymysql.connect(host=self.host, port=self.port, user=self.user, db=self.db, password=self.password,
                                     charset='utf8mb4')
        try:
            sql = """CREATE TABLE {} (`id` INT NOT NULL AUTO_INCREMENT, t DOUBLE, edc_id VARCHAR(128),
                        utilization DOUBLE, max_utilization DOUBLE, pue FLOAT, power_demand DOUBLE, it_power DOUBLE,
                        cooling_power DOUBLE, PRIMARY  KEY (`id`),
                        UNIQUE KEY (t, edc_id), FOREIGN KEY (edc_id)
                        REFERENCES {} (`id`))""".format(EDC_REPORT_TABLE, EDC_TABLE)
            connection.cursor().execute(sql)
            # TODO ¿tabla de rack, PUs...? -> son relaciones m:n

            sql = """CREATE TABLE {} (`id` INT NOT NULL AUTO_INCREMENT, t DOUBLE, ap_id VARCHAR(128),
                        ue_id VARCHAR(128), mcs_id VARCHAR(128), efficiency DOUBLE, bandwidth DOUBLE, rate DOUBLE,
                          PRIMARY  KEY (`id`), UNIQUE KEY (t, ap_id, ue_id), FOREIGN KEY (ap_id) REFERENCES {} (`id`),
                          FOREIGN KEY (ue_id) REFERENCES {} (`id`))""".format(RADIO_DL_REPORT_TABLE, AP_TABLE, UE_TABLE)
            connection.cursor().execute(sql)

            sql = """CREATE TABLE {} (`id` INT NOT NULL AUTO_INCREMENT, t DOUBLE, ue_id VARCHAR(128),
                        ap_id VARCHAR(128), mcs_id VARCHAR(128), efficiency DOUBLE, bandwidth DOUBLE, rate DOUBLE,
                        PRIMARY  KEY (`id`), UNIQUE KEY (t, ue_id, ap_id), FOREIGN KEY (ap_id) REFERENCES {} (`id`),
                        FOREIGN KEY (ue_id) REFERENCES {} (`id`))""".format(RADIO_UL_REPORT_TABLE, AP_TABLE, UE_TABLE)
            connection.cursor().execute(sql)

            sql = """CREATE TABLE {} (`id` INT NOT NULL AUTO_INCREMENT, t DOUBLE, ue_id VARCHAR(128),
                        service_id VARCHAR(128), t_generated DOUBLE, t_first_sent DOUBLE, t_processed DOUBLE,
                        delay DOUBLE, times_sent INT, PRIMARY KEY (`id`), UNIQUE KEY (t, ue_id, service_id),
                        FOREIGN KEY (ue_id) REFERENCES {} (`id`), FOREIGN KEY (service_id) REFERENCES {} (`id`))
                          """.format(UE_DELAY_TABLE, UE_TABLE, SRV_TABLE)
            connection.cursor().execute(sql)

            sql = """CREATE TABLE {} (`id` INT NOT NULL AUTO_INCREMENT, t DOUBLE, ue_id VARCHAR(128), location_x DOUBLE,
                        location_y DOUBLE, PRIMARY KEY (`id`), UNIQUE KEY (t, ue_id),
                        FOREIGN KEY (ue_id) REFERENCES {} (`id`))""".format(UE_LOCATION_TABLE, UE_TABLE)
            connection.cursor().execute(sql)
            connection.commit()
        finally:
            connection.close()

    def create_edc_transducer(self) -> MySQLEdgeDataCenterTransducer:
        return MySQLEdgeDataCenterTransducer(self.host, self.port, self.user, self.password, self.db)

    def create_radio_transducer(self) -> MySQLRadioTransducer:
        return MySQLRadioTransducer(self.host, self.port, self.user, self.password, self.db)

    def create_ue_delay_transducer(self) -> MySQLUEDelayTransducer:
        return MySQLUEDelayTransducer(self.host, self.port, self.user, self.password, self.db)
