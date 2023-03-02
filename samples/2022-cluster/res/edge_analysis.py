from __future__ import annotations
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdate
from mercury.analysis.metrics import time_to_epoch

JUNE_6 = 1212735600
MAX_T = 86400


def clean(dirname: str):
    df = pd.read_csv(f'{dirname}/transducer_edc_profile_events.csv', index_col=None)
    df = df[(df['req_type'] == 'OpenSessRequest') & (df['result'] == 'met_deadline')]
    df.drop(['service_id', 'req_type', 'result', 'window_n',
             'window_acc_delay', 'window_mean_delay'], axis=1, inplace=True)
    for edc_id in df['edc_id'].unique():
        edc_df = df[df['edc_id'] == edc_id]
        edc_df = edc_df.drop(['edc_id'], axis=1)
        edc_df.to_csv(f'{dirname}/{edc_id}_demand_analysis.csv', index=False)
        time_to_epoch(JUNE_6, f'{dirname}/{edc_id}_demand_analysis.csv', f'{dirname}/{edc_id}_demand_analysis_epoch.csv')

    df = pd.read_csv(f'{dirname}/transducer_edc_report_events.csv', index_col=None)
    df.drop(['adas_expected_size', 'adas_slice_size',
             'adas_free_size', 'adas_free_u'], axis=1, inplace=True)
    for edc_id in df['edc_id'].unique():
        edc_df = df[df['edc_id'] == edc_id]
        edc_df = edc_df.drop(['edc_id'], axis=1)
        edc_df.loc[len(df.index)] = edc_df.iloc[-1, :]
        edc_df.iloc[-1, 0] = MAX_T

        aux = edc_df[['time', 'it_power', 'cooling_power', 'power_demand']]
        aux = aux.shift(periods=1, fill_value=0)
        edc_df['it_energy'] = (aux['it_power'] * (edc_df['time'] - aux['time']) / 3600).cumsum()
        edc_df['cooling_energy'] = (aux['cooling_power'] * (edc_df['time'] - aux['time']) / 3600).cumsum()
        edc_df['total_energy'] = (aux['power_demand'] * (edc_df['time'] - aux['time']) / 3600).cumsum()

        edc_df.to_csv(f'{dirname}/{edc_id}_power_analysis.csv', index=False)
        time_to_epoch(JUNE_6, f'{dirname}/{edc_id}_power_analysis.csv', f'{dirname}/{edc_id}_power_analysis_epoch.csv')


def describe(dirname: str):
    for edc_id in 'edc_0', 'edc_1', 'edc_2':
        df = pd.read_csv(f'{dirname}/{edc_id}_demand_analysis.csv')
        # df = df.iloc[50:, :]['n_clients']  # We get rid of first 50 rows to obtain more reliable results
        print(f'{edc_id} demand: {df["n_clients"].min()}; {df["n_clients"].mean()}; {df["n_clients"].max()}')

        aux = df[['time', 'n_clients']].shift(periods=1, fill_value=0)
        mean_u = (aux['n_clients'].clip(upper=100) / 100 * (df['time'] - aux['time'])).sum() / MAX_T
        print(f'{edc_id} mean utilization: {mean_u}')

        df = pd.read_csv(f'{dirname}/{edc_id}_power_analysis.csv')
        # df = df.iloc[50:, :]  # We get rid of first 50 rows to obtain more reliable results

        aux = df[['time', 'adas_total_u', 'adas_slice_u', 'pue']].shift(periods=1, fill_value=0)
        mean_pue = (aux['pue'] * (df['time'] - aux['time'])).sum() / MAX_T
        print(f'{edc_id} PUE: {df["pue"].min()}; {mean_pue}; {df["pue"].max()}')

        it_energy = df["it_energy"].max()
        cooling_energy = df["cooling_energy"].max()
        total_energy = df["total_energy"].max()
        print(f'IT energy consumption (Wh): {it_energy}')
        print(f'Cooling energy consumption (Wh): {cooling_energy}')
        print(f'Total energy consumption (Wh): {total_energy}')
        for col, energy in ('it_power', it_energy), ('cooling_power', cooling_energy), ('power_demand', total_energy):
            print(f'{col} (W): {df[col].min()}; {energy * 3600 / 86400}; {df[col].max()}')

        columns = {
            'pue': 'PUE',
            'adas_total_u': 'utilization',
        }
        for column, description in columns.items():
            req_df = df[column]
            print(f'{edc_id} {description}: {req_df.min()}; {req_df.mean()}; {req_df.max()}')
        print()


def plot_demand(dirname: str, alpha_edge: float = 1, alpha_cloud: float | None = None):
    fig, ax = plt.subplots(figsize=(12, 6))
    for edc_id in 'edc_0', 'edc_1', 'edc_2':
        df = pd.read_csv(f'{dirname}/{edc_id}_demand_analysis_epoch.csv', index_col=None)
        if alpha_edge != 1:
            df['n_clients'] = df['n_clients'].ewm(alpha=alpha_edge).mean()
        df = df.iloc[50:, :]  # We get rid of first 50 rows to obtain more beautiful graphs
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, df['n_clients'], linewidth=1, drawstyle='steps-post', label=edc_id)
    if alpha_cloud is not None:
        df = pd.read_csv(f'{dirname}/cloud_analysis_epoch.csv', index_col=None)
        if alpha_cloud != 1:
            df['n_clients'] = df['n_clients'].ewm(alpha=alpha_cloud).mean()
        secs = mdate.date2num(df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, df['n_clients'], linewidth=1, drawstyle='steps-post', label='cloud')

    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=0)

    plt.title("Demand", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("clients", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.savefig(f'{dirname}/edge_demand.pdf')
    plt.show()


def plot_utilization(dirname: str, alpha_edge: float = 1, alpha_cloud: float | None = None):
    fig, ax = plt.subplots(figsize=(12, 6))
    for edc_id in 'edc_0', 'edc_1', 'edc_2':
        df = pd.read_csv(f'{dirname}/{edc_id}_demand_analysis_epoch.csv', index_col=None)
        df['utilization'] = df['n_clients']
        if alpha_edge != 1:
            df['utilization'] = df['utilization'].ewm(alpha=alpha_edge).mean()
        df['utilization'].clip(upper=100, inplace=True)
        df = df.iloc[50:, :]  # We get rid of first 50 rows to obtain more beautiful graphs
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, df['utilization'], linewidth=2, drawstyle='steps-post', label=edc_id)
    if alpha_cloud is not None:
        df = pd.read_csv(f'{dirname}/cloud_analysis_epoch.csv', index_col=None)
        if alpha_cloud != 1:
            df['utilization'] = df['utilization'].ewm(alpha=alpha_cloud).mean()
        secs = mdate.date2num(df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, df['utilization'] * 100, linewidth=1, drawstyle='steps-post', label='cloud')

    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=0)

    # plt.title('Utilization', fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("utilization [%]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.savefig(f'{dirname}/res_edge_hybrid_utilization.pdf')
    plt.show()


def plot_hot_stdby_u(dirname: str, alpha_edge: float = 1, alpha_cloud: float | None = None):
    fig, ax = plt.subplots(figsize=(12, 6))
    for edc_id in 'edc_0', 'edc_1', 'edc_2':
        df = pd.read_csv(f'{dirname}/{edc_id}_power_analysis_epoch.csv', index_col=None)
        if alpha_edge != 1:
            df['adas_total_u'] = df['adas_total_u'].ewm(alpha=alpha_edge).mean()
        df = df.iloc[200:, :]  # We get rid of first 50 rows to obtain more beautiful graphs
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, df['adas_total_u'] * 100, linewidth=2, drawstyle='steps-post', label=edc_id)
    if alpha_cloud is not None:
        df = pd.read_csv(f'{dirname}/cloud_analysis_epoch.csv', index_col=None)
        if alpha_cloud != 1:
            df['utilization'] = df['utilization'].ewm(alpha=alpha_cloud).mean()
        secs = mdate.date2num(df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, df['utilization'] * 100, linewidth=2, drawstyle='steps-post', label='cloud')

    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    # plt.ylim(bottom=0)

    #plt.title('Hot standby utilization', fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("utilization [%]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    # plt.savefig(f'{dirname}/edge_hot_stdby_u.pdf')
    plt.savefig(f'{dirname}/res_edge_hybrid_hot_u.pdf')
    plt.show()


def plot_pue(dirname: str, alpha_edge: float = 1):
    fig, ax = plt.subplots(figsize=(12, 6))
    for edc_id in 'edc_0', 'edc_1', 'edc_2':
        df = pd.read_csv(f'{dirname}/{edc_id}_power_analysis_epoch.csv', index_col=None)
        if alpha_edge != 1:
            df['pue'] = df['pue'].ewm(alpha=alpha_edge).mean()
        df = df.iloc[50:, :]  # We get rid of first 50 rows to obtain more beautiful graphs
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, df['pue'], linewidth=2, drawstyle='steps-post', label=edc_id)

    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=1.0068)

    # plt.title("Power Usage Effectiveness", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("PUE", fontsize=30)
    plt.xlabel("time", fontsize=30)
    # plt.savefig(f'{dirname}/edge_pue.pdf')
    plt.savefig(f'{dirname}/res_edge_hybrid_pue.pdf')
    plt.show()


def plot_power(dirname: str, alpha_edge: float = 1, alpha_cloud: float | None = None):
    fig, ax = plt.subplots(figsize=(12, 6))
    for edc_id in 'edc_0', 'edc_1', 'edc_2':
        df = pd.read_csv(f'{dirname}/{edc_id}_power_analysis_epoch.csv', index_col=None)
        if alpha_edge != 1:
            df['power_demand'] = df['power_demand'].ewm(alpha=alpha_edge).mean()
        df = df.iloc[50:, :]  # We get rid of first 50 rows to obtain more beautiful graphs
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, df['power_demand'], linewidth=2, drawstyle='steps-post', label=edc_id)
    if alpha_cloud is not None:
        df = pd.read_csv(f'{dirname}/cloud_analysis_epoch.csv', index_col=None)
        if alpha_cloud != 1:
            df['total_power'] = df['total_power'].ewm(alpha=alpha_cloud).mean()
        secs = mdate.date2num(df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, df['total_power'], linewidth=2, drawstyle='steps-post', label='cloud')

    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    # plt.ylim(bottom=1700)

    # plt.title("Power demand", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("power [W]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    # plt.savefig(f'{dirname}/edge_power_demand.pdf')
    plt.savefig(f'{dirname}/res_edge_hybrid_power.pdf')
    plt.show()


ALPHA_EDGE: float = 0.001
ALPHA_CLOUD: float | None = 0.5
# DIRECTORY = '06_edge_slice_proactive_30'
DIRECTORY = '19_sg_us3000c_strict'


if __name__ == '__main__':
    clean(DIRECTORY)
    describe(DIRECTORY)
    # plt.rcParams["font.family"] = "Times New Roman"
    # plt.rcParams['axes.grid'] = True
    # plot_demand(DIRECTORY, alpha_edge=ALPHA_EDGE, alpha_cloud=ALPHA_CLOUD)
    # plot_utilization(DIRECTORY, alpha_edge=ALPHA_EDGE, alpha_cloud=None)
    # plot_hot_stdby_u(DIRECTORY, alpha_edge=ALPHA_EDGE, alpha_cloud=None)
    # plot_power(DIRECTORY, alpha_edge=ALPHA_EDGE, alpha_cloud=ALPHA_CLOUD)
    # plot_pue(DIRECTORY, alpha_edge=ALPHA_EDGE)
