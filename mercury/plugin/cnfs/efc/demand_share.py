from abc import ABC, abstractmethod
from typing import Dict, Optional
from mercury.msg.smart_grid import PowerConsumptionReport


class DemandShare(ABC):
    def __init__(self, **kwargs):
        self.share: Dict[str, Dict[str, Optional[float]]] = dict()

    def demand_share(self, reports: Dict[str, PowerConsumptionReport], offers: Dict[str, Optional[float]],
                     demand: Dict[str, Optional[float]]) -> bool:
        new_share = self.compute_demand_share(reports, offers, demand)
        res = new_share != self.share
        if res:
            self.share = new_share
        return res

    @abstractmethod
    def compute_demand_share(self, reports: Dict[str, PowerConsumptionReport], offers: Dict[str, Optional[float]],
                             demand: Dict[str, Optional[float]]) -> Dict[str, Dict[str, Optional[float]]]:
        pass


class EqualDemandShare(DemandShare):
    def compute_demand_share(self, reports: Dict[str, PowerConsumptionReport], offers: Dict[str, Optional[float]],
                             demand: Dict[str, Optional[float]]) -> Dict[str, Dict[str, Optional[float]]]:
        return {edc: {service: None if n_users is None else n_users / len(reports)
                      for service, n_users in demand.items()}
                for edc in reports}


class TrendDemandShare(DemandShare):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def compute_demand_share(self, reports: Dict[str, PowerConsumptionReport], offers: Dict[str, Optional[float]],
                             demand: Dict[str, Optional[float]]) -> Dict[str, Dict[str, Optional[float]]]:
        res: Dict[str, Dict[str, Optional[float]]] = dict()   # It will contain the result
        sessions_per_edc: Dict[str, Dict[str, int]] = dict()  # Dictionary {EDC: {service: number of current sessions}}
        sessions_per_service: Dict[str, int] = dict()         # Dictionary {service: total number of current sessions}

        for edc_id, edc_report in reports.items():
            if edc_report is None:
                continue
            res[edc_id] = dict()
            sessions_per_edc[edc_id] = dict()
            for service_id, estimation in demand.items():
                if estimation is None:
                    res[edc_id][service_id] = None
                else:
                    n_sessions = edc_report.report.n_service_sessions(service_id)
                    if n_sessions == 0 and edc_report.report.max_sessions.get(service_id, 0) > 0:
                        n_sessions = 1
                    sessions_per_edc[edc_id][service_id] = n_sessions
                    if service_id not in sessions_per_service:
                        sessions_per_service[service_id] = 0
                    sessions_per_service[service_id] += n_sessions

        for edc_id, services in sessions_per_edc.items():
            for service_id, sessions in services.items():
                total_sessions = sessions_per_service[service_id]
                share = 0 if total_sessions == 0 else sessions / total_sessions
                res[edc_id][service_id] = share * demand[service_id]
        return res
