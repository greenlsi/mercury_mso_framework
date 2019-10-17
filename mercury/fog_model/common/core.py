from abc import ABC, abstractmethod
from math import sqrt
from .crosshaul import CrosshaulTransceiverConfiguration


class CoreLayerConfiguration:
    def __init__(self, amf_id, sdn_controller_id, core_location, crosshaul_transceiver, edc_slicing, congestion,
                 sdn_strategy=None):
        """
        Core Layer Configuration
        :param str amf_id: ID of the AMF
        :param str sdn_controller_id: ID of the SDN controller
        :param tuple core_location: Location of the Core Network Elements <x, y> (in meters)
        :param CrosshaulTransceiverConfiguration crosshaul_transceiver: Crosshaul Transceiver configuration
        :param dict edc_slicing: nested dictionary {EDC ID: {service ID: max_utilization}}
        :param float congestion: minimum utilization (in %) for considering an EDC congested (0 <= congestion <= 100)
        :param SDNStrategy sdn_strategy: Software-Defined Network linking strategy class
        """
        self.amf_id = amf_id
        self.sdn_controller_id = sdn_controller_id
        self.core_location = core_location
        self.crosshaul_transceiver = crosshaul_transceiver
        self.edc_slicing = edc_slicing
        self.congestion = congestion
        if sdn_strategy is None:
            sdn_strategy = SDNClosestStrategy
        self.sdn_strategy = sdn_strategy


class SDNStrategy(ABC):
    def __init__(self, aps_location, edcs_location, congestion, services_id, edc_slicing):
        """
        Software-Defined Network allocation strategy class.
        :param dict aps_location: Dictionary {AP ID: AP location}
        :param dict edcs_location: Dictionary {EDC ID: EDC location}
        :param float congestion: Maximum utilization factor to be considered for an EDC to be available
        :param list services_id: list with the ID of all the services_config within the scenario
        :param edc_slicing: nested dictionary {dc_id: {service_id: service_u}}
        """
        self.aps_location = aps_location
        self.edcs_location = edcs_location
        assert 0 <= congestion <= 100
        self.congestion = congestion
        for services in edc_slicing.values():
            for service in services:
                assert service in services_id
            for service in services_id:
                assert service in services
        self.services_id = services_id
        self.edc_slicing = edc_slicing

        self.edcs_utilization = {edc: dict() for edc in self.edcs_location.keys()}
        self.available_edcs = {edc: False for edc in self.edcs_location.keys()}
        self.edcs_availability = {edc: dict() for edc in self.edcs_location.keys()}

    def update_edc_utilization(self, edc_id, utilization_dict, overall_utilization):
        """
        Updates current utilization factor for a given Edge Data Center
        :param str edc_id: ID of the Edge Data Center
        :param dict utilization_dict: utilization {service_id: relative_u}
        :param float overall_utilization: overall utilization of the EDC (%)
        """
        self.edcs_utilization[edc_id] = {service_id: service_u for service_id, service_u in utilization_dict.items()}
        self.available_edcs[edc_id] = overall_utilization < self.congestion
        for service_id, max_u in self.edc_slicing[edc_id].items():
            if service_id not in self.edcs_utilization[edc_id]:
                self.edcs_availability[edc_id][service_id] = True
            else:
                service_u = self.edcs_utilization[edc_id][service_id]
                self.edcs_availability[edc_id][service_id] = service_u < self.edc_slicing[edc_id][service_id]

    @abstractmethod
    def assign_edc(self, ap_id):
        """
        From a list of available Edge Data Centers, the optimal is chosen for a given Access Point
        :param str ap_id: ID of the Access Point
        :return dict: Best Edge Data Center ID
        """
        pass


class SDNClosestStrategy(SDNStrategy):
    def distance_list(self, ap_location):
        """
        Compute the euclidean distance between an AP and all the EDCs. It returns a sorted list of edc
        :param tuple ap_location: AP location
        """
        distances = list()
        for edc_id, edc_location in self.edcs_location.items():
            distance = sqrt(sum([(ap_location[i] - edc_location[i]) ** 2 for i in range(len(ap_location))]))
            distances.append((edc_id, distance))
        distances = sorted(distances, key=lambda x: x[1])
        return [edc[0] for edc in distances]

    def assign_edc(self, ap_id):
        """
        From a list of available Edge Data Centers, the closest to a given Access Point is chosen
        :param str ap_id: ID of the Access Point
        :return: dictionary {service_id: dc_id} with the most suitable EDC for each pxsch
        """
        service_routing = {service_id: None for service_id in self.services_id}
        distance_list = self.distance_list(self.aps_location[ap_id])
        for service_id in self.services_id:
            for edc_id in distance_list:
                if self.available_edcs[edc_id] and self.edcs_availability[edc_id][service_id]:
                    service_routing[service_id] = edc_id
                    break
        return service_routing
