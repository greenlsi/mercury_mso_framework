from setuptools import setup, find_packages

setup(
    name='mercury',
    version='0.2',
    description='Edge Computing Federation Modeling and Simulation Tool',
    author='Román Cárdenas Rodríguez',
    author_email='r.cardenas@upm.es',
    classifiers=[
        'Development Status :: 3 Alpha',
        'License :: OSI Approved :: Apache Software License 2.0 (Apache-2.0)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
    packages=find_packages(exclude=["tests", "tests.*", "samples", "samples.*"]),
    install_requires=[
        'matplotlib>=3.7',
        'seaborn>=0.12',
        'pandas>=1.5',
        'scikit-learn>=1.2',
        'numpy>=1.17.3',
        'xdevs==2.2.1',
    ],
    entry_points={
        'mercury.cloud.network_delay.plugins': [
            'constant = mercury.plugin.cloud.network_delay:ConstantCloudNetworkDelay',
            'gaussian = mercury.plugin.cloud.network_delay:GaussianCloudNetworkDelay',
        ],
        'mercury.cloud.proc_t.plugins': [
            'constant = mercury.plugin.cloud.proc_t:ConstantProcTimeModel',
            'gaussian = mercury.plugin.cloud.proc_t:GaussianProcTimeModel',
        ],
        'mercury.smart_grid.consumer_manager.plugins': [
            'static = mercury.plugin.smart_grid.consumer_manager:StaticConsumerManager',
            'min_max = mercury.plugin.smart_grid.consumer_manager:MinDischargeMaxChargeConsumerManager',
        ],
        'mercury.smart_grid.energy_cost.plugins': [
            'constant = mercury.plugin.smart_grid.energy_cost:ConstantEnergyCostGenerator',
            'history = mercury.plugin.smart_grid.energy_cost:HistoryEnergyCostGenerator',
        ],
        'mercury.smart_grid.pwr_generation.plugins': [
            'constant = mercury.plugin.smart_grid.pwr_generation:ConstantPowerGeneration',
            'history = mercury.plugin.smart_grid.pwr_generation:HistoryPowerGeneration',
        ],
        'mercury.smart_grid.optimization.plugins': [
            'energy = mercury.plugin.smart_grid.cost_function:EnergyCostFunction',
        ],
        'mercury.edc.cooler.power.plugins': [
            'constant = mercury.plugin.edc.cooler_power:ConstantCoolerPowerModel',
            '2_phase_immersion = mercury.plugin.edc.cooler_power:TwoPhaseImmersionCoolerPowerModel',
        ],
        'mercury.edc.dyn.demand.plugins': [
            'constant = mercury.plugin.edc.dyn_demand:ConstantSrvDemandEstimator',
            'history = mercury.plugin.edc.dyn_demand:HistorySrvDemandEstimator',
            'hybrid = mercury.plugin.edc.dyn_demand:HybridSrvDemandEstimator',
        ],
        'mercury.edc.dyn.mapping.plugins': [],
        'mercury.edc.dyn.slicing.plugins': [
            'estimation = mercury.plugin.edc.dyn_slicing:EstimationSlicing',
        ],
        'mercury.edc.pu.mapping.plugins': [
            'ff = mercury.plugin.edc.pu_mapping:FirstFit',
            'epu = mercury.plugin.edc.pu_mapping:EmptiestProcessingUnit',
            'fpu = mercury.plugin.edc.pu_mapping:FullestProcessingUnit',
            'spt = mercury.plugin.edc.pu_mapping:ShortestProcessingTime',
            'lpt = mercury.plugin.edc.pu_mapping:LongestProcessingTime',
            'spi = mercury.plugin.edc.pu_mapping:SmallestPowerIncrement',
        ],
        'mercury.edc.server.mapping.plugins': [
            'closest = mercury.plugin.edc.server_mapping:ClosestEDCStrategy',
            'emptiest = mercury.plugin.edc.server_mapping:EmptiestEDCStrategy',
            'fullest = mercury.plugin.edc.server_mapping:FullestEDCStrategy',
            'pw_balance = mercury.plugin.edc.server_mapping:PowerBalanceStrategy',
            'highest_pw = mercury.plugin.edc.server_mapping:HighestPowerStrategy',
            'sg_closest = mercury.plugin.edc.server_mapping:SmartGridClosestEDCStrategy',
            'sg_emptiest = mercury.plugin.edc.server_mapping:SmartGridEmptiestEDCStrategy',
            'sg_fullest = mercury.plugin.edc.server_mapping:SmartGridFullestEDCStrategy',
        ],
        'mercury.edc.pu.proc_t.plugins': [
            'constant = mercury.plugin.edc.pu_proc_t:ConstantProcTimeModel',
            'round_robin = mercury.plugin.edc.pu_proc_t:RoundRobinProcTimeModel',
            'gaussian = mercury.plugin.edc.pu_proc_t:GaussianProcTimeModel',
        ],
        'mercury.edc.pu.power.plugins': [
            'constant = mercury.plugin.edc.pu_power:ConstantPowerModel',
            'idle_active = mercury.plugin.edc.pu_power:IdleActivePowerModel',
            'linear = mercury.plugin.edc.pu_power:LinearPowerModel',
            'static_dyn = mercury.plugin.edc.pu_power:StaticDynamicPowerModel',
        ],
        'mercury.edc.pu.scheduler.plugins': [
            'fcfs = mercury.plugin.edc.pu_scheduler:FirstComeFirstServed',
            'sjf = mercury.plugin.edc.pu_scheduler:ShortestJobFirst',
            'ljf = mercury.plugin.edc.pu_scheduler:LongestJobFirst',
            'srtf = mercury.plugin.edc.pu_scheduler:ShortestRemainingTimeFirst',
            'lrtf = mercury.plugin.edc.pu_scheduler:LongestRemainingTimeFirst',
            'edf = mercury.plugin.edc.pu_scheduler:EarliestDeadlineFirst',
            'llf = mercury.plugin.edc.pu_scheduler:LeastLaxityFirst',
        ],
        'mercury.edc.pu.temperature.plugins': [
            'constant = mercury.plugin.edc.pu_temperature:ConstantTemperatureModel',
        ],
        'mercury.network.attenuation.plugins': [
            'fspl = mercury.plugin.network.attenuation:FreeSpacePathLossAttenuation',
            'fiber = mercury.plugin.network.attenuation:FiberLinkAttenuation',
        ],
        'mercury.network.channel_division.plugins': [
            'equal = mercury.plugin.network.channel_division:EqualChannelDivision',
            'proportional = mercury.plugin.network.channel_division:ProportionalChannelDivision',
        ],
        'mercury.network.noise.plugins': [
            'thermal = mercury.plugin.network.noise:ThermalNoise',
        ],
        'mercury.mobility.plugins': [
            'still = mercury.plugin.network.mobility:StillNodeMobility',
            '2D_function = mercury.plugin.network.mobility:NodeMobility2DFunction',
            'gradient = mercury.plugin.network.mobility:GradientNodeMobility',
            'history = mercury.plugin.network.mobility:HistoryNodeMobility',
        ],
        'mercury.client.client_generator.plugins': [
            'list = mercury.plugin.client.client_generator:ListClientGenerator',
            'synthetic = mercury.plugin.client.client_generator:SyntheticClientGenerator',
            'history_wired = mercury.plugin.client.client_generator:HistoryWiredClientGenerator',
            'history_wireless = mercury.plugin.client.client_generator:HistoryWirelessClientGenerator',
        ],
        'mercury.client.srv_activity_generator.plugins': [
            'single = mercury.plugin.client.activity_generator:SingleSrvActivityGenerator',
            'periodic = mercury.plugin.client.activity_generator:PeriodicSrvActivityGenerator',
            'uniform = mercury.plugin.client.activity_generator:UniformSrvActivityGenerator',
            'gaussian = mercury.plugin.client.activity_generator:GaussianSrvActivityGenerator',
            'exponential = mercury.plugin.client.activity_generator:ExponentialSrvActivityGenerator',
            'lambda = mercury.plugin.client.activity_generator:LambdaSrvActivityGenerator',
        ],
        'mercury.client.srv_activity_window.plugins': [
            'constant = mercury.plugin.client.activity_window:ConstantSrvWindowGenerator',
            'uniform = mercury.plugin.client.activity_window:UniformSrvWindowGenerator',
            'gaussian = mercury.plugin.client.activity_window:GaussianSrvWindowGenerator',
            'exponential = mercury.plugin.client.activity_window:ExponentialSrvWindowGenerator',
            'lambda = mercury.plugin.client.activity_window:LambdaSrvSessionDuration',
        ],
        'mercury.client.srv_req_generator.plugins': [
            'single = mercury.plugin.client.req_generator:SingleSrvRequestGenerator',
            'periodic = mercury.plugin.client.req_generator:PeriodicSrvRequestGenerator',
            'uniform = mercury.plugin.client.req_generator:UniformSrvRequestGenerator',
            'gaussian = mercury.plugin.client.req_generator:GaussianSrvRequestGenerator',
            'exponential = mercury.plugin.client.req_generator:ExponentialSrvRequestGenerator',
            'lambda = mercury.plugin.client.req_generator:LambdaSrvRequestGenerator',
        ],
        'mercury.optimization.cost_function.plugins': [
            'deadlines = mercury.plugin.optimization.cost_function:DeadlinesCost',
            'energy = mercury.plugin.optimization.cost_function:EnergyCost',
        ],
        'mercury.optimization.move_function.plugins': [
            'charge_discharge = mercury.plugin.optimization.move_function:MoveChargeDischarge',
            'n_pus = mercury.plugin.optimization.move_function:MoveProcessingUnits',
        ],
        'mercury.optimization.optimizer.plugins': [
            'simulated_annealing = mercury.plugin.optimization.optimizer.simulated_annealing:SimulatedAnnealing',
            'stc_hill_climbing = mercury.plugin.optimization.optimizer.stc_hill_climbing:StochasticHillClimbing',
            'tabu_search = mercury.plugin.optimization.optimizer.tabu_search:TabuSearch',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/greenlsi/mercury_mso_framework/issues',
        'Source': 'https://github.com/greenlsi/mercury_mso_framework',
        'Cite': 'https://doi.org/10.1016/j.simpat.2019.102037',
    },
)
