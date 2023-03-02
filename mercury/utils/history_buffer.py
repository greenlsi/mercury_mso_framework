import numpy as np
import pandas as pd
from math import inf
from typing import Any, Callable, Dict


class EventHistoryBuffer:
    def __init__(self, **kwargs):
        """
        This class hides the complexity of dealing with a pandas dataframe that represents changes with time.

        :param history: pandas dataframe with the historic data.
        :param t_column: name of the time column. By default, it is set to 'time'.
        :param t_init: value of time to be considered as 'time zero'. By default, it is set to 0.
        :param t_start: time from t_init from which historic entries are not valid yet. By default, it is set to 0.
        :param t_end: time from t_init from which historic entries are no longer valid. By default, it is set to 0.
        :param modifiers: dictionary {column_name: modifier_function}. By default, it is an empty dictionary.
        :param interpolation: interpolation factor. By default, it is set to 1 (i.e., no interpolation).
        """
        self.pointer = 0
        self.t_column: str = kwargs.get('t_column', 'time')
        if 'history' in kwargs:
            history: pd.DataFrame = kwargs['history']
        else:
            filepath: str = kwargs['filepath']
            sep: str = kwargs.get('sep', ',')
            history = pd.read_csv(filepath, sep=sep)
        history = history.sort_values(by=self.t_column, ascending=True)
        t_init: float = kwargs.get('t_init', 0)
        t_start: float = kwargs.get('t_start', 0)
        t_end: float = kwargs.get('t_end', inf)
        modifiers: Dict[str, Callable[[Any], Any]] = kwargs.get('modifiers', dict())
        interpolation: int = kwargs.get('interpolation', 1)

        # 1. Modify column values
        for col, modifier in modifiers.items():
            history[col] = history[col].apply(modifier)
        # 2. Adjust time and remove invalid entries
        t_first = t_init + t_start
        t_last = t_init + t_end
        past = history[history[self.t_column] <= t_first]
        history = history[(history[self.t_column] > t_first) & (history[self.t_column] <= t_last)]
        self.initial_val = history.iloc[0] if past.empty else past.iloc[-1]
        history[self.t_column] = history[self.t_column] - t_init  # We adapt time so 0 corresponds to t_init
        # 3. Interpolate rows
        if interpolation > 1:
            n_rows, n_cols = history.shape
            history_np = np.empty(shape=[(n_rows - 1) * interpolation + 1, n_cols], dtype=object)
            history_np[:] = np.nan
            i = 0
            for index, row in history.iterrows():
                history_np[i * interpolation] = row
                i += 1
            history = pd.DataFrame(history_np, index=None, columns=history.columns)
            for col in history:
                history[col] = pd.to_numeric(history[col], errors="ignore")
            history = history.interpolate(limit_direction='both')
            history = history.ffill()
        self.history = history

    def time_of_next_event(self) -> float:
        return self.history[self.t_column].iloc[self.pointer].item() if self.pointer < self.history.shape[0] else inf

    def time_advance(self, clock: float) -> float:
        return self.time_of_next_event() - clock

    def column_exists(self, column_name: str) -> bool:
        return column_name in self.history

    def get_event(self) -> pd.Series:
        try:
            return self.history.iloc[min(self.pointer, self.history.shape[0] - 1)]
        except IndexError:  # history buffer is empty (i.e., we only had one point)
            return self.initial_val

    def advance(self):
        time = self.time_of_next_event()
        while self.pointer < self.history.shape[0] and self.history[self.t_column].iloc[self.pointer].item() <= time:
            self.pointer += 1
