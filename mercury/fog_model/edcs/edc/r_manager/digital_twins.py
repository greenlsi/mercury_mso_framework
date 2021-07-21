from typing import Dict, Optional, Set, Tuple
from mercury.config.edcs import ProcessingUnitConfig
from mercury.msg.edcs import ProcessingUnitReport
from mercury.msg.network.packet.app_layer.service import ServiceRequest


class ProcessingUnitDigitalTwin:
    def __init__(self, edc_id: str, pu_id: str, pu_config: ProcessingUnitConfig, env_temp: float = 298):
        """
        Processing Unit Digital Twin.
        :param edc_id: ID of the Edge Data Center that contains the PU.
        :param pu_id: ID of the PU.
        :param pu_config: Configuration parameters of the PU.
        :param env_temp: Environment temperature.
        """
        from mercury.plugin import AbstractFactory, SchedulingAlgorithm, \
            ProcessingUnitPowerModel, ProcessingUnitTemperatureModel

        self.edc_id: str = edc_id
        self.pu_id: str = pu_id
        self.env_temp: float = env_temp
        self.pu_config: ProcessingUnitConfig = pu_config
        self.latest_report: Optional[ProcessingUnitReport] = None

        self.hot_standby: bool = False
        self.reserved_u: float = 0
        self.approx_power: float = 0
        self.approx_temp: float = env_temp

        self.starting_sessions: Dict[str, Set[str]] = dict()
        self.started_sessions: Dict[str, Set[str]] = dict()
        self.stopping_sessions: Dict[str, Set[str]] = dict()
        self.session_requests: Dict[str, Dict[str, Set[ServiceRequest]]] = dict()

        self.power_model: Optional[ProcessingUnitPowerModel] = None
        power_model_name = pu_config.power_name
        power_model_config = pu_config.power_config
        if power_model_name is not None:
            self.power_model = AbstractFactory.create_edc_pu_pwr(power_model_name, **power_model_config)

        self.temp_model: Optional[ProcessingUnitTemperatureModel] = None
        temp_model_name = pu_config.temp_name
        temp_model_config = pu_config.temp_config
        if temp_model_name is not None:
            self.temp_model = AbstractFactory.create_edc_pu_temp(temp_model_name, **temp_model_config)

        # TODO these are for future steps
        self.utilization: float = 0
        self.power: float = 0
        self.temp: float = env_temp
        self.resource_share: Dict[str, Dict[ServiceRequest, Tuple[float, float]]] = dict()
        self.scheduler: SchedulingAlgorithm = AbstractFactory.create_scheduling_algorithm(pu_config.scheduling_name,
                                                                                          **pu_config.scheduling_config)

    def __lt__(self, other):
        """PU Digital Twins are sorted depending on their reserved u"""
        return self.reserved_u < other.reserved_u

    @property
    def status(self) -> bool:
        """True if the PU is powered on"""
        return self.hot_standby or any((self.starting_sessions, self.started_sessions, self.stopping_sessions))

    def n_sessions(self, service_id: str) -> int:
        res = 0
        for sessions in (self.starting_sessions, self.started_sessions, self.stopping_sessions):
            res += len(sessions.get(service_id, set()))
        return res

    def predict_dvfs_index(self, status: bool, u: float) -> float:
        """
        Makes a prediction of the DVFS configuration that the PU would use for a given status and utilization
        :param status: status under study (True if powered on)
        :param u: utilization (in %)
        :return: DVFS index
        """
        return 0 if not status else min(i for i in self.pu_config.dvfs_table if i >= u)

    def predict_power(self, status: bool, u: float) -> float:
        """
        Makes a prediction of the PU power consumption for a given status and utilization
        :param status: status under study (True if powered on)
        :param u: utilization (in %)
        :return: Estimated power consumption (in Watts)
        """
        if self.power_model is None:
            return 0
        dvfs_config = self.pu_config.dvfs_table.get(self.predict_dvfs_index(status, u), None)
        return self.power_model.compute_power(status, u, dvfs_config)

    def predict_temperature(self, status: bool, u: float) -> float:
        """
        Makes a prediction of the PU temperature for a given status and utilization
        :param status: status under study (True if powered on)
        :param u: utilization (in %)
        :return: Estimated temperature (in Kelvin)
        """
        if self.temp_model is None:
            return self.env_temp
        dvfs_config = self.pu_config.dvfs_table.get(self.predict_dvfs_index(status, u), None)
        return self.temp_model.compute_temperature(status, u, dvfs_config)

    @staticmethod
    def clean_session_addition(target: Dict[str, Set[str]], service_id: str, client_id: str):
        if service_id not in target:
            target[service_id] = set()
        target[service_id].add(client_id)

    @staticmethod
    def clean_session_removal(target: Dict[str, Set[str]], service_id: str, client_id: str):
        if service_id not in target or client_id not in target[service_id]:
            raise AssertionError('Unable to remove non-existent session')
        target[service_id].remove(client_id)
        if not target[service_id]:
            target.pop(service_id)

    def session_exists(self, service_id: str, client_id: str) -> bool:
        for target in (self.starting_sessions, self.started_sessions, self.stopping_sessions):
            if client_id in target.get(service_id, set()):
                return True
        return False

    def start_starting_session(self, service_id: str, client_id: str):
        if self.session_exists(service_id, client_id):
            raise AssertionError('Session already exists')
        utilization = self.pu_config.services[service_id].max_u
        if self.reserved_u + utilization > 100:
            raise AssertionError('Unable to reserve more resources than available')
        self.clean_session_addition(self.starting_sessions, service_id, client_id)
        self.reserved_u += utilization
        self._recompute_approx_power_and_temp()

    def finish_starting_session(self, service_id: str, client_id: str, result: bool):
        self.clean_session_removal(self.starting_sessions, service_id, client_id)
        if result:
            self._add_to_started(service_id, client_id)
        else:
            self.reserved_u -= self.pu_config.services[service_id].max_u
            self._recompute_approx_power_and_temp()

    def start_processing_task(self, request: ServiceRequest):
        if request.session:
            service_id, client_id, _ = request.info
            try:
                self.session_requests[service_id][client_id].add(request)
            except KeyError:
                raise KeyError('session not found')
        else:
            raise NotImplementedError('this functionality is not available yet')

    def request_being_processed(self, request: ServiceRequest) -> bool:
        if request.session:
            return request in self.session_requests.get(request.service_id, dict()).get(request.client_id, set())
        else:
            raise NotImplementedError('this functionality is not available yet')

    def finish_processing_task(self, request: ServiceRequest):
        if request.session:
            service_id, client_id, _ = request.info
            try:
                self.session_requests[service_id][client_id].remove(request)
            except KeyError:
                raise AssertionError('session and/or request not found')
        else:
            raise NotImplementedError('this functionality is not available yet')

    def start_stopping_session(self, service_id: str, client_id: str):
        if self.session_requests[service_id][client_id]:
            raise AssertionError('session is busy and cannot be stopped')
        self._remove_from_started(service_id, client_id)
        self.clean_session_addition(self.stopping_sessions, service_id, client_id)

    def finish_stopping_session(self, service_id: str, client_id: str, result: bool):
        self.clean_session_removal(self.stopping_sessions, service_id, client_id)
        if result:
            self.reserved_u -= self.pu_config.services[service_id].max_u
            self._recompute_approx_power_and_temp()
        else:
            self._add_to_started(service_id, client_id)

    def set_hot_standby(self, hot_standby: bool):
        """
        Changes the digital twin hot standby configuration and recomputes power consumption and temperature
        :param hot_standby: new eventual hot standby mode
        """
        self.hot_standby = hot_standby
        self._recompute_approx_power_and_temp()

    def reset(self):
        self.latest_report = None
        self.hot_standby = False
        self.reserved_u = 0
        self.approx_power = 0
        self.approx_temp = self.env_temp
        self.starting_sessions = dict()
        self.started_sessions = dict()
        self.stopping_sessions = dict()
        self.session_requests = dict()
        self.power = 0
        self.temp: float = self.env_temp
        self.utilization = 0
        self.resource_share = dict()
        self._recompute_approx_power_and_temp()

    def _recompute_approx_power_and_temp(self):
        """Recomputes power consumption and temperature"""
        self.approx_power = self.predict_power(self.status, self.reserved_u)
        self.approx_temp = self.predict_temperature(self.status, self.reserved_u)
        # TODO
        self.power = self.approx_power
        self.temp = self.approx_temp

    def _add_to_started(self, service_id: str, client_id: str):
        self.clean_session_addition(self.started_sessions, service_id, client_id)
        if service_id not in self.session_requests:
            self.session_requests[service_id] = dict()
        self.session_requests[service_id][client_id] = set()

    def _remove_from_started(self, service_id: str, client_id: str):
        if self.session_requests[service_id][client_id]:
            raise AssertionError('session is busy and cannot be removed')
        self.session_requests[service_id].pop(client_id)
        if not self.session_requests[service_id]:
            self.session_requests.pop(service_id)
        self.clean_session_removal(self.started_sessions, service_id, client_id)
