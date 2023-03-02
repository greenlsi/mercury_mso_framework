import mercury.logger as logger
from mercury.config import MercuryConfig
from mercury.model import MercuryModelABC
from mercury import Mercury
from mercury.msg import *

alpha = 1
stacked = False
lite = True
p_type = PhysicalPacket
sg = False

T_END = 2000


if __name__ == '__main__':
    
    # SET LOGGING IF NEEDED
    logger.set_logger_level('FATAL')
    logger.add_file_handler('mercury.log')
    
    # READ CONFIGURATION FROM JSON FILE
    config = MercuryConfig.from_json("config.json")
       
    # ONCE THE CONFIGURATION IS DONE, WE BUILD THE DEVS MODEL
    model = MercuryModelABC.new_mercury(config, lite, p_type)
    # WE MAY WANT TO ADD TRANSDUCERS TO THE MODEL
    model.add_transducers('transducer', 'csv', {'output_dir': 'res/'})

    # ONCE MODEL IS DESCRIBED, WE RUN THE SIMULATION
    mercury = Mercury(model)
    mercury.start_simulation(time_interv=T_END, log_time=True)

    # AFTER RUNNING THE SIMULATION, WE CAN REPRESENT SOME RESULTS
    mercury.plot_srv_delay('res/transducer_srv_report_events.csv', alpha=alpha)
    mercury.plot_srv_delay('res/transducer_srv_report_events.csv', req_type='OpenSessRequest', alpha=alpha)
    mercury.plot_srv_delay('res/transducer_srv_report_events.csv', req_type='SrvRequest', alpha=alpha)
    mercury.plot_srv_delay('res/transducer_srv_report_events.csv', req_type='CloseSessRequest', alpha=alpha)
    if not lite and p_type == PhysicalPacket:
        mercury.plot_network_bw('res/transducer_network_events.csv', alpha=alpha)
        mercury.plot_network_bw('res/transducer_network_events.csv', alpha=alpha)
    mercury.plot_edc_power_demand('res/transducer_edc_report_events.csv', stacked=stacked, alpha=alpha)
    mercury.plot_edc_it_power('res/transducer_edc_report_events.csv', stacked=stacked, alpha=alpha)
    mercury.plot_edc_cooling_power('res/transducer_edc_report_events.csv', stacked=stacked, alpha=alpha)
    if sg:
        mercury.plot_edc_power_consumption('res/transducer_smart_grid_events.csv', stacked=stacked, alpha=alpha)
        mercury.plot_edc_power_storage('res/transducer_smart_grid_events.csv', stacked=stacked, alpha=alpha)
        mercury.plot_edc_power_generation('res/transducer_smart_grid_events.csv', stacked=stacked, alpha=alpha)
        mercury.plot_edc_energy_stored('res/transducer_smart_grid_events.csv', alpha=alpha)
