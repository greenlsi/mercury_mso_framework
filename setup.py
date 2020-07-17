from setuptools import setup, find_namespace_packages

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
    packages=find_namespace_packages(include=["mercury.*"]),
    include_package_data=True,
    entry_points={
        'mercury.sdn_strategy.plugins': [
            'closest = mercury.fog_model.core.sdn_strategy:SDNClosestStrategy',
        ],
        'mercury.edc.dispatching.plugins': [
            'emptiest_rack_emptiest_pu = mercury.fog_model.edge_fed.edc.dispatching.dispatching:EmptiestRackEmptiestProcessingUnit',
            'emptiest_rack_fullest_pu = mercury.fog_model.edge_fed.edc.dispatching.dispatching:EmptiestRackFullestProcessingUnit',
            'fullest_rack_emptiest_pu = mercury.fog_model.edge_fed.edc.dispatching.dispatching:FullestRackEmptiestProcessingUnit',
            'fullest_rack_fullest_pu = mercury.fog_model.edge_fed.edc.dispatching.dispatching:FullestRackFullestProcessingUnit',
        ],
        'mercury.edc.pu_pwr.plugins': [
            'idle_active = mercury.fog_model.edge_fed.edc.rack.pu.pu_pwr.pu_pwr_idle_active:IdleActivePowerModel',
            'static_dyn = mercury.fog_model.edge_fed.edc.rack.pu.pu_pwr.pu_pwr_static_dyn:StaticDynamicPowerModel',
        ],
        'mercury.edc.pu_temp.plugins': [],  # TODO
        'mercury.edc.rack_pwr.plugins': [],  # TODO
        'mercury.edc.rack_temp.plugins': [],  # TODO
        'mercury.edc.pwr_source.plugins': [
            'static = mercury.fog_model.edge_fed.edc.pwr_source.pwr_source_static:PowerSourceStatic',
        ],
        'mercury.edc.pwr_storage.plugins': [  # TODO new EDC model (power storage isolation)
            'pwr_storage = mercury.fog_model.edge_fed.edc.pwr_storage.pwr_storage:PowerStorage',
        ],
        'mercury.network.attenuation.plugins': [
            'fspl = mercury.fog_model.network.attenuation:FreeSpacePathLossAttenuation',
            'fiber = mercury.fog_model.network.attenuation:FiberLinkAttenuation',
        ],
        'mercury.network.channel_division.plugins': [
            'equal = mercury.fog_model.network.channel_division:EqualChannelDivision',
            'proportional = mercury.fog_model.network.channel_division:ProportionalChannelDivision',
        ],
        'mercury.network.noise.plugins': [
            'thermal = mercury.fog_model.network.noise:ThermalNoise',
        ],
        'mercury.mobility.plugins': [
            'still = mercury.fog_model.network.mobility:NodeMobilityStill',
            '2D-function = mercury.fog_model.network.mobility:NodeMobility2DFunction',
            'history = mercury.fog_model.network.mobility:NodeMobilityHistory',
        ],
        'mercury.transducers.plugins': [
            'csv = mercury.fog_model.transducers.transducers_csv:CSVTransducerBuilder',
            'mysql = mercury.fog_model.transducers.transducers_mysql:MySQLTransducerBuilder',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/greenlsi/mercury_mso_framework/issues',
        'Source': 'https://github.com/greenlsi/mercury_mso_framework',
        'Cite': 'https://doi.org/10.1016/j.simpat.2019.102037',
    },
)
