from keras.models import model_from_json
from sklearn.externals.joblib import load as load_scaler
from numpy import zeros as np_zeros
from mercury.fog_model import ProcessingUnitPowerModel


class Rx580PowerModel(ProcessingUnitPowerModel):
    def __init__(self, **kwargs):
        """
        Create object for Rx580 power estimation
        :param str file_path_to_model_and_scalers: File path to files containing model's weights (h5), scalers (save)
        and arch (json), extension of files not needed
        :raises FileNotFoundError
        """
        super().__init__()
        dirpath = kwargs.get('file_path_to_model_and_scalers', '.')
        with open(dirpath + '.json', 'r') as f:
            self.model = model_from_json(f.read())
        self.model.load_weights(dirpath + '.h5')
        self.scaler_x = load_scaler(dirpath + '_scaler_x.save')
        self.scaler_y = load_scaler(dirpath + '_scaler_y.save')

    def compute_power(self, status, utilization, max_u, dvfs_index, dvfs_table):  # TODO con max_u
        res = 0
        if status:
            x = np_zeros((1, 3))
            x[0, 0] = dvfs_table[dvfs_index]['memory_clock']
            x[0, 1] = dvfs_table[dvfs_index]['core_clock']
            x[0, 2] = utilization / 20.0  # TODO
            y = self.model.predict(self.scaler_x.transform(x))
            res = self.scaler_y.inverse_transform(y)[0, 0]
        return res
