from mercury.logger import logger as logging, logging_overhead
from mercury.config.core import CoreConfig
from mercury.msg.network.packet.app_layer.ran import RANControlRequest, CreatePathRequest, RemovePathRequest,\
    SwitchPathRequest, CreatePathResponse, RemovePathResponse, SwitchPathResponse, RANControlResponse
from typing import Dict
from xdevs.models import Port
from ..common import ExtendedAtomic


class AccessAndMobilityManagementFunction(ExtendedAtomic):

    LOGGING_OVERHEAD = "    "

    def __init__(self):
        """Access and Mobility Management Function xDEVS model"""

        super().__init__(name='{}_amf'.format(CoreConfig.CORE_ID))

        self.path_table: Dict[str, str] = dict()

        self.input_request = Port(RANControlRequest, 'input_request')
        self.output_response = Port(RANControlResponse, 'output_response')
        self.add_in_port(self.input_request)
        self.add_out_port(self.output_response)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        overhead = logging_overhead(self._clock, self.LOGGING_OVERHEAD)
        for job in self.input_request.values:
            ap_id = job.ap_id
            ue_id = job.ue_id
            if isinstance(job, SwitchPathRequest):
                prev_ap_id = job.prev_ap_id
                self._switch_path(ue_id, ap_id, prev_ap_id, overhead)
            elif isinstance(job, CreatePathRequest):
                self._create_path(ue_id, ap_id, overhead)
            elif isinstance(job, RemovePathRequest):
                self._remove_path(ue_id, ap_id, overhead)
            else:
                raise Exception("RAN access_points_config control message type could nob be identified by AMF")
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass

    def _create_path(self, ue_id: str, ap_id: str, overhead: str):
        """
        If UE has not yet an assigned path, the AMF module generates new path.
        :param ue_id: ID of the UE to be routed
        :param ap_id: ID of the AP on which the UE is connected_ap
        :param overhead: logging overhead
        """
        res = ue_id not in self.path_table
        logging.info(overhead + '%s--->AMF create path %s request' % (ap_id, ue_id))
        if res:
            self.path_table[ue_id] = ap_id
        self.add_msg_to_queue(self.output_response, CreatePathResponse(ap_id, ue_id, res))

    def _remove_path(self, ue_id: str, ap_id: str, overhead: str):
        """
        If UE has an assigned path, the AMF removes it
        :param ue_id: ID of the UE to be routed
        :param ap_id: ID of the AP on which the UE is connected_ap
        :param overhead: logging overhead
        """
        res = ue_id in self.path_table and ap_id == self.path_table[ue_id]
        logging.info(overhead + '%s--->AMF remove path %s request' % (ap_id, ue_id))
        if res:
            self.path_table.pop(ue_id)
        self.add_msg_to_queue(self.output_response, RemovePathResponse(ap_id, ue_id, res))

    def _switch_path(self, ue_id: str, new_ap_id: str, prev_ap_id: str, overhead: str):
        """
        If UE has already an assigned path, the path can be changed by the AMF when requested
        :param ue_id: ID of the UE to be re-routed
        :param new_ap_id: ID of the AP on which the UE is re-connected_ap
        :param prev_ap_id: ID of the AP on which the UE was previously connected_ap
        :param overhead: logging overhead
        """
        res = ue_id in self.path_table and prev_ap_id == self.path_table[ue_id]
        logging.info(overhead + '%s--->AMF switch path %s request' % (new_ap_id, ue_id))
        if res:
            self.path_table[ue_id] = new_ap_id
        self.add_msg_to_queue(self.output_response, SwitchPathResponse(new_ap_id, ue_id, prev_ap_id, res))
