import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdate
from mercury.analysis.visualization import plot_edc_step_data, plot_edc_line_data

max_threshold = 37
min_threshold = 19
offers = pd.read_csv('../data/smart_grid/electricity_offer.csv', sep=';').values
secs = mdate.epoch2num(offers[:, 0] - 25200)


def plot_edc_stuff(data_path: str):
    df = pd.read_csv(data_path)


    fig, ax = plt.subplots(figsize=(12, 6))
    plot_edc_step_data(df, 'power_consumption', fig, ax, edc_col='consumer_id', epoch=True, fill_negative=True)
    # plt.ylim(bottom=0)
    # plt.locator_params(axis='x', nbins=6)
    plt.title("Power consumption of EDCs", fontsize=35)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("Power [W]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.legend(fontsize=20)

    # ax.axhline(min_threshold, color='green', lw=2, alpha=0.7)
    ax.fill_between(secs, 0, 1, where=offers[:, 1] <= min_threshold,
                    color='green', alpha=0.2, transform=ax.get_xaxis_transform())

    # ax.axhline(max_threshold, color='red', lw=2, alpha=0.7)
    ax.fill_between(secs, 0, 1, where=offers[:, 1] >= max_threshold,
                    color='red', alpha=0.15, transform=ax.get_xaxis_transform())

    plt.savefig('10_battery_1_strict/edc_power_consumption.pdf')
    plt.show()

    """
    fig, ax = plt.subplots(figsize=(12, 6))
    plot_edc_step_data(df, 'power_demand', fig, ax, edc_col='consumer_id', epoch=True)
    plt.ylim(bottom=0)
    # plt.locator_params(axis='x', nbins=6)
    plt.title("Power demand of EDCs", fontsize=35)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("Power [W]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.legend(fontsize=20)
    plt.savefig('9_10_trend_summer/edc_power_demand.pdf')
    plt.show()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    plot_edc_step_data(df, 'power_storage', fig, ax, edc_col='consumer_id', epoch=True)
    # plt.ylim(bottom=0)
    # plt.locator_params(axis='x', nbins=6)
    plt.title("Power storage of EDCs", fontsize=35)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("Power [W]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.legend(fontsize=20)

    # ax.axhline(min_threshold, color='green', lw=2, alpha=0.7)
    ax.fill_between(secs, 0, 1, where=offers[:, 1] <= min_threshold,
                    color='green', alpha=0.2, transform=ax.get_xaxis_transform())

    # ax.axhline(max_threshold, color='red', lw=2, alpha=0.7)
    ax.fill_between(secs, 0, 1, where=offers[:, 1] >= max_threshold,
                    color='red', alpha=0.2, transform=ax.get_xaxis_transform())

    plt.savefig('10_battery_1_strict/edc_power_storage.pdf')
    plt.show()

    fig, ax = plt.subplots(figsize=(12, 6))
    plot_edc_step_data(df, 'power_generation', fig, ax, edc_col='consumer_id', epoch=True)
    plt.ylim(bottom=0)
    # plt.locator_params(axis='x', nbins=6)
    plt.title("Power generation of EDCs", fontsize=35)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("Power [W]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.legend(fontsize=20)
    plt.savefig('9_10_trend_summer/edc_power_generation.pdf')
    plt.show()
    # TODO meterle las áreas de cuándo se puede descargar y cuando no la batería
    """

    fig, ax = plt.subplots(figsize=(12, 6))
    plot_edc_line_data(df, 'energy_stored', fig, ax, edc_col='consumer_id', epoch=True)
    plt.ylim(bottom=0)
    # plt.locator_params(axis='x', nbins=6)
    plt.title("Energy storage of EDCs", fontsize=35)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("Energy [Wh]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.legend(fontsize=20)

    # ax.axhline(min_threshold, color='green', lw=2, alpha=0.7)
    ax.fill_between(secs, 0, 1, where=offers[:, 1] <= min_threshold,
                    color='green', alpha=0.2, transform=ax.get_xaxis_transform())

    # ax.axhline(max_threshold, color='red', lw=2, alpha=0.7)
    ax.fill_between(secs, 0, 1, where=offers[:, 1] >= max_threshold,
                    color='red', alpha=0.15, transform=ax.get_xaxis_transform())

    plt.savefig('10_battery_1_strict/edc_energy_storage.pdf')
    plt.show()

    """
    fig, ax = plt.subplots(figsize=(12, 6))
    plot_edc_step_data(df, 'utilization', fig, ax, epoch=True)
    plt.ylim(bottom=0)
    # plt.locator_params(axis='x', nbins=6)
    plt.title("Resource utilization of EDCs", fontsize=35)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("Utilization [%]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.legend(fontsize=20)
    plt.savefig('9_10_trend_summer/edc_utilization.pdf')
    plt.show()

    fig, ax = plt.subplots(figsize=(12, 6))
    plot_edc_step_data(df, 'PUE', fig, ax, epoch=True)
    plt.ylim(bottom=1, top=1.1)
    # plt.locator_params(axis='x', nbins=6)
    plt.title("Power Usage Effectiveness of EDCs", fontsize=35)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("PUE", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.legend(fontsize=20)
    plt.savefig('9_10_trend_summer/edc_pue.pdf')
    plt.show()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    plot_edc_line_data(df, 'acc_cost', fig, ax, edc_col='consumer_id', epoch=True)
    plt.ylim(bottom=0)
    # plt.locator_params(axis='x', nbins=6)
    plt.title("Energy cost of EDCs", fontsize=35)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("Cost [$]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.legend(fontsize=20)

    # ax.axhline(min_threshold, color='green', lw=2, alpha=0.7)
    ax.fill_between(secs, 0, 1, where=offers[:, 1] <= min_threshold,
                    color='green', alpha=0.2, transform=ax.get_xaxis_transform())

    # ax.axhline(max_threshold, color='red', lw=2, alpha=0.7)
    ax.fill_between(secs, 0, 1, where=offers[:, 1] >= max_threshold,
                    color='red', alpha=0.15, transform=ax.get_xaxis_transform())

    plt.savefig('10_battery_1_strict/energy_cost.pdf')
    plt.show()

    fig, ax = plt.subplots(figsize=(12, 6))
    plot_edc_line_data(df, 'acc_energy', fig, ax, edc_col='consumer_id', epoch=True)
    plt.ylim(bottom=0)
    # plt.locator_params(axis='x', nbins=6)
    plt.title("Energy consumption of EDCs", fontsize=35)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("Energy [W·h]", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.legend(fontsize=20)
    plt.savefig('10_smart_sdnc/energy_consumption.pdf')
    plt.show()
    """


if __name__ == '__main__':
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams['axes.grid'] = True

    plot_edc_stuff('10_battery_1_strict/epoch_smart_grid.csv')
