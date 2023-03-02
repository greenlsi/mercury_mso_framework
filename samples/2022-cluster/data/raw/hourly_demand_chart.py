import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdate


def print_demand_profile(plot_friday: bool):
    fig, ax = plt.subplots(figsize=(12, 6))
    for edc_id in 'edc_0', 'edc_1', 'edc_2':
        demand = pd.read_csv(f'{edc_id}_discrete_demand.csv')

        daily_demand = np.zeros([25, 2])
        friday_demand = np.zeros([25, 2])

        for hour in range(0, 24):
            df = demand[demand['hour'] == hour]
            mean = df[['demand']].mean(axis=0).demand
            daily_demand[hour] = [hour, mean]

            df_friday = df[df['day'] == 5]
            mean_friday = df_friday[['demand']].mean(axis=0).demand
            friday_demand[hour] = [hour, mean_friday]
        daily_demand[24] = [24, daily_demand[23, 1]]
        friday_demand[24] = [24, friday_demand[23, 1]]

        daily_demand[:, 0] = daily_demand[:, 0] * 3600 + 1212735600
        friday_demand[:, 0] = friday_demand[:, 0] * 3600 + 1212735600

        daily_df = pd.DataFrame(data=daily_demand, columns=['hour', 'demand'])
        daily_df.to_csv(f'{edc_id}_hourly_demand.csv', index=False)
        friday_df = pd.DataFrame(data=friday_demand, columns=['hour', 'demand'])
        friday_df.to_csv(f'{edc_id}_friday_demand.csv', index=False)

        secs = mdate.epoch2num(daily_demand[:, 0] - 25200)
        if plot_friday:
            ax.step(secs, friday_demand[:, 1], where='post', linewidth='3', label=f'{edc_id}')
        else:
            ax.step(secs, daily_demand[:, 1], where='post', linewidth='3', label=f'{edc_id}')

    date_fmt = '%H:%M:%S'
    date_formatter = mdate.DateFormatter(date_fmt)
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=0)

    plt.locator_params(axis='x', nbins=12)
    if plot_friday:
        plt.title("Hourly average demand (only Fridays)", fontsize=35)
    else:
        plt.title("Hourly average demand", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("clients", fontsize=30)
    plt.xlabel("time", fontsize=30)
    if plot_friday:
        plt.savefig('friday_demand.pdf')
    else:
        plt.savefig('hourly_demand.pdf')
    plt.show()


if __name__ == '__main__':
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams['axes.grid'] = True
    print_demand_profile(True)
