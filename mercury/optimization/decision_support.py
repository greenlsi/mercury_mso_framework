from __future__ import annotations
import os.path
import json
from mercury.msg.packet import PacketInterface, AppPacket
from mercury.plugin import AbstractFactory, CostFunction, MoveFunction, Optimizer
from typing import Type


class DecisionSupport:
    def __init__(self, initial_config: str, base_dir: str, interval: float,
                 lite: bool = True, p_type: Type[PacketInterface] = AppPacket):
        """
        Decision support Class for smart grid optimization.
        """
        if not os.path.exists(initial_config):
            raise AssertionError(f'{initial_config} does not exist')
        if os.path.exists(base_dir):
            raise AssertionError(f'{base_dir} should not exist')
        self.base_dir: str = base_dir
        os.mkdir(self.base_dir)
        os.system(f'cp {initial_config} {os.path.join(self.base_dir, "initial_config.json")}')
        self.interval: float = interval
        self.lite: bool = lite
        self.p_type: Type[PacketInterface] = p_type

        self.cost_function: CostFunction | None = None
        self.move_function: MoveFunction | None = None
        self.optimizer: Optimizer | None = None

    def create_cost_function(self, function_id: str, **kwargs):
        self.cost_function = AbstractFactory.create_cost_function(function_id, **kwargs)

    def create_move_function(self, function_id: str, **kwargs):
        self.move_function = AbstractFactory.create_move_function(function_id, **kwargs)
        
    def create_optimizer(self, optimizer_id: str, **kwargs):
        if self.cost_function is None:
            raise AssertionError('you must first select the cost function')
        if self.move_function is None:
            raise AssertionError('you must first select the move function')

        self.optimizer = AbstractFactory.create_optimizer(optimizer_id, **kwargs, cost_function=self.cost_function,
                                                          move_function=self.move_function, interval=self.interval,
                                                          lite=self.lite, base_dir=self.base_dir, p_type=self.p_type)
        
    def run_optimization(self, n_iterations: int, verbose: bool = True, log: bool = True):
        self.optimizer.run(n_iterations, verbose, log)
        best_state = self.optimizer.best_state
        if best_state is not None:
            best_config_path = os.path.join(self.base_dir, 'best_config.json')
            with open(best_config_path, 'w') as f:
                json.dump(best_state.raw_config, f, indent=2, sort_keys=True)
