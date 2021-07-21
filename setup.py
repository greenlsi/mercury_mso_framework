from setuptools import setup, find_packages

setup(
    name='mercury',
    version=0.1,
    description='Edge Computing Federation Modeling and Simulation Tool',
    author='Román Cárdenas Rodríguez',
    author_email='r.cardenas@upm.es',
    classifiers=[
        'Development Status :: 3 Alpha',
        'License :: OSI Approved :: Apache Software License 2.0 (Apache-2.0)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    packages=find_packages(include=["mercury", "mercury.*"]),
    install_requires=[
        'matplotlib>=3.4.0',
        'numpy>=1.19.0',
        'pandas>=1.3.0',
        'scikit-learn==0.22.1',
        'xdevs>=2.2',
    ],
    entry_points={
        'mercury.cnfs.sdn_strategy.plugins': [
            'closest = mercury.plugin.cnfs.sdn_strategy:ClosestEDCStrategy',
            'emptiest = mercury.plugin.cnfs.sdn_strategy:EmptiestEDCStrategy',
            'fullest = mercury.plugin.cnfs.sdn_strategy:FullestEDCStrategy',
            'emptiest_slice = mercury.plugin.cnfs.sdn_strategy:EmptiestEDCSliceStrategy',
            'fullest_slice = mercury.plugin.cnfs.sdn_strategy:FullestEDCSliceStrategy',
            'power_balance = mercury.plugin.cnfs.sdn_strategy:PowerBalanceConsumptionStrategy',
            'highest_power = mercury.plugin.cnfs.sdn_strategy:HighestPowerConsumptionStrategy',
            'electricity_offer = mercury.plugin.cnfs.sdn_strategy:BestElectricityOfferStrategy',
            'smart_grid_closest = mercury.plugin.cnfs.sdn_strategy:SmartGridClosestEDCStrategy',
            'smart_grid_emptiest = mercury.plugin.cnfs.sdn_strategy:SmartGridEmptiestEDCStrategy',
            'smart_grid_fullest = mercury.plugin.cnfs.sdn_strategy:SmartGridFullestEDCStrategy',
            'smart_grid_emptiest_slice = mercury.plugin.cnfs.sdn_strategy:SmartGridEmptiestEDCSliceStrategy',
            'smart_grid_fullest_slice = mercury.plugin.cnfs.sdn_strategy:SmartGridFullestEDCSliceStrategy',
        ],
        'mercury.cnfs.demand_estimation.plugins': [
            'static = mercury.plugin.cnfs.demand_estimation:DemandEstimationGeneratorStatic',
            'history = mercury.plugin.cnfs.demand_estimation:DemandEstimationGeneratorHistory',
        ],
        'mercury.smart_grid.consumption_manager.plugins': [
            'static = mercury.plugin.smart_grid.consumption_manager:StaticConsumptionManager',
            'min_max = mercury.plugin.smart_grid.consumption_manager:MinDischargeMaxChargeConsumptionManager',
        ],
        'mercury.smart_grid.energy_provider.plugins': [
            'static = mercury.plugin.smart_grid.provider:EnergyProviderStatic',
            'history = mercury.plugin.smart_grid.provider:EnergyProviderHistory',
        ],
        'mercury.smart_grid.pwr_source.plugins': [
            'static = mercury.plugin.smart_grid.pwr_source:PowerSourceStatic',
            'history = mercury.plugin.smart_grid.pwr_source:PowerSourceHistory',
        ],
        'mercury.edc.demand_share.plugins': [
            'equal = mercury.plugin.cnfs.efc.demand_share:EqualDemandShare',
            'trend = mercury.plugin.cnfs.efc.demand_share:TrendDemandShare',
        ],
        'mercury.edc.dyn_mapping.plugins': [],  # TODO
        'mercury.edc.dyn_hot_standby.plugins': [
            'session = mercury.plugin.cnfs.efc.dyn_hot_standby:SessionDynamicHotStandby',
        ],
        'mercury.edc.dyn_slicing.plugins': [],  # TODO
        'mercury.edc.mapping.plugins': [
            'first_fit = mercury.plugin.edc.mapping:FirstFitMapping'
            'emptiest_pu = mercury.plugin.edc.mapping:EmptiestProcessingUnit',
            'fullest_pu = mercury.plugin.edc.mapping:FullestProcessingUnit',
            'less_it_pwr = mercury.plugin.edc.mapping:LessITPowerIncrement',
        ],
        'mercury.edc.hot_standby.plugins': [
            'session = mercury.plugin.edc.hot_standby:SessionHotStandby',
            'full = mercury.plugin.edc.hot_standby:FullHotStandby',
        ],
        'mercury.edc.scheduling.plugins': [
            'round_robin = mercury.plugin.edc.scheduling:RoundRobinScheduler',
            'fcfs = mercury.plugin.edc.scheduling:FirstComeFirstServed',
            'sjf = mercury.plugin.edc.scheduling:ShortestJobFirst',
            'ljf = mercury.plugin.edc.scheduling:LongestJobFirst',
            'srtf = mercury.plugin.edc.scheduling:ShortestRemainingTimeFirst',
            'lrtf = mercury.plugin.edc.scheduling:LongestRemainingTimeFirst',
        ],
        'mercury.edc.pu.pwr.plugins': [
            'idle_active = mercury.plugin.edc.pu_pwr:IdleActivePowerModel',
            'static_dyn = mercury.plugin.edc.pu_pwr:StaticDynamicPowerModel',
        ],
        'mercury.edc.pu.temp.plugins': [],  # TODO
        'mercury.edc.rack.cooler_pwr.plugins': [
            'static = mercury.plugin.edc.cooler_pwr:StaticCoolerPowerModel',
            '2_phase_immersion = mercury.plugin.edc.cooler_pwr:TwoPhaseImmersionCoolerPowerModel',
        ],
        'mercury.edc.rack.cooler_temp.plugins': [],  # TODO
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
            'still = mercury.plugin.network.mobility:NodeMobilityStill',
            '2D_function = mercury.plugin.network.mobility:NodeMobility2DFunction',
            'history = mercury.plugin.network.mobility:NodeMobilityHistory',
        ],
        'mercury.service.request_profile.plugins': [
            'periodic = mercury.plugin.service.request_profile:PeriodicRequestProfile',
            'uniform = mercury.plugin.service.request_profile:UniformDistributionRequestProfile',
            'gaussian = mercury.plugin.service.request_profile:GaussianDistributionRequestProfile',
            'exponential = mercury.plugin.service.request_profile:ExponentialDistributionRequestProfile',
            'lambda = mercury.plugin.service.request_profile:LambdaDrivenRequestProfile',
        ],
        'mercury.service.session_profile.plugins': [
            'periodic = mercury.plugin.service.session_profile:PeriodicSessionProfile',
            'uniform = mercury.plugin.service.session_profile:UniformDistributionSessionProfile',
            'gaussian = mercury.plugin.service.session_profile:GaussianDistributionSessionProfile',
            'exponential = mercury.plugin.service.session_profile:ExponentialDistributionSessionProfile',
            'lambda = mercury.plugin.service.session_profile:LambdaDrivenSessionProfile',
        ],
        'mercury.service.session_duration.plugins': [
            'fixed = mercury.plugin.service.session_duration:FixedServiceSessionDuration',
            'uniform = mercury.plugin.service.session_duration:UniformDistributionSessionDuration',
            'gaussian = mercury.plugin.service.session_duration:GaussianDistributionSessionDuration',
            'exponential = mercury.plugin.service.session_duration:ExponentialDistributionSessionDuration',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/greenlsi/mercury_mso_framework/issues',
        'Source': 'https://github.com/greenlsi/mercury_mso_framework',
        'Cite': 'https://doi.org/10.1016/j.simpat.2019.102037',
    },
)
