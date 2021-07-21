from mercury.config.edcs import EdgeDataCenterConfig
from mercury.msg.edcs import *
from mercury.msg.network.packet.app_layer.service import ServiceRequest, \
    StartSessionRequest, StopSessionRequest, ServiceResponse
from typing import Dict, List, Optional, Union
from .cooler import EdgeDataCenterCooler
from .digital_twins import ProcessingUnitDigitalTwin


class EdgeDataCenterDispatcher:
    def __init__(self, edc_config: EdgeDataCenterConfig):

        from mercury.plugin import MappingStrategy, HotStandbyStrategy

        self.edc_config = edc_config
        r_manager_config = self.edc_config.r_manager_config

        self.explore_hot_standby: bool = False
        self._standby_name: Optional[str] = None
        self.hot_standby: Optional[HotStandbyStrategy] = None
        self.new_hot_standby(r_manager_config.hot_standby_name, **r_manager_config.hot_standby_config)

        self.mapper: Optional[MappingStrategy] = None
        self.new_mapper(r_manager_config.mapping_name, **r_manager_config.mapping_config)

        self.pu_twins: Dict[str, ProcessingUnitDigitalTwin] = dict()
        for pu_id, pu_config in edc_config.pus_config.items():
            self.pu_twins[pu_id] = ProcessingUnitDigitalTwin(edc_config.edc_id, pu_id, pu_config, edc_config.env_temp)

        self.cooler: Optional[EdgeDataCenterCooler] = None
        if edc_config.cooler_config is not None:
            self.cooler = EdgeDataCenterCooler(edc_config.edc_id, edc_config.cooler_config, edc_config.env_temp)

        self.starting: Dict[str, Dict[str, ProcessingUnitDigitalTwin]] = dict()
        self.started: Dict[str, Dict[str, ProcessingUnitDigitalTwin]] = dict()
        self.stopping: Dict[str, Dict[str, ProcessingUnitDigitalTwin]] = dict()

    def new_mapper(self, name: str, **kwargs):
        from mercury.plugin import AbstractFactory
        self.mapper = AbstractFactory.create_edc_mapping(name, edc_config=self.edc_config, **kwargs)
        self.explore_hot_standby = True

    def new_hot_standby(self, name: Optional[str], **kwargs):
        from mercury.plugin import AbstractFactory
        if name is None:
            self.hot_standby = None
        elif name == self._standby_name:
            self.hot_standby.update_hot_standby(**kwargs)
        else:
            self.hot_standby = AbstractFactory.create_edc_hot_standby(name, edc_config=self.edc_config, **kwargs)
        self._standby_name = name
        self.explore_hot_standby = True

    def explore_hot_standby_changes(self, instantaneous: bool = False) -> List[ProcessingUnitHotStandBy]:
        res: List[ProcessingUnitHotStandBy] = list()
        if self.explore_hot_standby:
            if self.hot_standby is None:
                standby_pus = {pu_id: False for pu_id in self.pu_twins}
            else:
                standby_pus = self.hot_standby.explore_hot_standby(self.mapper, self.starting,
                                                                   self.started, self.stopping)
            for pu_id, standby in standby_pus.items():
                if standby != self.pu_twins[pu_id].hot_standby:
                    self.pu_twins[pu_id].set_hot_standby(standby)
                    res.append(ProcessingUnitHotStandBy(self.edc_config.edc_id, pu_id, standby, instantaneous))
            self.explore_hot_standby = False
        return res

    def start_request(self, req: StartSessionRequest) -> Optional[Union[ProcessingUnitServiceRequest, ServiceResponse]]:
        if self.session_starting(req.service_id, req.client_id):
            return
        elif self.session_started(req.service_id, req.client_id):
            return ServiceResponse(req, True, 'session already created')
        elif self.session_stopping(req.service_id, req.client_id):
            return ServiceResponse(req, False, 'session is currently stopping')

        hot_pus = (pu_twin for pu_twin in self.pu_twins.values() if pu_twin.hot_standby)
        mapped_pu = self.mapper.allocate_session(req.service_id, hot_pus)
        if mapped_pu is None:
            cold_pus = (pu_twin for pu_twin in self.pu_twins.values() if not pu_twin.hot_standby)
            mapped_pu = self.mapper.allocate_session(req.service_id, cold_pus)
            if mapped_pu is None:
                return ServiceResponse(req, False, 'not able to map session into any PU')

        self.explore_hot_standby = True
        mapped_pu.start_starting_session(req.service_id, req.client_id)
        self.clean_session_addition(self.starting, req.service_id, req.client_id, mapped_pu)
        return ProcessingUnitServiceRequest(self.edc_config.edc_id, mapped_pu.pu_id, req)

    def start_response(self, response: ProcessingUnitServiceResponse) -> ServiceResponse:
        request = response.response.request
        pu = self.starting[request.service_id][request.client_id]
        success = response.response.response
        pu.finish_starting_session(request.service_id, request.client_id, success)
        self.clean_session_removal(self.starting, request.service_id, request.client_id)
        if success:
            self.clean_session_addition(self.started, request.service_id, request.client_id, pu)
        else:
            self.explore_hot_standby = True
        return response.response

    def service_request(self, req: ServiceRequest) -> Optional[Union[ProcessingUnitServiceRequest, ServiceResponse]]:
        pu: Optional[ProcessingUnitDigitalTwin] = None
        if req.session:
            if self.session_starting(req.service_id, req.client_id):
                return ServiceResponse(req, False, 'session is still starting')
            elif self.session_stopping(req.service_id, req.client_id):
                return ServiceResponse(req, False, 'session is currently stopping')
            elif not self.session_started(req.service_id, req.client_id):
                return ServiceResponse(req, False, 'session not found')
            pu = self.started[req.service_id][req.client_id]
        else:
            raise NotImplementedError('this is not available yet')
        if pu.request_being_processed(req):
            return
        pu.start_processing_task(req)
        return ProcessingUnitServiceRequest(self.edc_config.edc_id, pu.pu_id, req)

    def service_response(self, response: ProcessingUnitServiceResponse) -> ServiceResponse:
        request = response.response.request
        pu: Optional[ProcessingUnitDigitalTwin] = None
        if request.session:
            pu = self.started[request.service_id][request.client_id]
        else:
            raise NotImplementedError('this is not available yet')
        pu.finish_processing_task(request)
        return response.response

    def stop_request(self, req: StopSessionRequest) -> Optional[Union[ProcessingUnitServiceRequest, ServiceResponse]]:
        if self.session_starting(req.service_id, req.client_id):
            return ServiceResponse(req, False, 'session is still starting')
        elif self.session_stopping(req.service_id, req.client_id):
            return
        elif not self.session_started(req.service_id, req.client_id):
            return ServiceResponse(req, True, 'session not found')
        elif self.session_busy(req.service_id, req.client_id):
            return ServiceResponse(req, False, 'session is busy')

        pu = self.started[req.service_id][req.client_id]
        pu.start_stopping_session(req.service_id, req.client_id)
        self.clean_session_removal(self.started, req.service_id, req.client_id)
        self.clean_session_addition(self.stopping, req.service_id, req.client_id, pu)
        return ProcessingUnitServiceRequest(self.edc_config.edc_id, pu.pu_id, req)

    def stop_response(self, response: ProcessingUnitServiceResponse) -> ServiceResponse:
        request = response.response.request
        pu = self.stopping[request.service_id][request.client_id]
        success = response.response.response
        pu.finish_stopping_session(request.service_id, request.client_id, success)
        self.clean_session_removal(self.stopping, request.service_id, request.client_id)
        if success:
            self.explore_hot_standby = True
        else:
            self.clean_session_addition(self.started, request.service_id, request.client_id, pu)
        return response.response

    def update_pu_report(self, pu_id: str, pu_report: ProcessingUnitReport):
        self.pu_twins[pu_id].latest_report = pu_report

    def update_cooler(self):
        if self.cooler is not None:
            temps: Dict[str, float] = dict()
            powers: Dict[str, float] = dict()
            for pu_id, pu_twin in self.pu_twins.items():
                if pu_twin.latest_report is not None:
                    temps[pu_id] = pu_twin.latest_report.temp
                    powers[pu_id] = pu_twin.latest_report.power
            self.cooler.refresh_cooler(temps, powers)

    def session_starting(self, service_id: str, client_id: str) -> bool:
        return service_id in self.starting and client_id in self.starting[service_id]

    def session_started(self, service_id: str, client_id: str) -> bool:
        return service_id in self.started and client_id in self.started[service_id]

    def session_busy(self, service_id: str, client_id: str) -> bool:
        return bool(self.started[service_id][client_id].session_requests[service_id][client_id])

    def session_stopping(self, service_id: str, client_id: str) -> bool:
        return service_id in self.stopping and client_id in self.stopping[service_id]

    @staticmethod
    def clean_session_addition(target: Dict[str, Dict[str, ProcessingUnitDigitalTwin]],
                               service_id: str, client_id: str, pu: ProcessingUnitDigitalTwin):
        if service_id not in target:
            target[service_id] = dict()
        target[service_id][client_id] = pu

    @staticmethod
    def clean_session_removal(target: Dict[str, Dict[str, ProcessingUnitDigitalTwin]], service_id: str, client_id: str):
        if service_id not in target or client_id not in target[service_id]:
            raise AssertionError('Unable to remove non-existent session')
        target[service_id].pop(client_id)
        if not target[service_id]:
            target.pop(service_id)
