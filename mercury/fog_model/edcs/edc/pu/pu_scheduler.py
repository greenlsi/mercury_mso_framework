from math import inf
from mercury.config.edcs import ProcessingUnitConfig
from mercury.utils.process import ProcessingUnitProcess
from mercury.msg.network.packet.app_layer.service import ServiceRequest, \
    StartSessionRequest, StopSessionRequest, ServiceResponse
from typing import Dict, Generator, List, NoReturn, Optional, Set, Tuple


class ProcessingUnitScheduler:
    def __init__(self, pu_config: ProcessingUnitConfig):
        from mercury.plugin import AbstractFactory, SchedulingAlgorithm
        self.pu_config: ProcessingUnitConfig = pu_config
        self.algorithm: SchedulingAlgorithm = AbstractFactory.create_scheduling_algorithm(pu_config.scheduling_name,
                                                                                          **pu_config.scheduling_config)
        self.reserved_u: float = 0
        self.last_t: float = 0
        self.next_t: float = inf
        self.last_u: float = 0
        self.last_running_processes: Dict[ProcessingUnitProcess, float] = dict()

        self.ready_tasks: Dict[ServiceRequest, ProcessingUnitProcess] = dict()
        self.ready_to_start_sessions: Dict[Tuple[str, str], ProcessingUnitProcess] = dict()
        self.ready_session_requests: Dict[Tuple[str, str], Set[ServiceRequest]] = dict()
        self.ready_session_tasks: Dict[Tuple[str, str], List[ProcessingUnitProcess]] = dict()
        self.ready_to_stop_sessions: Dict[Tuple[str, str], ProcessingUnitProcess] = dict()

    @property
    def busy(self) -> bool:
        return any((self.ready_tasks, self.ready_to_start_sessions,
                    self.ready_session_requests, self.ready_to_stop_sessions))

    @property
    def ready_processes(self) -> Generator[ProcessingUnitProcess, None, None]:
        for process in self.ready_to_start_sessions.values():
            yield process
        for processes in self.ready_session_tasks.values():
            for process in processes:
                yield process
        for process in self.ready_to_stop_sessions.values():
            yield process
        for process in self.ready_tasks.values():
            yield process

    def change_algorithm(self, t: float, algorithm_key: str, **kwargs):  # TODO check how to implement this
        from mercury.plugin import AbstractFactory
        self._assert_not_running()
        self._advance_last_time(t)
        self.algorithm = AbstractFactory.create_scheduling_algorithm(algorithm_key, **kwargs)

    def start_session(self, request: StartSessionRequest, t: float) -> Optional[ServiceResponse]:
        self._assert_not_running()
        self._advance_last_time(t)
        service_id: str = request.service_id
        client_id: str = request.client_id
        if not self.session_starting(service_id, client_id):
            if self.session_started(service_id, client_id):
                return ServiceResponse(request, True, 'session already created')
            elif self.session_stopping(service_id, client_id):
                return ServiceResponse(request, False, 'session being removed')
            srv_config = self.pu_config.services[service_id]
            if self.reserved_u + srv_config.max_u > 100:
                return ServiceResponse(request, False, 'not enough available resources')
            self.reserved_u += srv_config.max_u
            process = ProcessingUnitProcess(request, srv_config.u_busy, srv_config.t_start, self.last_t)
            self.ready_to_start_sessions[(service_id, client_id)] = process

    def execute_task(self, request: ServiceRequest, t: float) -> Optional[ServiceResponse]:
        self._assert_not_running()
        self._advance_last_time(t)
        srv_config = self.pu_config.services[request.service_id]
        if request.session:
            if not self.session_started(request.service_id, request.client_id):
                return ServiceResponse(request, False, 'session not found')
            elif request not in self.ready_session_requests[(request.service_id, request.client_id)]:
                process = ProcessingUnitProcess(request, srv_config.u_busy, srv_config.t_process, self.last_t)
                self.ready_session_requests[(request.service_id, request.client_id)].add(request)
                self.ready_session_tasks[(request.service_id, request.client_id)].append(process)
        elif request not in self.ready_tasks:
            process = ProcessingUnitProcess(request, srv_config.u_busy, srv_config.t_total, self.last_t)
            self.ready_tasks[request] = process

    def stop_session(self, request: StopSessionRequest, t: float) -> Optional[ServiceResponse]:
        self._assert_not_running()
        self._advance_last_time(t)
        service_id: str = request.service_id
        client_id: str = request.client_id
        if self.session_starting(service_id, client_id):
            return ServiceResponse(request, False, 'session still being created')
        elif not self.session_started(service_id, client_id):
            return ServiceResponse(request, True, 'session not found')
        elif self.session_busy(service_id, client_id):
            return ServiceResponse(request, False, 'session busy')
        elif not self.session_stopping(service_id, client_id):
            self.ready_session_requests.pop((service_id, client_id))
            self.ready_session_tasks.pop((service_id, client_id))
            srv_conf = self.pu_config.services[request.service_id]
            process = ProcessingUnitProcess(request, srv_conf.u_busy, srv_conf.t_stop, self.last_t)
            self.ready_to_stop_sessions[(service_id, client_id)] = process

    def start_execution(self, t: float) -> Dict[ServiceRequest, Tuple[float, float]]:
        self._assert_not_running()
        self._advance_last_time(t)
        ta = inf
        new_u = 0
        new_running_processes = dict()
        res: Dict[ServiceRequest, Tuple[float, float]] = {p.request: (0, p.progress) for p in self.ready_processes}
        for process in self.ready_to_start_sessions.values():
            ta = min(process.start(self.last_t, process.max_u), ta)
            new_u += process.max_u
            new_running_processes[process] = process.max_u
            res[process.request] = process.max_u, process.progress
        for (service_id, _), tasks in self.ready_session_tasks.items():
            if tasks:
                for process in self.algorithm.schedule_tasks(tasks, tasks[0].max_u, t):
                    ta = min(process.start(self.last_t, process.max_u), ta)
                    new_u += process.utilization
                    new_running_processes[process] = process.utilization
                    res[process.request] = process.utilization, process.progress
            else:
                new_u += self.pu_config.services[service_id].u_idle
        for process in self.ready_to_stop_sessions.values():
            ta = min(process.start(self.last_t, process.max_u), ta)
            new_u += process.max_u
            new_running_processes[process] = process.max_u
            res[process.request] = process.max_u, process.progress
        # TODO check this
        # for process in self.algorithm.schedule_tasks(self.ready_tasks.values(), 100 - self.reserved_u, self.last_t):
        for process in self.algorithm.schedule_tasks(self.ready_tasks.values(), 100 - new_u, self.last_t):
            ta = min(process.start(self.last_t, process.max_u), ta)
            new_u += process.utilization
            new_running_processes[process] = process.utilization
            res[process.request] = process.utilization, process.progress
        if new_u > 100:
            raise AssertionError('PU scheduler assigned more resources than available')
        self.next_t = self.last_t + ta
        self.last_u = new_u
        self.last_running_processes = new_running_processes
        return res

    def stop_execution(self, t: float) -> Tuple[List[ServiceResponse], List[ServiceResponse], List[ServiceResponse]]:
        self._advance_last_time(t)
        sessions_started: List[ServiceResponse] = list()
        tasks_executed: List[ServiceResponse] = list()
        sessions_stopped: List[ServiceResponse] = list()
        for process in self.last_running_processes.keys():  # Stop all running processes
            if process.stop(self.last_t) >= 100:  # Note down finished processes to notify their execution
                request = process.request
                service_id, client_id, packet_id = request.info
                if isinstance(request, StartSessionRequest):
                    self.ready_to_start_sessions.pop((service_id, client_id))
                    self.ready_session_requests[(service_id, client_id)] = set()
                    self.ready_session_tasks[(service_id, client_id)] = list()
                    sessions_started.append(ServiceResponse(request, True))
                elif isinstance(request, StopSessionRequest):
                    self.ready_to_stop_sessions.pop((service_id, client_id))
                    self.reserved_u -= self.pu_config.services[request.service_id].max_u
                    sessions_stopped.append(ServiceResponse(request, True))
                else:
                    if process.request.session:
                        self.ready_session_requests[(service_id, client_id)].remove(process.request)
                        self.ready_session_tasks[(service_id, client_id)].remove(process)
                    else:
                        self.ready_tasks.pop(process.request)
                    tasks_executed.append(ServiceResponse(request, True))
        self.next_t = inf
        self.last_u = 0
        self.last_running_processes = dict()
        return sessions_started, tasks_executed, sessions_stopped

    def session_starting(self, service_id: str, client_id: str) -> bool:
        return (service_id, client_id) in self.ready_to_start_sessions

    def session_started(self, service_id: str, client_id: str) -> bool:
        return (service_id, client_id) in self.ready_session_tasks

    def session_busy(self, service_id: str, client_id: str) -> bool:
        return bool(self.ready_session_tasks[(service_id, client_id)])

    def session_stopping(self, service_id: str, client_id: str) -> bool:
        return (service_id, client_id) in self.ready_to_stop_sessions

    def _assert_not_running(self) -> NoReturn:
        """:raises AssertionError: if any process is currently running."""
        if self.last_running_processes:
            raise AssertionError('Scheduler cannot be changed if processes are running.')

    def _advance_last_time(self, t: float) -> NoReturn:
        if t < self.last_t:
            raise AssertionError('new time is less than last time.')
        self.last_t = t
