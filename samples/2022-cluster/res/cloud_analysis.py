from __future__ import annotations
import pandas as pd
from datetime import datetime
from math import ceil, floor
import matplotlib.pyplot as plt
import matplotlib.dates as mdate
from mercury.analysis.metrics import time_to_epoch


JUNE_6 = 1212735600
DIRECTORY = '06_edge_slice_proactive_30'
# DIRECTORY = '11_edge_slice_hybrid_20'

PUE: float = 1.5
MAX_SESS: int = 5
PU_POWER: list[float] = [88.278755, 97.26515, 105.19226, 107.77093, 109.1158, 110.41844]
MAX_T = 86400


def clean(dirname: str):
    df = pd.read_csv(f'{dirname}/transducer_cloud_events.csv', index_col=None)
    df = df[(df['req_type'] == 'OpenSessRequest') & (df['result'] == 'met_deadline')]
    df.drop(['cloud_id', 'service_id', 'req_type', 'result', 'window_n',
             'window_acc_delay', 'window_mean_delay'], axis=1, inplace=True)
    df.loc[len(df.index)] = df.iloc[-1, :]
    df.iloc[-1, 0] = MAX_T

    # max_pus: int = ceil(df['n_clients'].max() / MAX_SESS)
    df['max_pus'] = ceil(df['n_clients'].max() / MAX_SESS)
    df['full_pus'] = df['n_clients'].apply(lambda x: floor(x / MAX_SESS))
    df['hanging_sessions'] = df['n_clients'] % MAX_SESS
    df['idle_pus'] = df['max_pus'] - df['full_pus'] - df['hanging_sessions'].apply(lambda x: 0 if x == 0 else 1)
    df['it_power'] = df['idle_pus'] * PU_POWER[0] + df['full_pus'] * PU_POWER[5] + \
                     df['hanging_sessions'].apply(lambda x: PU_POWER[int(x)] if x > 0 else 0)
    df['others_power'] = df['it_power'] * (PUE - 1)
    df['total_power'] = df['it_power'] * PUE
    df['utilization'] = df['n_clients'] / (df['max_pus'] * MAX_SESS)

    aux = df[['time', 'it_power', 'others_power', 'total_power']]
    aux = aux.shift(periods=1, fill_value=0)
    aux.iloc[0, 1:] = aux.iloc[1, 1:]
    df['it_energy'] = (aux['it_power'] * (df['time'] - aux['time']) / 3600).cumsum()
    df['others_energy'] = (aux['others_power'] * (df['time'] - aux['time']) / 3600).cumsum()
    df['total_energy'] = (aux['total_power'] * (df['time'] - aux['time']) / 3600).cumsum()

    df.to_csv(f'{dirname}/cloud_analysis.csv', index=False)
    time_to_epoch(JUNE_6, f'{dirname}/cloud_analysis.csv', f'{dirname}/cloud_analysis_epoch.csv')


def describe(dirname: str):
    df = pd.read_csv(f'{dirname}/cloud_analysis.csv')
    # df = df.iloc[50:, :]  # We get rid of first 50 rows to obtain more reliable results
    print(f'Maximum number of PUs: {df["max_pus"].max()}')
    print(f'Demand: {df["n_clients"].min()}; {df["n_clients"].mean()}; {df["n_clients"].max()}')

    aux = df[['time', 'utilization']].shift(periods=1, fill_value=0)
    mean_u = (aux['utilization'] * (df['time'] - aux['time'])).sum() / 86400
    print(f'Utilization: {df["utilization"].min()}; {mean_u}; {df["utilization"].max()}')

    it_energy = df["it_energy"].max()
    others_energy = df["others_energy"].max()
    total_energy = df["total_energy"].max()
    print(f'IT energy consumption (Wh): {it_energy}')
    print(f'Others energy consumption (Wh): {others_energy}')
    print(f'Total energy consumption (Wh): {total_energy}')
    for col_name, energy in ('it_power', it_energy), ('others_power', others_energy), ('total_power', total_energy):
        print(f'{col_name} (W): {df[col_name].min()}; {energy * 3600 / 86400}; {df[col_name].max()}')


def plot_demand(dirname: str):
    df = pd.read_csv(f'{dirname}/cloud_analysis_epoch.csv', index_col=None)
    df = df.iloc[50:, :]  # We get rid of first 50 rows to obtain more beautiful graphs

    fig, ax = plt.subplots(figsize=(12, 6))

    # The 25200 thing compensates the time zone in San Francisco
    secs = df['epoch'].apply(lambda i: mdate.date2num(datetime.utcfromtimestamp(i - 25200)))
    ax.plot_date(secs, df['n_clients'], fmt='-', linewidth='3')

    date_fmt = '%H:%M:%S'
    date_formatter = mdate.DateFormatter(date_fmt)
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=0)

    plt.title("Cloud demand", fontsize=35)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("clients", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.savefig(f'{dirname}/cloud_demand.pdf')
    plt.show()


def plot_power(dirname: str):
    df = pd.read_csv(f'{dirname}/cloud_analysis_epoch.csv', index_col=None)
    df = df.iloc[50:, :]  # We get rid of first 50 rows to obtain more beautiful graphs

    fig, ax = plt.subplots(figsize=(12, 6))

    # The 25200 thing compensates the time zone in San Francisco
    secs = df['epoch'].apply(lambda i: mdate.date2num(datetime.utcfromtimestamp(i - 25200)))
    ax.plot_date(secs, df['total_power'], fmt='-', linewidth='3', label='total')
    ax.plot_date(secs, df['it_power'], fmt='-', linewidth='3', label='IT')
    ax.plot_date(secs, df['others_power'], fmt='-', linewidth='3', label='others')

    date_fmt = '%H:%M:%S'
    date_formatter = mdate.DateFormatter(date_fmt)
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=0)

    # plt.title("Cloud power consumption", fontsize=35)
    plt.legend(loc='lower right', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("power [W]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    # plt.savefig(f'{dirname}/cloud_power.pdf')
    plt.savefig(f'{dirname}/res_edge_none_cloud_power.pdf')
    plt.show()


if __name__ == '__main__':
    # clean(DIRECTORY)
    describe(DIRECTORY)
    # plt.rcParams["font.family"] = "Times New Roman"
    # plt.rcParams['axes.grid'] = True
    # plot_demand(DIRECTORY)
    # plot_power(DIRECTORY)
