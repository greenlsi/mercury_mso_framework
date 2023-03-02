from __future__ import annotations
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdate
from mercury.analysis.metrics import time_to_epoch

JUNE_6 = 1212735600
MAX_T = 86400

DYNAMIC_COLUMNS = {
    'power_consumption': 'Power consumption (W)',
    'power_demand': 'Power demand (W)',
    'power_storage': 'Power storage (W)',
    'power_generation': 'Power generation (W)',
    'energy_stored': 'Energy stored (Wh)',
}

ACCUMULATIVE_COLUMNS = {
    'acc_energy_consumption': 'energy consumption (Wh)',
    'acc_energy_returned': 'energy returned to the grid (Wh)',
    'acc_cost': 'energy cost ($)',
}


def clean(dirname: str):
    time_to_epoch(JUNE_6, f'{dirname}/transducer_smart_grid_events.csv', f'{dirname}/smart_grid_analysis_epoch.csv')


def describe(dirname: str):
    df = pd.read_csv(f'{dirname}/transducer_smart_grid_events.csv')
    for consumer_id in df['consumer_id'].unique():
        print(f'DATA FOR CONSUMER {consumer_id}:')
        consumer_df = df[df['consumer_id'] == consumer_id]
        for column_id, description in DYNAMIC_COLUMNS.items():
            data = consumer_df[column_id]
            print(f'{description}: {data.min()} - {data.mean()} - {data.max()}')
        for column_id, description in ACCUMULATIVE_COLUMNS.items():
            data = consumer_df[column_id]
            print(f'{description}: {data.abs().max()}')
        print()


def plot_acc_cost(dirname: str, alpha: float = 1, price_thresholds: tuple[float, float] | None = None):
    fig, ax = plt.subplots(figsize=(12, 6))
    df = pd.read_csv(f'{dirname}/smart_grid_analysis_epoch.csv', index_col=None)
    for edc_id in df['consumer_id'].unique():
        edc_df = df.loc[df['consumer_id'] == edc_id, ('epoch', 'acc_cost')]
        if alpha != 1:
            edc_df.loc[:, 'acc_cost'] = edc_df['acc_cost'].ewm(alpha=alpha).mean()
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(edc_df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, edc_df['acc_cost'], linewidth=2, label=edc_id)

    if price_thresholds is not None:
        min_threshold, max_threshold = price_thresholds
        df = pd.read_csv('../data/electricity_offer_viz.csv', sep=';', index_col=None)
        secs = mdate.date2num(df['hour'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))

        ax.fill_between(secs, 0, 1, where=df['offer'] <= min_threshold,
                        color='green', alpha=0.2, transform=ax.get_xaxis_transform())

        # ax.axhline(max_threshold, color='red', lw=2, alpha=0.7)
        ax.fill_between(secs, 0, 1, where=df['offer'] >= max_threshold,
                        color='red', alpha=0.15, transform=ax.get_xaxis_transform())


    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=0)

    # plt.title("Accumulated cost", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("cost [$]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    # plt.savefig(f'{dirname}/smart_grid_cost.pdf')
    plt.savefig(f'{dirname}/res_sg_us3000c_strict_cost.pdf')
    plt.show()


def plot_power_generation(dirname: str, alpha: float = 1):
    fig, ax = plt.subplots(figsize=(12, 6))
    df = pd.read_csv(f'{dirname}/smart_grid_analysis_epoch.csv', index_col=None)
    for edc_id in df['consumer_id'].unique():
        edc_df = df.loc[df['consumer_id'] == edc_id, ('epoch', 'power_generation')]
        if alpha != 1:
            edc_df.loc[:, 'power_generation'] = edc_df['power_generation'].ewm(alpha=alpha).mean()
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(edc_df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, edc_df['power_generation'], drawstyle='steps-post', linewidth=2, label=edc_id)

    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=0)

    # plt.title("Power generation", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("power [W]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    # plt.savefig(f'{dirname}/smart_grid_cost.pdf')
    plt.savefig(f'{dirname}/res_sg_us3000c_strict_power_generation.pdf')
    plt.show()


def plot_power_storage(dirname: str, alpha: float = 1, price_thresholds: tuple[float, float] | None = None):
    fig, ax = plt.subplots(figsize=(12, 6))
    df = pd.read_csv(f'{dirname}/smart_grid_analysis_epoch.csv', index_col=None)
    for edc_id in df['consumer_id'].unique():
        edc_df = df.loc[df['consumer_id'] == edc_id, ('epoch', 'power_storage')]
        if alpha != 1:
            edc_df.loc[:, 'power_storage'] = edc_df['power_storage'].ewm(alpha=alpha).mean()
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(edc_df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, edc_df['power_storage'], drawstyle='steps-post', linewidth=2, label=edc_id)

    if price_thresholds is not None:
        min_threshold, max_threshold = price_thresholds
        df = pd.read_csv('../data/electricity_offer_viz.csv', sep=';', index_col=None)
        secs = mdate.date2num(df['hour'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))

        ax.fill_between(secs, 0, 1, where=df['offer'] <= min_threshold,
                        color='green', alpha=0.2, transform=ax.get_xaxis_transform())

        # ax.axhline(max_threshold, color='red', lw=2, alpha=0.7)
        ax.fill_between(secs, 0, 1, where=df['offer'] >= max_threshold,
                        color='red', alpha=0.15, transform=ax.get_xaxis_transform())

    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()

    # plt.title("Power storage", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("power [W]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    # plt.savefig(f'{dirname}/smart_grid_cost.pdf')
    plt.savefig(f'{dirname}/res_sg_us3000c_strict_power_storage.pdf')
    plt.show()


def plot_energy_storage(dirname: str, alpha: float = 1, price_thresholds: tuple[float, float] | None = None):
    fig, ax = plt.subplots(figsize=(12, 6))
    df = pd.read_csv(f'{dirname}/smart_grid_analysis_epoch.csv', index_col=None)
    for edc_id in df['consumer_id'].unique():
        edc_df = df.loc[df['consumer_id'] == edc_id, ('epoch', 'energy_stored')]
        if alpha != 1:
            edc_df.loc[:, 'energy_stored'] = edc_df['energy_stored'].ewm(alpha=alpha).mean()
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(edc_df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, edc_df['energy_stored'], linewidth=2, label=edc_id)

    if price_thresholds is not None:
        min_threshold, max_threshold = price_thresholds
        df = pd.read_csv('../data/electricity_offer_viz.csv', sep=';', index_col=None)
        secs = mdate.date2num(df['hour'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))

        ax.fill_between(secs, 0, 1, where=df['offer'] <= min_threshold,
                        color='green', alpha=0.2, transform=ax.get_xaxis_transform())

        # ax.axhline(max_threshold, color='red', lw=2, alpha=0.7)
        ax.fill_between(secs, 0, 1, where=df['offer'] >= max_threshold,
                        color='red', alpha=0.15, transform=ax.get_xaxis_transform())

    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=0)

    # plt.title("Energy storage", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("energy [Wh]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    # plt.savefig(f'{dirname}/smart_grid_cost.pdf')
    plt.savefig(f'{dirname}/res_sg_us3000c_strict_energy_storage.pdf')
    plt.show()


# TODO poner bloques azules cuando hay return
def plot_power_consumption(dirname: str, alpha: float = 1, price_thresholds: tuple[float, float] | None = None):
    fig, ax = plt.subplots(figsize=(12, 6))
    df = pd.read_csv(f'{dirname}/smart_grid_analysis_epoch.csv', index_col=None)
    for edc_id in df['consumer_id'].unique():
        edc_df = df.loc[df['consumer_id'] == edc_id, ('epoch', 'power_consumption')]
        if alpha != 1:
            edc_df.loc[:, 'power_consumption'] = edc_df['power_consumption'].ewm(alpha=alpha).mean()
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(edc_df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, edc_df['power_consumption'], drawstyle='steps-post', linewidth=2, label=edc_id)

        ax.fill_between(secs, 0, 1, where=edc_df['power_consumption'] < 0,
                        color='blue', alpha=0.2, transform=ax.get_xaxis_transform())

    if price_thresholds is not None:
        min_threshold, max_threshold = price_thresholds
        df = pd.read_csv('../data/electricity_offer_viz.csv', sep=';', index_col=None)
        secs = mdate.date2num(df['hour'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))

        ax.fill_between(secs, 0, 1, where=df['offer'] <= min_threshold,
                        color='green', alpha=0.2, transform=ax.get_xaxis_transform())

        # ax.axhline(max_threshold, color='red', lw=2, alpha=0.7)
        ax.fill_between(secs, 0, 1, where=df['offer'] >= max_threshold,
                        color='red', alpha=0.15, transform=ax.get_xaxis_transform())

    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    # plt.ylim(bottom=0)

    # plt.title("Power consumption", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("power [W]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    # plt.savefig(f'{dirname}/smart_grid_cost.pdf')
    plt.savefig(f'{dirname}/res_sg_us3000c_strict_power_consumption.pdf')
    plt.show()


def plot_power_demand(dirname: str, alpha: float = 1):
    fig, ax = plt.subplots(figsize=(12, 6))
    df = pd.read_csv(f'{dirname}/smart_grid_analysis_epoch.csv', index_col=None)
    for edc_id in df['consumer_id'].unique():
        edc_df = df.loc[df['consumer_id'] == edc_id, ('epoch', 'power_demand')]
        if alpha != 1:
            edc_df.loc[:, 'power_demand'] = edc_df['power_demand'].ewm(alpha=alpha).mean()
        # The 25200 thing compensates the time zone in San Francisco
        secs = mdate.date2num(edc_df['epoch'].apply(lambda i: datetime.utcfromtimestamp(i - 25200)))
        ax.plot(secs, edc_df['power_demand'], drawstyle='steps-post', linewidth=2, label=edc_id)

    date_formatter = mdate.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=0)

    # plt.title("Power demand", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("power [W]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    # plt.savefig(f'{dirname}/smart_grid_cost.pdf')
    plt.savefig(f'{dirname}/res_sg_us3000c_strict_power_demand.pdf')
    plt.show()



ALPHA: float = 0.01
# DIRECTORY, PRICE_THRESHOLDS = '15_sg_none', None
# DIRECTORY, PRICE_THRESHOLDS = '16_sg_us2000c_loose', (20, 35)
# DIRECTORY, PRICE_THRESHOLDS = '17_sg_us2000c_strict', (19, 37)
# DIRECTORY, PRICE_THRESHOLDS = '18_sg_us3000c_loose', (20, 35)
DIRECTORY, PRICE_THRESHOLDS = '15_sg_none', (19, 37)


if __name__ == '__main__':
    # clean(DIRECTORY)
    describe(DIRECTORY)
    # plt.rcParams["font.family"] = "Times New Roman"
    # plt.rcParams['axes.grid'] = True
    # plot_acc_cost(DIRECTORY, price_thresholds=PRICE_THRESHOLDS)
    # plot_power_generation(DIRECTORY)
    # plot_power_storage(DIRECTORY, price_thresholds=PRICE_THRESHOLDS)
    # plot_power_demand(DIRECTORY, alpha=ALPHA)
    # plot_power_consumption(DIRECTORY, alpha=ALPHA, price_thresholds=PRICE_THRESHOLDS)
    # plot_energy_storage(DIRECTORY, price_thresholds=PRICE_THRESHOLDS)
