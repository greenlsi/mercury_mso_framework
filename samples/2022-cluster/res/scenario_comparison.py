import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdate
from mercury.analysis.metrics import time_to_epoch

JUNE_6 = 1212735600
DIRECTORY = '14_edge_slice_hybrid_50'
MAX_T = 86400

SCENARIO_TAGS = {
    '01_edge_none': 'None',
    '02_edge_all': 'All',
    '03_edge_slice_proactive_00': r'$\alpha$=0.0',
    '04_edge_slice_proactive_10': r'$\alpha$=0.1',
    '05_edge_slice_proactive_20': r'$\alpha$=0.2',
    '06_edge_slice_proactive_30': r'$\alpha$=0.3',
    '07_edge_slice_proactive_40': r'$\alpha$=0.4',
    '08_edge_slice_proactive_50': r'$\alpha$=0.5',
    '09_edge_slice_hybrid_00': r'$\alpha$=0.0',
    '10_edge_slice_hybrid_10': r'$\alpha$=0.1',
    '11_edge_slice_hybrid_20': r'$\alpha$=0.2',
    '12_edge_slice_hybrid_30': r'$\alpha$=0.3',
    '13_edge_slice_hybrid_40': r'$\alpha$=0.4',
    '14_edge_slice_hybrid_50': r'$\alpha$=0.5',
}


def plot_proactive():
    scenarios = [
        '01_edge_none',
        '03_edge_slice_proactive_00',
        '04_edge_slice_proactive_10',
        '05_edge_slice_proactive_20',
        '06_edge_slice_proactive_30',
        '07_edge_slice_proactive_40',
        '08_edge_slice_proactive_50',
        '02_edge_all',
    ]

    df = pd.read_csv('scenario_comparison.csv', index_col=None)
    df = df[df['scenario'].isin(scenarios)]
    # We move the all policy to the end of the dataframe
    df = df.drop(1).append(df.loc[1])

    x = [SCENARIO_TAGS[scenario] for scenario in scenarios]
    y_edc_0 = df['energy_edc_0'] / 1000
    y_edc_1 = df['energy_edc_1'] / 1000
    y_edc_2 = df['energy_edc_2'] / 1000
    y_cloud = df['energy_cloud'] / 1000

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.bar(x, y_edc_0, label='edc_0')
    ax.bar(x, y_edc_1, bottom=y_edc_0, label='edc_1')
    ax.bar(x, y_edc_2, bottom=y_edc_0 + y_edc_1, label='edc_2')
    ax.bar(x, y_cloud, bottom=y_edc_0 + y_edc_1 + y_edc_2, label='cloud')

    plt.title('Energy consumption of proactive policies', fontsize=35)
    plt.legend(fontsize=15)
    plt.ylabel('Energy [kWh]', fontsize=30)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=18)
    plt.savefig(f'proactive_comparison.pdf')
    # plt.savefig(f'res_proactive_comparison.pdf')
    plt.show()


def plot_hybrid():
    scenarios = [
        '01_edge_none',
        '09_edge_slice_hybrid_00',
        '10_edge_slice_hybrid_10',
        '11_edge_slice_hybrid_20',
        '12_edge_slice_hybrid_30',
        '13_edge_slice_hybrid_40',
        '14_edge_slice_hybrid_50',
        '02_edge_all',
    ]

    df = pd.read_csv('scenario_comparison.csv', index_col=None)
    df = df[df['scenario'].isin(scenarios)]
    # We move the all policy to the end of the dataframe
    df = df.drop(1).append(df.loc[1])

    x = [SCENARIO_TAGS[scenario] for scenario in scenarios]
    y_edc_0 = df['energy_edc_0'] / 1000
    y_edc_1 = df['energy_edc_1'] / 1000
    y_edc_2 = df['energy_edc_2'] / 1000
    y_cloud = df['energy_cloud'] / 1000

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.bar(x, y_edc_0, label='edc_0')
    ax.bar(x, y_edc_1, bottom=y_edc_0, label='edc_1')
    ax.bar(x, y_edc_2, bottom=y_edc_0 + y_edc_1, label='edc_2')
    ax.bar(x, y_cloud, bottom=y_edc_0 + y_edc_1 + y_edc_2, label='cloud')

    # plt.title('Energy consumption of proactive policies', fontsize=35)
    plt.legend(fontsize=15)
    plt.ylabel('Energy [kWh]', fontsize=30)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=18)
    # plt.savefig(f'hybrid_comparison.pdf')
    plt.savefig(f'res_hybrid_comparison.pdf')
    plt.show()


if __name__ == '__main__':
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams['axes.grid'] = True
    plot_hybrid()
