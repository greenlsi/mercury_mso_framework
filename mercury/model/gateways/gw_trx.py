from xdevs.models import Port
from mercury.msg.packet import AppPacket, NetworkPacket, PhysicalPacket
from mercury.msg.packet.app_packet.acc_packet import AccessPacket
from mercury.msg.packet.phys_packet import RadioPacket, CrosshaulPacket
from ..common import ExtendedAtomic


class AccessTransceiver(ExtendedAtomic):
    def __init__(self, gateway_id: str, wired: bool):
        """
        Model of gateway transceiver for access network.
        :param str gateway_id: Gateway ID.
        """
        self.gateway_id: str = gateway_id
        self.wired: bool = wired
        super().__init__(f'gateway_{self.gateway_id}_acc_trx')

        self.input_net: Port[NetworkPacket] = Port(NetworkPacket, 'input_net')
        self.input_phys: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_phys')
        self.output_net: Port[NetworkPacket] = Port(NetworkPacket, 'output_net')
        self.output_net_to_xh: Port[NetworkPacket] = Port(NetworkPacket, 'output_net_to_xh')
        self.output_phys_acc: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_acc')
        self.output_phys_srv: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys_srv')
        self.add_in_port(self.input_net)
        self.add_in_port(self.input_phys)
        self.add_out_port(self.output_net)
        self.add_out_port(self.output_net_to_xh)
        self.add_out_port(self.output_phys_acc)
        self.add_out_port(self.output_phys_srv)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        for net_msg in self.input_net.values:
            phys_msg = RadioPacket(self.gateway_id, net_msg.node_to, net_msg, self.wired)
            app_msg = net_msg.data if isinstance(net_msg.data, AppPacket) else net_msg.data.data
            out_port = self.output_phys_acc if isinstance(app_msg, AccessPacket) else self.output_phys_srv
            self.add_msg_to_queue(out_port, phys_msg)
        for phys_msg in self.input_phys.values:
            phys_msg.receive(self._clock)
            net_msg = phys_msg.data
            out_port = self.output_net_to_xh
            if net_msg.node_to == self.gateway_id:
                out_port = self.output_net
                if isinstance(net_msg.data, AccessPacket):
                    net_msg.data.snr = phys_msg.snr
            self.add_msg_to_queue(out_port, net_msg)
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass


class CrosshaulTransceiver(ExtendedAtomic):
    def __init__(self, gateway_id: str):
        """
        Model of gateway transceiver for crosshaul network.
        :param gateway_id: ID of the corresponding gateway
        """
        self.gateway_id = gateway_id
        super().__init__(f'gateway_{self.gateway_id}_xh_trx')
        self.input_net: Port[NetworkPacket] = Port(NetworkPacket, 'input_net')
        self.input_phys: Port[PhysicalPacket] = Port(PhysicalPacket, 'input_phys')
        self.output_net: Port[NetworkPacket] = Port(NetworkPacket, 'output_net')
        self.output_net_to_acc: Port[NetworkPacket] = Port(NetworkPacket, 'output_net_to_acc')
        self.output_phys: Port[PhysicalPacket] = Port(PhysicalPacket, 'output_phys')
        self.add_in_port(self.input_net)
        self.add_in_port(self.input_phys)
        self.add_out_port(self.output_net)
        self.add_out_port(self.output_net_to_acc)
        self.add_out_port(self.output_phys)

    def deltint_extension(self):
        self.passivate()

    def deltext_extension(self, e):
        for net_msg in self.input_net.values:
            self.add_msg_to_queue(self.output_phys, CrosshaulPacket(self.gateway_id, net_msg.node_to, net_msg))
        for phys_msg in self.input_phys.values:
            phys_msg.receive(self._clock)
            net_msg = phys_msg.data
            out_port = self.output_net if net_msg.node_to == self.gateway_id else self.output_net_to_acc
            self.add_msg_to_queue(out_port, net_msg)
        self.passivate() if self.msg_queue_empty() else self.activate()

    def lambdaf_extension(self):
        pass

    def initialize(self):
        self.passivate()

    def exit(self):
        pass
