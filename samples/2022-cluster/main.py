import mercury.logger as logger
from mercury.config import MercuryConfig
from mercury.model import MercuryModelABC
from mercury import Mercury
from mercury.msg import *

alpha = 1
stacked = False
lite = True
p_type = PhysicalPacket

# N_VEHICLES = 100
T_START = 1212735600
T_END = 1212822000
RES_DIR = 'res/19_sg_us3000c_strict'


if __name__ == '__main__':
    # SET LOGGING IF NEEDED
    logger.set_logger_level('WARNING')
    logger.add_stream_handler()
    
    # READ CONFIGURATION FROM JSON FILE
    config = MercuryConfig.from_json(f'{RES_DIR}/config.json')
       
    # ONCE THE CONFIGURATION IS DONE, WE BUILD THE DEVS MODEL
    model = MercuryModelABC.new_mercury(config, lite, p_type)
    # WE MAY WANT TO ADD TRANSDUCERS TO THE MODEL
    model.add_transducers('transducer', 'csv', {'output_dir': RES_DIR})

    # ONCE MODEL IS DESCRIBED, WE RUN THE SIMULATION
    mercury = Mercury(model)
    mercury.start_simulation(time_interv=T_END - T_START, log_time=True)


    # AFTER RUNNING THE SIMULATION, WE CAN REPRESENT SOME RESULTS
    """
    mercury.plot_srv_delay(f'{RES_DIR}/transducer_srv_report_events.csv', alpha=alpha)
    mercury.plot_srv_delay(f'{RES_DIR}/transducer_srv_report_events.csv', req_type='OpenSessRequest', alpha=alpha)
    mercury.plot_srv_delay(f'{RES_DIR}/transducer_srv_report_events.csv', req_type='SrvRequest', alpha=alpha)
    mercury.plot_srv_delay(f'{RES_DIR}/transducer_srv_report_events.csv', req_type='CloseSessRequest', alpha=alpha)
    if not lite and p_type == PhysicalPacket:
        mercury.plot_network_bw(f'{RES_DIR}/transducer_network_events.csv', alpha=alpha)
        mercury.plot_network_bw(f'{RES_DIR}/transducer_network_events.csv', alpha=alpha)
    if mercury.model.edcs is not None:
        mercury.plot_edc_power_demand(f'{RES_DIR}/transducer_edc_report_events.csv', stacked=stacked, alpha=alpha)
        # mercury.plot_edc_it_power(f'{RES_DIR}/transducer_edc_report_events.csv', stacked=stacked, alpha=alpha)
        # mercury.plot_edc_cooling_power(f'{RES_DIR}/transducer_edc_report_events.csv', stacked=stacked, alpha=alpha)
    if mercury.model.smart_grid is not None:
        mercury.plot_edc_power_consumption(f'{RES_DIR}/transducer_smart_grid_events.csv', stacked=stacked, alpha=alpha)
        mercury.plot_edc_power_storage(f'{RES_DIR}/transducer_smart_grid_events.csv', stacked=stacked, alpha=alpha)
        mercury.plot_edc_power_generation(f'{RES_DIR}/transducer_smart_grid_events.csv', stacked=stacked, alpha=alpha)
        mercury.plot_edc_energy_stored(f'{RES_DIR}/transducer_smart_grid_events.csv', alpha=alpha)
    """
