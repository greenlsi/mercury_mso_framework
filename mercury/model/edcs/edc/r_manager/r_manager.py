from __future__ import annotations
from mercury.config.edcs import EdgeDataCenterConfig
from mercury.logger import logger as logging, logging_overhead
from mercury.msg.edcs import *
from mercury.msg.packet.app_packet.srv_packet import *
from xdevs.models import Port
from .cooler import Cooler
from .pu import ProcessingUnit
from .slicer import EDCResourceSlicer
from ....common.fsm import ExtendedAtomic


class EDCResourceManager(ExtendedAtomic):

    LOGGING_OVERHEAD: str = '            '

    def __init__(self, edc_config: EdgeDataCenterConfig, srv_priority: list[str], cloud_id: str | None):
        """
        Edge data center resource manager.  # TODO add migration capabilities
        :param edc_config: EDC configuration parameters.
        :param srv_priority: service priority list. leftmost services have a higher priority.
        :param cloud_id:
        """
        from mercury.plugin import PUMappingStrategy
        self.edc_config: EdgeDataCenterConfig = edc_config
        self.edc_id: str = self.edc_config.edc_id
        self.srv_priority: list[str] = srv_priority
        self.cloud_id: str | None = cloud_id
        super().__init__(f'edc_{self.edc_id}_r_manager')

        self.cooler: Cooler = Cooler(self.edc_id, self.edc_config.cooler_config, self.edc_config.edc_temp)
        self.pus: dict[str, ProcessingUnit] = dict()
        for pu_id, pu_config in edc_config.pu_configs.items():
            self.pus[pu_id] = ProcessingUnit(self.edc_id, pu_id, pu_config, self.edc_config.edc_temp, True)
        self.mapping: PUMappingStrategy | None = None
        self.slicer: EDCResourceSlicer = EDCResourceSlicer(self.edc_config, self.srv_priority)
        self.expected_slicing: dict[str, int] = dict()
        self.pu_slices: dict[str | None, tuple[int, dict[str, ProcessingUnit]]] = {
            None: (0, {pu_id: pu for pu_id, pu in self.pus.items()})
        }
        self.req_map: dict[str, dict[str, ProcessingUnit]] = dict()  # {service ID: {client ID: Processing Unit}}
        self.report_required: bool = False

        self.input_config: Port[NewEDCConfig] = Port(NewEDCConfig, 'input_config')
        self.input_srv: Port[SrvRelatedRequest] = Port(SrvRelatedRequest, 'input_srv')
        self.output_srv_request: Port[SrvRelatedRequest] = Port(SrvRelatedRequest, 'output_srv_request')
        self.output_srv_response: Port[SrvRelatedResponse] = Port(SrvRelatedResponse, 'output_srv_response')
        self.output_report: Port[EdgeDataCenterReport] = Port(EdgeDataCenterReport, 'output_report')
        for in_port in self.input_config, self.input_srv:
            self.add_in_port(in_port)
        for out_port in self.output_srv_request, self.output_srv_response, self.output_report:
            self.add_out_port(out_port)

    @property
    def it_power(self) -> float:
        return self.cooler.it_power

    @property
    def cooling_power(self) -> float:
        return self.cooler.cooling_power

    def initialize(self):
        overhead = logging_overhead(self._clock, EDCResourceManager.LOGGING_OVERHEAD)
        self.new_mapping(overhead, self.edc_config.r_mngr_config.mapping_id,
                         **self.edc_config.r_mngr_config.mapping_config)
        self.slice_resources(overhead, self.edc_config.r_mngr_config.edc_slicing, True)
        self.sigma = self.next_sigma()

    def exit(self):
        pass

    def deltint_extension(self):
        self.report_required = False
        overhead = logging_overhead(self._clock, EDCResourceManager.LOGGING_OVERHEAD)
        self.update_t(overhead)
        self.sigma = self.next_sigma()

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, EDCResourceManager.LOGGING_OVERHEAD)
        for msg in self.input_config.values:
            if isinstance(msg, NewEDCMapping):
                self.new_mapping(overhead, msg.mapping_id, **msg.mapping_config)
            elif isinstance(msg, NewEDCSlicing):
                self.expected_slicing = msg.slicing
                self.slice_resources(overhead, self.expected_slicing, self._clock <= 0)
        if self.input_srv:
            self.update_t(overhead, True)  # first, we update the status of the processed tasks
            for request in self.input_srv.values:
                request.receive(self._clock)
                response: SrvRelatedResponse | None = None
                if isinstance(request, OpenSessRequest):
                    response = self.map_open_session(request)
                elif isinstance(request, SrvRequest):
                    request.create_process(self._clock)
                    response = self.map_srv_request(request)
                elif isinstance(request, CloseSessRequest):
                    response = self.map_close_session(request)
                if isinstance(response, SrvRelatedResponse):
                    self.send_response(overhead, response)
                elif isinstance(response, SrvRelatedRequest):
                    self.send_to_cloud(overhead, response)
            self.update_t(overhead)  # Once we have processed all the new requests, we update the PUs again
        self.sigma = self.next_sigma()

    def lambdaf_extension(self):
        if self.report_required:
            slicing: dict[str, SrvSlicingReport] = dict()
            _, free_pus = self.pu_slices.get(None, (0, dict()))
            for srv_id in self.srv_priority:
                slice_size, slice_available = 0, 0
                _, pus = self.pu_slices.get(srv_id, (0, dict()))
                for pu in pus.values():
                    slice_size += pu.max_n_tasks(srv_id)
                    slice_available += pu.additional_tasks(srv_id)
                free_size, free_available = 0, 0
                for pu in free_pus.values():
                    free_size += pu.max_n_tasks(srv_id)
                    free_available += pu.additional_tasks(srv_id)
                slicing[srv_id] = SrvSlicingReport(self.expected_slicing.get(srv_id, 0), slice_size,
                                                   slice_available, free_size, free_available)
            self.output_report.add(EdgeDataCenterReport(self.edc_id, slicing, self.it_power, self.cooling_power))

    def new_mapping(self, overhead: str, mapping_id: str, **kwargs):
        from mercury.plugin import AbstractFactory
        logging.info(f'{overhead}EDC {self.edc_id}: new mapping function ({mapping_id})')
        self.mapping = AbstractFactory.create_edc_pu_mapping(mapping_id, **kwargs)

    def slice_resources(self, overhead: str, srv_slicing: dict[str, int], instantaneous: bool = False):
        self.report_required = True
        pu_slices = self.slicer.slice_resources(srv_slicing)
        for srv_id in self.srv_priority:
            expected_slice = srv_slicing.get(srv_id, 0)
            slice_size, sliced_pus = pu_slices.get(srv_id, (0, list()))
            msg = f'{overhead}EDC {self.edc_id} slice for service {srv_id}: {slice_size} (expected {expected_slice}) in {sliced_pus}'
            logging.info(msg) if expected_slice <= slice_size else logging.warning(msg)
            for pu_id in sliced_pus:
                self.set_standby(overhead, pu_id, True, instantaneous)
        _, free_pus = pu_slices[None]
        logging.info(f'{overhead}EDC {self.edc_id} unassigned PUs: {free_pus}')
        for pu_id in free_pus:
            self.set_standby(overhead, pu_id, self.edc_config.r_mngr_config.standby, instantaneous)
        self.pu_slices = {srv_id: (slice_size, {pu_id: self.pus[pu_id] for pu_id in pus})
                          for srv_id, (slice_size, pus) in pu_slices.items()}
        self.update_t(overhead)

    def update_t(self, overhead: str, force: bool = False):
        it_power: float = 0
        self.report_required |= force
        for pu in self.pus.values():
            if force:
                self.update_pu_t(overhead, pu)
            while pu.update or pu.next_t <= self._clock:
                self.report_required = True
                self.update_pu_t(overhead, pu)
            it_power += pu.power
        self.cooler.update_cooler(it_power)

    def update_pu_t(self, overhead: str, pu: ProcessingUnit):
        status = pu.update_t(self._clock)
        if status is not None:
            for responses in status:
                for response in responses:
                    self.report_required = True
                    self.send_response(overhead, response)
                    # Check if we need to modify the request map
                    if isinstance(response, SrvResponse) and not response.request.sess_required \
                            or isinstance(response, CloseSessResponse) and response.response >= 0:
                        self.req_map[response.service_id].pop(response.client_id)
                        if not self.req_map[response.service_id]:
                            self.req_map.pop(response.service_id)

    def next_sigma(self) -> float:
        if self.report_required or not self.msg_queue_empty():
            return 0
        return max(min((pu.next_t for pu in self.pus.values()), default=inf) - self._clock, 0)

    def map_open_session(self, request: OpenSessRequest) -> OpenSessRequest | OpenSessResponse | None:
        new_map: bool = False
        pu = self.req_map.get(request.service_id, dict()).get(request.client_id)  # Primero miro si sesión ya existe
        if pu is None:
            new_map = True
            pu = self.map_task(request.service_id)  # Si no, pruebo a mapear en los recursos
            if pu is None:
                if self.cloud_id is not None:
                    request.set_server(self.cloud_id)
                    return request
                else:
                    return OpenSessResponse(request, None, self._clock, 'EDC mapping error: out of resources')
        response = pu.add_open_session(request)
        if new_map and response is None:  # New session being opened
            self.report_required = True
            if request.service_id not in self.req_map:
                self.req_map[request.service_id] = dict()
            self.req_map[request.service_id][request.client_id] = pu
        return response

    def map_srv_request(self, request: SrvRequest) -> SrvRequest | SrvResponse | None:
        new_map: bool = False
        pu = self.req_map.get(request.service_id, dict()).get(request.client_id)
        if pu is None:
            if request.sess_required:
                return SrvResponse(request, False, self._clock, 'EDC mapping error: required session not found')
            new_map = True
            pu = self.map_task(request.service_id)
            if pu is None:
                if self.cloud_id is not None:
                    request.set_server(self.cloud_id)
                    return request
                return SrvResponse(request, False, self._clock, 'EDC mapping error: out of resources')
        response = pu.add_srv_request(request.process)
        if new_map and response is None:  # The request is being processed, and we need to modify the request map
            self.report_required = True
            if request.service_id not in self.req_map:
                self.req_map[request.service_id] = dict()
            self.req_map[request.service_id][request.client_id] = pu
        return response

    def map_close_session(self, request: CloseSessRequest) -> CloseSessResponse | None:
        pu = self.req_map.get(request.service_id, dict()).get(request.client_id)
        if pu is None:
            return CloseSessResponse(request, 0, self._clock, 'EDC mapping error: required session does not exist')
        return pu.add_close_session(request)

    def send_response(self, overhead: str, response: SrvRelatedResponse):
        response.send(self._clock)
        self.add_msg_to_queue(self.output_srv_response, response)
        logging.info(f'{overhead}EDC {self.edc_id} response: {response}')

    def send_to_cloud(self, overhead: str, request: SrvRelatedRequest):
        request.set_server(self.cloud_id)
        self.add_msg_to_queue(self.output_srv_request, request)
        logging.warning(f'{overhead}EDC {self.edc_id} out of resources. Forwarding request {request} to cloud {self.cloud_id}')

    def set_standby(self, overhead: str, pu_id: str, standby: bool, instantaneous: bool = False):
        pu = self.pus[pu_id]
        if pu.standby != standby:
            logging.info(f'{overhead}PU {pu_id} of EDC {self.edc_id} standby: {standby}')
            pu.set_standby(standby, instantaneous)

    def map_task(self, service_id: str) -> ProcessingUnit | None:
        _, sliced_pus = self.pu_slices.get(service_id, (0, dict()))
        pu = self.mapping.map_task(sliced_pus.values(), service_id)  # primero intento mapear en el slice
        if pu is None:
            _, free_pus = self.pu_slices.get(None, (0, dict()))      # luego intento mapear en recursos sin asignar
            pu = self.mapping.map_task(free_pus.values(), service_id)
        return pu
