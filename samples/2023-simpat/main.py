from mercury.optimization.decision_support import DecisionSupport

T_START = 1212735600
T_END = 1212822000
N_ITERS = 300

OPTIMIZERS = {
    'simulated_annealing': {
        't_max': 200,
        'schedule_constant': .95,
    },
    'stc_hill_climbing': {
        'temp': .1,
    },
    'tabu_search': {
        'n_candidates': 10,
        'tabu_size': 50,
        'parallel': True,
    },
}


if __name__ == '__main__':
    for opt_id, opt_config in OPTIMIZERS.items():

        decision_support = DecisionSupport('config_difficult.json', opt_id, T_END - T_START)

        decision_support.create_cost_function('energy')
        decision_support.create_move_function('charge_discharge', n_edcs=3, max_val=59,
                                              min_val=14, max_gradient=5, scale=1e-6)

        decision_support.create_optimizer(opt_id, **opt_config)
        
        n_iters = 100 if opt_id == 'tabu_search' else N_ITERS

        decision_support.run_optimization(n_iters)
