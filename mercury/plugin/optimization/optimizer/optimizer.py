from __future__ import annotations
import json
import os.path
from mercury.config import MercuryConfig
from mercury.msg.packet import PacketInterface, AppPacket
from random import random
from time import time
from typing import Any, Callable, Type
from ..cost_function import CostFunction
from ..move_function import MoveFunction
import csv


class OptimizerState:
    def __init__(self, cost_function: CostFunction, raw_config: dict[str, Any], base_dir: str,
                 interval: float, lite: bool = True, p_type: Type[PacketInterface] = AppPacket):
        """
        State configuration for a given optimization.

        :param cost_function: cost function to evaluate the scenario.
        :param raw_config: raw configuration of the scenario.
        :param base_dir: path to the base directory.
        :param interval: simulation interval.
        :param lite: if True, simulations are executed in lite mode. It is activated by default.
        :param p_type: communication layer to use if lite is not activated. Defaults to AppPacket.
        """
        self.cost_function: CostFunction = cost_function
        self.raw_config: dict[str, Any] = raw_config
        self.base_dir: str = base_dir
        if os.path.exists(self.base_dir):
            raise AssertionError(f'directory {self.base_dir} should not exist')
        os.mkdir(self.base_dir)
        # self.n_iter: int = n_iter
        self.config_file = os.path.join(self.base_dir, 'config.json')
        with open(self.config_file, 'w') as f:
            json.dump(self.raw_config, f, indent=2, sort_keys=True)
        self.interval: float = interval
        self.lite: bool = lite
        self.p_type: Type[PacketInterface] = p_type
        self._cost: float | None = None

    def __eq__(self, other: OptimizerState):
        """
        Two scenarios are equal if their raw configuration is the same.
        :param other: other optimization state.
        :return: True if all the configuration parameters are the same.
        """
        return self.raw_config == other.raw_config

    @property
    def cost(self) -> float:
        """
        Returns the scenario cost. This cost is cache-based to save execuion time
        :return: scenario cost.
        """
        if self._cost is None:
            from mercury import Mercury
            from mercury.model import MercuryModelABC

            config = MercuryConfig.from_json(self.config_file)
            model = MercuryModelABC.new_mercury(config, self.lite, self.p_type)
            model.add_transducers('transducer', 'csv', {'output_dir': self.base_dir})
            mercury = Mercury(model)
            mercury.start_simulation(time_interv=self.interval, log_time=False)
            self._cost = self.cost_function.cost(self.base_dir)
        return self._cost


class Optimizer:
    def __init__(self, **kwargs):
        """
        Base optimizer class.

        :param dict[str, Any] initial_state:
        :param float min_cost: minimum cost. If optimizer reaches this minimum, optimization stops. It defaults to None
        :param CostFunction cost_function: cost function used by the optimizer. It tries to minimize it.
        :param MoveFunction move_function: scenario move function.
        :param str base_dir: base directory. It must contain a config.json file with the initial configuration.
        :param float interval: simulation interval applied to each evaluation.
        :param bool lite: if true, it uses the Mercury lite version.
        :param Type[PacketInterface] p_type: package type. By default, it is set to AppPacket.
        :param kwargs: any additional parameter required by the class specialization.
        """
        self.current_state: OptimizerState | None = None
        self.best_state: OptimizerState | None = None
        self.n_iter: int = 0

        self.min_cost: float | None = kwargs.get('min_cost')
        self.cost_function: CostFunction = kwargs['cost_function']
        self.move_function: MoveFunction = kwargs['move_function']

        self.preconditions: list[Callable[[dict[str, Any]], bool]] = list()

        self.base_dir: str = kwargs['base_dir']
        with open(os.path.join(self.base_dir, 'initial_config.json')) as file:
            raw_config = json.load(file)
        self.interval: float = kwargs['interval']
        self.lite: bool = kwargs.get('lite', True)
        self.p_type: Type[PacketInterface] = kwargs.get('p_type', AppPacket)
        initial_state_dir = os.path.join(self.base_dir, 'initial_state')
        self.initial_state = OptimizerState(self.cost_function, raw_config, initial_state_dir,
                                            self.interval, self.lite, self.p_type)

    def reset(self):
        """Resets the variables that are altered on a per-run basis of the algorithm"""
        self.current_state = self.initial_state
        self.best_state = self.current_state
        self.n_iter = 0

    def add_precondition(self, function: Callable[[dict[str, Any]], bool]):
        self.preconditions.append(function)
    
    def check_preconditions(self, state: dict[str, Any]) -> bool:
        return not self.preconditions or all(precondition(state) for precondition in self.preconditions)

    def new_raw_candidate(self, prev_raw_state: dict[str, Any]) -> dict[str, Any] | None:
        new_raw_config = self.move_function.move(prev_raw_state)
        while not self.check_preconditions(new_raw_config):
            new_raw_config = self.move_function.move(prev_raw_state)
        return new_raw_config

    def new_candidate(self, prev_state: OptimizerState) -> OptimizerState | None:
        new_raw_neighbor = self.new_raw_candidate(prev_state.raw_config)
        if new_raw_neighbor is None:
            return None
        base_dir = os.path.join(self.base_dir, f'iter_{self.n_iter}')
        return OptimizerState(self.cost_function, new_raw_neighbor, base_dir,
                              self.interval, self.lite, self.p_type)

    def run(self, n_iterations: int, verbose: bool = True, log: bool = True) -> OptimizerState:
        self.reset()
        early_break = None
        file, csv_writer = None, None
        if log:
            log_path = os.path.join(self.base_dir, 'optimization_log.csv')
            file = open(log_path, 'w', newline='')
            csv_writer = csv.writer(file, delimiter=',')
            csv_writer.writerow(['n_iter', 't_start', 't_stop', 'candidate_cost',
                                 'acceptance_p', 'accepted', 'current_cost', 'best_cost'])
            file.flush()
        for i in range(n_iterations):
            self.n_iter = i
            early_break = self.run_iteration(csv_writer)
            if file is not None:
                file.flush()
            if self.current_state.cost < self.best_state.cost:
                self.best_state = self.current_state
                if self.min_cost is not None and self.best_state.cost < self.min_cost:
                    early_break = 'REACHED MINIMUM COST'
            if verbose:
                print(f'(iteration {self.n_iter + 1}) Best cost: {self.best_state.cost}')
            if early_break is not None:
                break
        if early_break is None:
            early_break = 'REACHED MAXIMUM ITERATIONS'
        print(f'TERMINATING - {early_break}')
        if file is not None:
            file.close()
        return self.best_state

    def run_iteration(self, csv_writer) -> str | None:
        t_start = time()
        candidate = self.new_candidate(self.current_state)
        if candidate is None:
            return 'UNABLE TO GENERATE A VALID CANDIDATE'
        p = self.acceptance_p(candidate)
        accepted = p >= random()
        if accepted:
            self.current_state = candidate
        t_stop = time()
        if csv_writer is not None:
            csv_writer.writerow([self.n_iter, t_start, t_stop, candidate.cost, p,
                                 accepted, self.current_state.cost, self.best_state.cost])
        return None

    def acceptance_p(self, candidate: OptimizerState) -> float:
        """
        Returns the probability to move the current state to a new candidate.

        :param candidate: a state
        :return: acceptance probability
        """
        return 1 if candidate.cost < self.current_state.cost else 0
