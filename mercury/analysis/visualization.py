import pandas as pd
import matplotlib.dates as mdate
from matplotlib.figure import Figure
from matplotlib.axes import Axes


def plot_edc_step_data(df: pd.DataFrame, target_col: str, fig: Figure, ax: Axes,
                       edc_col: str = 'edc_id', linewidth: str = '2', epoch: bool = False, fill_negative: bool = False):
    edc_ids = df[edc_col].unique().tolist()
    edc_ids.sort()
    for edc_id in edc_ids:
        edc_df = df[df[edc_col] == edc_id]
        secs = mdate.epoch2num(edc_df['epoch']) if epoch else edc_df['time']
        ax.step(secs, edc_df[target_col], where='post', linewidth=linewidth, label=edc_id)

        if fill_negative:
            ax.fill_between(secs, 0, 1, where=edc_df[target_col] < 0,
                            color='blue', alpha=0.2, transform=ax.get_xaxis_transform())

    if epoch:
        date_formatter = mdate.DateFormatter('%H:%M:%S')
        ax.xaxis.set_major_formatter(date_formatter)
        fig.autofmt_xdate()


def plot_edc_line_data(df: pd.DataFrame, target_col: str, fig: Figure, ax: Axes,
                       edc_col: str = 'edc_id', linewidth: str = '2', epoch: bool = False):
    edc_ids = df[edc_col].unique().tolist()
    edc_ids.sort()
    for edc_id in edc_ids:
        edc_df = df[df[edc_col] == edc_id]
        secs = mdate.epoch2num(edc_df['epoch']) if epoch else edc_df['time']
        ax.plot(secs, edc_df[target_col], linewidth=linewidth, label=edc_id)

    if epoch:
        date_formatter = mdate.DateFormatter('%H:%M:%S')
        ax.xaxis.set_major_formatter(date_formatter)
        fig.autofmt_xdate()
