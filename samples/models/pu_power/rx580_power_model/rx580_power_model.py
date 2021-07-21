from functools import lru_cache
from typing import Dict
from numpy import zeros as np_zeros
from joblib import load as load_scaler
from tensorflow.keras.models import model_from_json
# from keras.models import model_from_json
from mercury.plugin import ProcessingUnitPowerModel


class Rx580Aux:
    model = None
    scaler_x = None
    scaler_y = None

    def __init__(self, dirpath):
        if Rx580Aux.model is None:
            with open(dirpath + '.json', 'r') as f:
                Rx580Aux.model = model_from_json(f.read())
            Rx580Aux.model.load_weights(dirpath + '.h5')
            Rx580Aux.scaler_x = load_scaler(dirpath + '_scaler_x.joblib')
            Rx580Aux.scaler_y = load_scaler(dirpath + '_scaler_y.joblib')

    @lru_cache(maxsize=32)
    def predict(self, memory_clock: float, core_clock: float, utilization: float):
        x = np_zeros((1, 3))
        x[0, 0] = memory_clock
        x[0, 1] = core_clock
        x[0, 2] = utilization / 20.0  # TODO esto es lo raro
        y = Rx580Aux.model.predict(Rx580Aux.scaler_x.transform(x))
        return Rx580Aux.scaler_y.inverse_transform(y)[0, 0]


class Rx580PowerModel(ProcessingUnitPowerModel):
    def __init__(self, **kwargs):
        """
        Create object for Rx580 power estimation

        :param str file_path_to_model_and_scalers: File path to files containing model's weights (h5), scalers (save)
        and arch (json), extension of files not needed
        :raises FileNotFoundError if any of the required files do not exist.
        """
        super().__init__()
        dirpath = kwargs.get('file_path_to_model_and_scalers', '.')
        Rx580Aux(dirpath)

    def compute_power(self, status: bool, utilization: float, dvfs_config: Dict[str, float]) -> float:
        res = 0
        if status:
            x = np_zeros((1, 3))
            x[0, 0] = dvfs_config['memory_clock']
            x[0, 1] = dvfs_config['core_clock']
            x[0, 2] = utilization / 20.0  # TODO esto es lo raro
            y = Rx580Aux.model.predict(Rx580Aux.scaler_x.transform(x))
            res = Rx580Aux.scaler_y.inverse_transform(y)[0, 0]
        return res
