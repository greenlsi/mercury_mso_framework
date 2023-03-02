from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
from random import shuffle, randint
from typing import Any


class MoveFunction(ABC):
    def __init__(self, **kwargs):
        """
        Abstract class for scenario move function in the decision support system.

        :param max_val: maximum allowed value(s) (move method-specific).
        :param min_val: minimum allowed value(s) (move method-specific).
        :param max_gradient: maximum allowed movement(s) (move method-specific).
        :param kwargs: any other parameter required by a specific implementation.
        """
        self.max_val = kwargs.get('max_val')
        self.min_val = kwargs.get('min_val')
        self.max_gradient = kwargs.get('max_gradient')

    @abstractmethod
    def move(self, prev_state: dict[str, Any]) -> dict[str, Any]:
        """
        Moves a scenario configuration.

        :param prev_state: previous scenario state.
        :return: a deep copy of the new state after the movement.
        """
        pass


class MoveEdgeDataCenters(MoveFunction, ABC):
    def __init__(self, **kwargs):
        """
        Abstract class for EDC configuration move function in the decision support system.

        :param int n_edcs: maximum number of EDCs to be modified in each movement. Defaults to 1.
        :param bool copy: if True, all the EDCs will have the same configuration. Defaults to False.
        :param kwargs: see [`MoveFunction`] for more details.
        """
        super().__init__(**kwargs)
        self.n_edcs: int = kwargs.get('n_edcs', 1)
        self.copy: bool = kwargs.get('copy', False)

    def move(self, prev_state: dict[str, Any]) -> dict[str, Any]:
        new_state = deepcopy(prev_state)
        edcs = list(new_state['edcs'].keys())
        for _ in range(self.n_edcs):
            # select a random EDC
            try:
                shuffle(edcs)
                edc_id = edcs.pop()
            except IndexError:
                break
            # Move the EDC's configuration
            self.move_edc(edc_id, new_state)
            # If copy is enabled, we reproduce the change to all the EDCs in the scenario
            if self.copy:
                self.copy_config(edc_id, new_state)
                break
        return new_state

    @abstractmethod
    def move_edc(self, edc_id: str, new_state: dict[str, Any]):
        """
        Moves the configuration of a single EDC.

        :param edc_id: ID of the EDC to be moved.
        :param new_state: reference to the new scenario state. You must modify it in-place.
        """
        pass

    @abstractmethod
    def copy_config(self, edc_id: str, new_state: dict[str, Any]):
        pass


class MoveChargeDischarge(MoveEdgeDataCenters):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scale: float = kwargs.get('scale', 1)

    def move_edc(self, edc_id: str, new_state: dict[str, Any]):
        """
        Changes the minimum discharge cost and maximum charge cost thresholds of a given EDC.
        The smart grid layer must be activated for all the EDCs of the scenario.

        :param edc_id: ID of the EDC to be moved.
        :param new_state: reference to the new scenario state. Movements are done in-place.
        """
        # Get current configuration of the EDC
        current_min = int(new_state['edcs'][edc_id]['sg_config']['manager_config']['min_discharge_cost'] / self.scale)
        current_max = int(new_state['edcs'][edc_id]['sg_config']['manager_config']['max_charge_cost'] / self.scale)

        # randomly select the new minimum discharge cost
        min_lower_limit = max(self.min_val, current_min - self.max_gradient)
        min_upper_limit = min(self.max_val, current_min + self.max_gradient)
        new_min = randint(min_lower_limit, min_upper_limit)

        # randomly select the new maximum charge cost
        max_lower_limit = max(self.min_val, current_max - self.max_gradient)
        max_upper_limit = min(self.max_val, current_max + self.max_gradient)
        new_max = min(randint(max_lower_limit, max_upper_limit), new_min)  # we avoid threshold crosses

        # Update configuration
        new_state['edcs'][edc_id]['sg_config']['manager_config']['min_discharge_cost'] = new_min * self.scale
        new_state['edcs'][edc_id]['sg_config']['manager_config']['max_charge_cost'] = new_max * self.scale

    def copy_config(self, edc_id: str, new_state: dict[str, Any]):
        new_min = new_state['edcs'][edc_id]['sg_config']['manager_config']['min_discharge_cost']
        new_max = new_state['edcs'][edc_id]['sg_config']['manager_config']['max_charge_cost']
        for edc_id in new_state['edcs']:
            new_state['edcs'][edc_id]['sg_config']['manager_config']['min_discharge_cost'] = new_min
            new_state['edcs'][edc_id]['sg_config']['manager_config']['max_charge_cost'] = new_max


class MoveProcessingUnits(MoveEdgeDataCenters):
    def __init__(self, **kwargs):
        """
        Changes the number of PUs on an EDC.

        :param pu_types: list with the ID of the PU types to be modified.
        :param n_pus: maximum number of PU types to be modified in each iteration for each target EDC.
        :param kwargs: see [`MoveEdgeDataCenters`] for more details.
        """
        super().__init__(**kwargs)
        self.pu_types: list[str] = kwargs['pu_types']
        self.n_pus: int = kwargs.get('n_pus', len(self.pu_types))

    def move_edc(self, edc_id: str, new_state: dict[str, Any]):
        """
        Changes the number of PUs on a given EDC.

        :param edc_id: ID of the target EDC.
        :param new_state: reference to the new scenario state. Movements are done in-place.
        """
        target_config = {p: t for p, t in new_state['edcs'][edc_id]['pus'].items()}  # copy of EDC configuration
        pu_types = [pu_type for pu_type in self.pu_types]  # copy of target PU types
        for _ in range(self.n_pus):
            # select a random PU type
            try:
                shuffle(pu_types)
                pu_type = pu_types.pop()
            except IndexError:
                break
            # get current number of PUs of the given type in the EDC
            current_n_pus = list(target_config.values()).count(pu_type)
            # remove PUs of target type in the EDC
            target_config = {p: t for p, t in target_config.items() if t != pu_type}

            # randomly select a new number of PUs of the selected type
            min_limit = max(self.min_val[pu_type], current_n_pus - self.max_gradient[pu_type])
            max_limit = min(self.max_val[pu_type], current_n_pus + self.max_gradient[pu_type])
            new_n_pus = randint(min_limit, max_limit + 1)

            # add the required number of PUs
            for i in range(new_n_pus):
                pu_id = f'{pu_type}_{i}'
                while pu_id in target_config:
                    pu_id = f'{pu_id}_{i}'
                target_config[pu_id] = pu_type
        # update the new configuration
        new_state['edcs'][edc_id]['pus'] = target_config

    def copy_config(self, edc_id: str, new_state: dict[str, Any]):
        # we only copy the PUs of the PU type
        new_config = {p: t for p, t in new_state['edcs'][edc_id]['pus'].items() if t in self.pu_types}
        for edc_id in new_state['edcs']:
            # first, we only keep non-targeted PUs...
            edc_config = {p: t for p, t in new_state['edcs'][edc_id]['pus'].items() if t not in self.pu_types}
            # ... and copy the configuration of targeted PUs
            for p, t in new_config.items():
                edc_config[p] = t
            new_state['edcs'][edc_id]['pus'] = edc_config


# TODO add AggregatedMove (cuando estén las factorías)
