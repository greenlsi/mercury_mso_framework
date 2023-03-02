from __future__ import annotations
from math import floor
from mercury.config.edcs import ProcessingUnitConfig
from mercury.msg.edcs import ProcessingUnitReport
from mercury.msg.packet.app_packet.srv_packet import *
from typing import Any


class ProcessingUnit:

    PHASE_OFF = 'off'
    PHASE_ON = 'on'
    PHASE_TO_ON = 'to_on'
    PHASE_TO_OFF = 'to_off'

    def __init__(self, edc_id: str, pu_id: str, pu_config: ProcessingUnitConfig, edc_temp: float, standby: bool):
        from mercury.plugin import AbstractFactory, ProcessingUnitScheduler, \
            ProcessingUnitPowerModel, ProcessingUnitTemperatureModel
        self.update: bool = False
        self.last_t: float = 0
        self.next_t: float = inf
        self.standby: bool = standby
        self.phase: str = ProcessingUnit.PHASE_ON if standby else ProcessingUnit.PHASE_OFF
        self.edc_id: str = edc_id
        self.pu_id: str = pu_id
        self.pu_config: ProcessingUnitConfig = pu_config

        self.service_id: str | None = None
        self.max_parallel_tasks: int | None = None
        self.stream: bool | None = None
        self.sessions: dict[str, float] = dict()

        self.ready_open_sess: dict[str, OpenSessRequest] = dict()
        self.ready_close_sess: dict[str, CloseSessRequest] = dict()
        self.ready_srv_reqs: dict[tuple[str, str], SrvRequestProcess] = dict()
        self.running_processes: list[SrvRequestProcess] = list()

        self.scheduler: ProcessingUnitScheduler = AbstractFactory.create_edc_pu_scheduler(pu_config.scheduling_id, **pu_config.scheduling_config)
        power_config: dict[str, Any] = {**self.pu_config.default_power_config, 'max_parallel_tasks': 1}
        self.power_model: ProcessingUnitPowerModel = AbstractFactory.create_edc_pu_pwr(self.pu_config.default_power_id, **power_config)
        temp_config: dict[str, Any] = {**self.pu_config.temperature_config, 'edc_temp': edc_temp}
        self.temp_model: ProcessingUnitTemperatureModel = AbstractFactory.create_edc_pu_temp(self.pu_config.temperature_id, **temp_config)
        self.srv_power_models: dict[str, ProcessingUnitPowerModel] = dict()
        for service_id, srv_config in self.pu_config.srv_configs.items():
            power_config: dict[str, Any] = {**srv_config.power_config, 'max_parallel_tasks': srv_config.max_parallel_tasks}
            self.srv_power_models[service_id] = AbstractFactory.create_edc_pu_pwr(srv_config.power_id, **power_config)

    def __lt__(self, other: ProcessingUnit):
        return self.pu_id < other.pu_id

    @property
    def busy(self) -> bool:
        return self.standby or self.sessions or self.ready_srv_reqs

    @property
    def queue_time(self):  # TODO calculo el tiempo estimado hasta aceptar una tarea nueva
        time = 0
        if self.phase == ProcessingUnit.PHASE_OFF:
            time = self.pu_config.t_on
        elif self.phase == ProcessingUnit.PHASE_TO_ON:
            time = self.next_t - self.last_t
        elif self.phase == ProcessingUnit.PHASE_TO_OFF:
            time = self.next_t - self.last_t + self.pu_config.t_on
        if self.service_id is not None:
            if len(self.sessions) >= self.max_parallel_tasks:
                time = inf
        else:
            for process in self.ready_srv_reqs.values():
                time += self.pu_config.srv_configs[process.service_id].proc_t_model.expected_proc_time * (1 - process.progress)
        return time

    @property
    def status(self) -> bool:
        return self.phase != ProcessingUnit.PHASE_OFF

    @property
    def power(self) -> float:
        service_id = None
        n_tasks = 0
        if self.phase == ProcessingUnit.PHASE_ON:
            service_id = self.service_id
            if service_id is None and self.running_processes:
                service_id = self.running_processes[0].service_id
            n_tasks = len(self.running_processes) if not self.stream else len(self.sessions)
        return self.compute_power(self.status, service_id, n_tasks)

    def set_standby(self, standby: bool, instantaneous: bool = False):
        self.standby = standby
        self.update = True
        if instantaneous:
            self.phase = ProcessingUnit.PHASE_ON if self.busy else ProcessingUnit.PHASE_OFF

    def additional_tasks(self, service_id: str) -> int:  # TODO calculo cuantas tareas más de un servicio puedo aceptar
        srv_config = self.pu_config.srv_configs.get(service_id)
        if srv_config is not None:  # solo aceptamos tareas compatibles con la PU
            proc_t: float = srv_config.proc_t_model.expected_proc_time
            t_delta: float = srv_config.t_deadline - self.queue_time
            if t_delta >= proc_t:  # solo aceptamos tareas a las que podemos cumplir el deadline
                if srv_config.sess_required:  # solo podemos abrir sesiones en PUs vacías o con sesiones de la misma app
                    if self.service_id == service_id or self.service_id is None and not self.ready_srv_reqs:
                        return srv_config.max_parallel_tasks - len(self.sessions)  # solo depende de max_parallel_tasks
                elif self.service_id is None:  # solo podemos aceptar tareas BE si no hay sesiones abiertas
                    if proc_t > 0:
                        return srv_config.max_parallel_tasks * floor(t_delta / proc_t)  # valoramos que haya cola
                    return srv_config.max_parallel_tasks
        return 0

    def max_n_tasks(self, service_id: str) -> int:  # TODO si estuviese idle y vacío, ¿cuántas tareas puedo aceptar?
        srv_config = self.pu_config.srv_configs.get(service_id)
        if srv_config is None:
            return 0
        elif srv_config.sess_required or srv_config.proc_t_model.expected_proc_time <= 0:
            return srv_config.max_parallel_tasks
        return srv_config.max_parallel_tasks * floor(srv_config.t_deadline / srv_config.proc_t_model.expected_proc_time)

    def add_open_session(self, request: OpenSessRequest) -> OpenSessResponse | None:
        srv_config = self.pu_config.srv_configs.get(request.service_id)
        if srv_config is None:
            return OpenSessResponse(request, None, self.last_t, 'Bad PU mapping: it does not support this service')
        if self.service_id is None:
            if self.ready_srv_reqs:
                return OpenSessResponse(request, None, self.last_t, 'Bad PU mapping: PU has pending BE requests')
            else:
                self.service_id = request.service_id
                self.max_parallel_tasks = srv_config.max_parallel_tasks
                self.stream = srv_config.stream
                self.sessions[request.client_id] = self.last_t
                self.ready_open_sess[request.client_id] = request
                self.update = True
        elif self.service_id != request.service_id:
            return OpenSessResponse(request, None, self.last_t, 'Bad PU mapping: PU hosts sessions of different services')
        elif request.client_id in self.sessions:
            if request.client_id in self.ready_close_sess:
                return OpenSessResponse(request, None, self.last_t, 'Service session is being closed')
            elif request.client_id not in self.ready_open_sess:
                return OpenSessResponse(request, self.edc_id, self.last_t, 'Service session is already opened')
        elif len(self.sessions) >= self.max_parallel_tasks:
            return OpenSessResponse(request, None, self.last_t, 'Bad PU mapping: PU is full of service sessions')
        else:
            self.sessions[request.client_id] = self.last_t
            self.ready_open_sess[request.client_id] = request
            self.update = True

    def add_srv_request(self, request: SrvRequestProcess) -> SrvResponse | None:
        srv_config = self.pu_config.srv_configs.get(request.service_id)
        if srv_config is None:
            return SrvResponse(request.request, False, self.last_t, 'Bad PU mapping: it does not support this service')
        if srv_config.sess_required:
            if request.service_id == self.service_id and request.client_id in self.sessions:
                if request.client_id in self.ready_open_sess or request.client_id in self.ready_close_sess:
                    return SrvResponse(request.request, False, self.last_t, 'Session is being opened or removed')
                # elif (request.service_id, request.client_id) not in self.ready_srv_reqs:
                #     self.ready_srv_reqs[(request.service_id, request.client_id)] = request
                #     self.update = True
                # elif request != self.ready_srv_reqs[(request.service_id, request.client_id)]:
                #    return SrvResponse(request.request, False, self.last_t, 'PU is busy with a different request')
            else:
                return SrvResponse(request.request, False, self.last_t, 'Bad PU mapping: required session does not exist')
        elif self.service_id is not None:
            return SrvResponse(request.request, False, self.last_t, 'Bad PU mapping: PU hosts sessions of different services')
        # elif (request.service_id, request.client_id) not in self.ready_srv_reqs:
        if (request.service_id, request.client_id) not in self.ready_srv_reqs:
            self.ready_srv_reqs[(request.service_id, request.client_id)] = request
            self.update = True
        elif self.ready_srv_reqs[(request.service_id, request.client_id)] != request:
            return SrvResponse(request.request, False, self.last_t, 'PU is busy with a different request of the same client')

    def add_close_session(self, request: CloseSessRequest) -> CloseSessResponse | None:
        if self.service_id == request.service_id and request.client_id in self.sessions:
            if request.client_id in self.ready_open_sess or (request.service_id, request.client_id) in self.ready_srv_reqs:
                return CloseSessResponse(request, -1, self.last_t, 'Service session is busy and cannot be closed')
            elif request.client_id not in self.ready_close_sess:
                self.ready_close_sess[request.client_id] = request
                self.update = True
        else:
            return CloseSessResponse(request, 0, self.last_t, 'Service session does not exist')

    def preempt_srv_requests(self) -> tuple[list[SrvResponse], dict[tuple[str, str], SrvRequestProcess]] | None:  # TODO
        if self.service_id is None:
            _, srv_responses, _ = self._stop_execution()
            pending_processes = self.ready_srv_reqs
            self.ready_srv_reqs = dict()  # TODO ver lo de las sesiones
            return srv_responses, pending_processes

    def _stop_execution(self) -> list[SrvResponse]:
        processed: list[SrvResponse] = list()
        for process in self.running_processes:
            if process.stop(self.last_t) >= 1:
                self.ready_srv_reqs.pop((process.service_id, process.client_id))
                processed.append(SrvResponse(process.request, True, self.last_t))
        self.running_processes = list()
        self.next_t = inf
        return processed

    def _start_execution(self) -> tuple[list[OpenSessResponse], list[SrvResponse], list[CloseSessResponse]]:
        if self.phase != ProcessingUnit.PHASE_ON:
            return list(), list(), list()
        opened, closed = list(), list()
        processed = self._stop_execution()
        ta: float = inf
        service_id = self.service_id
        if service_id is not None:
            srv_config = self.pu_config.srv_configs[self.service_id]
            for request in self.ready_open_sess.values():
                opened.append(OpenSessResponse(request, self.edc_id, self.last_t))
            self.ready_open_sess = dict()
            n_tasks = len(self.ready_srv_reqs)
            for process in self.ready_srv_reqs.values():
                ta = min(process.start(self.last_t, srv_config.proc_t_model.proc_time(n_tasks)), ta)
                self.running_processes.append(process)
            for request in self.ready_close_sess.values():
                closed.append(CloseSessResponse(request, self.last_t - self.sessions.pop(request.client_id), self.last_t))
            self.ready_close_sess = dict()
            if not self.sessions:
                self.service_id = None
                self.max_parallel_tasks = None
                self.stream = None
        else:
            self.running_processes = self.scheduler.select_tasks(self.last_t, self.pu_config, self.ready_srv_reqs.values())
            n_tasks = len(self.running_processes)
            if n_tasks > 0:
                service_id = self.running_processes[0].service_id
                srv_config = self.pu_config.srv_configs.get(service_id)
                for process in self.running_processes:
                    ta = min(process.start(self.last_t, srv_config.proc_t_model.proc_time(n_tasks)), ta)
        self.next_t = self.last_t + ta
        return opened, processed, closed

    def compute_power(self, status: bool, srv_id: str | None, n_tasks: int) -> float:
        if not status:
            return 0
        elif srv_id is None:
            return self.power_model.compute_power(0)
        return self.srv_power_models[srv_id].compute_power(n_tasks)

    def compute_temperature(self, power: float) -> float:
        return self.temp_model.compute_temperature(power)

    def pu_report(self) -> ProcessingUnitReport:
        power = self.power
        temperature = self.compute_temperature(power)
        n_sessions = len(self.sessions) if self.service_id is not None else None
        return ProcessingUnitReport(self.edc_id, self.pu_id, self.pu_config.pu_id, self.status, self.service_id,
                                    n_sessions, self.max_parallel_tasks, self.queue_time, power, temperature)

    def update_t(self, t: float) -> tuple[list[OpenSessResponse], list[SrvResponse], list[CloseSessResponse]] | None:
        self.update = False
        if t < self.last_t:
            raise AssertionError('new time is less than last time')
        self.last_t = t
        if self.phase == ProcessingUnit.PHASE_OFF:
            if not self.busy:
                self.next_t = inf
            elif self.pu_config.t_on <= 0:
                self.phase = ProcessingUnit.PHASE_ON
            else:
                self.phase = ProcessingUnit.PHASE_TO_ON
                self.next_t = self.last_t + self.pu_config.t_on
        if self.phase == ProcessingUnit.PHASE_TO_ON:
            if self.last_t >= self.next_t:
                self.phase = ProcessingUnit.PHASE_ON
                self.next_t = inf if self.busy else self.last_t
        if self.phase == ProcessingUnit.PHASE_ON:
            res = self._start_execution()
            if not self.busy:
                if self.pu_config.t_off <= 0:
                    self.phase = ProcessingUnit.PHASE_OFF
                    self.next_t = inf
                else:
                    self.phase = ProcessingUnit.PHASE_TO_OFF
                    self.next_t = self.last_t + self.pu_config.t_off
            return res
        if self.phase == ProcessingUnit.PHASE_TO_OFF:
            if self.last_t >= self.next_t:
                if self.busy:
                    self.phase = ProcessingUnit.PHASE_TO_ON
                    self.next_t = self.last_t + self.pu_config.t_on
                else:
                    self.phase = ProcessingUnit.PHASE_OFF
                    self.next_t = inf
