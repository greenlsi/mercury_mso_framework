from xdevs.models import Port
from mercury.fog_model.common import ExtendedAtomic
from typing import Tuple, Union, Optional
from mercury.config.core import CoreConfig
from mercury.msg.smart_grid import PowerConsumptionReport
from mercury.msg.edcs import DispatchingFunction, HotStandbyFunction
from mercury.msg.network import PhysicalPacket, NetworkPacket, ApplicationPacket, CrosshaulPacket
from mercury.msg.network.packet.app_layer.edge_fed_mgmt import NewDispatchingFunction, \
    NewHotStandbyFunction, NewEDCReport
from mercury.msg.network.packet.app_layer.service import GetDataCenterRequest, GetDataCenterResponse
from mercury.msg.network.packet.app_layer.ran import RANControlRequest, RANControlResponse


class CoreNetworkFunctions(ExtendedAtomic):

    def __init__(self, lite: bool = False):

        super().__init__('{}_cnfs'.format(CoreConfig.CORE_ID))

        self.input_dispatching = Port(DispatchingFunction, 'input_dispatching')
        self.input_hot_standby = Port(HotStandbyFunction, 'input_hot_standby')
        self.input_datacenter_response = Port(GetDataCenterResponse, 'input_datacenter_response')
        self.input_amf_response = Port(RANControlResponse, 'input_amf_response')
        self.output_power_consumption = Port(PowerConsumptionReport, 'output_power_consumption')
        self.output_datacenter_request = Port(GetDataCenterRequest, 'output_datacenter_request')
        self.output_amf_request = Port(RANControlRequest, 'output_amf_request')

        self.lite = lite
        port_type = NetworkPacket if lite else PhysicalPacket
        self.input_data = Port(port_type, 'input_data')
        self.output_data = Port(port_type, 'output_data')

        self.add_in_port(self.input_dispatching)
        self.add_in_port(self.input_hot_standby)
        self.add_in_port(self.input_datacenter_response)
        self.add_in_port(self.input_amf_response)
        self.add_out_port(self.output_power_consumption)
        self.add_out_port(self.output_datacenter_request)
        self.add_out_port(self.output_amf_request)

        self.add_in_port(self.input_data)
        self.add_out_port(self.output_data)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        # 1. Wrap leaving messages to send them through the network
        for job in self.input_dispatching.values:
            self.add_msg_to_output_port(NewDispatchingFunction(job), job.edc_id)
        for job in self.input_hot_standby.values:
            self.add_msg_to_output_port(NewHotStandbyFunction(job), job.edc_id)
        for job in self.input_datacenter_response.values:
            self.add_msg_to_output_port(job, job.ue_id, job.ap_id)
        for job in self.input_amf_response.values:
            self.add_msg_to_output_port(job, job.ap_id)
        # 2. Process new data from the network
        for job in self.input_data.values:
            node_from, app_msg = self.expanse_input_msg(job)
            if isinstance(app_msg, NewEDCReport):
                self.add_msg_to_queue(self.output_power_consumption, app_msg.power_report)
            elif isinstance(app_msg, RANControlRequest):
                self.add_msg_to_queue(self.output_amf_request, app_msg)
            elif isinstance(app_msg, GetDataCenterRequest):
                self.add_msg_to_queue(self.output_datacenter_request, app_msg)
            else:
                raise ValueError('Unable to determine message data type')
        self.passivate() if self.msg_queue_empty() else self.activate()

    def add_msg_to_output_port(self, job: ApplicationPacket, network_to: str, physical_to: Optional[str] = None):
        msg = NetworkPacket(CoreConfig.CORE_ID, network_to, job)
        if not self.lite:
            node_to = network_to if physical_to is None else physical_to
            msg = CrosshaulPacket(CoreConfig.CORE_ID, node_to, msg)
        self.add_msg_to_queue(self.output_data, msg)

    @staticmethod
    def expanse_input_msg(job: Union[NetworkPacket, PhysicalPacket]) -> Tuple[str, ApplicationPacket]:
        node_from, msg = job.expanse_packet()
        if isinstance(msg, NetworkPacket):
            node_from, msg = msg.expanse_packet()
        return node_from, msg

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
