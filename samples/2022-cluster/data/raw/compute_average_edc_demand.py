import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdate


MAY_17 = 1211007600
JUNE_6 = 1212735600


def print_demand_profile(filename: str):
    all_demand = pd.read_csv(filename)
    days = np.linspace(MAY_17, JUNE_6, 21)
    fig, ax = plt.subplots(figsize=(12, 6))
    for edc_id in all_demand['edc_id'].unique():
        demand = all_demand[all_demand['edc_id'] == edc_id][['epoch', 'demand']]
        results = np.zeros([20*24, 4])
        last_val = 0
        for i in range(days.size - 1):
            min_day = days[i]
            max_day = days[i + 1]
            hours = np.linspace(min_day, max_day, 25)
            for j in range(hours.size - 1):
                min_hour = hours[j]
                max_hour = hours[j + 1]
                df = demand[(min_hour <= demand['epoch']) & (demand['epoch'] < max_hour)]

                array = df.values[np.argsort(df.values[:, 0])]
                mean = last_val
                if array.shape[0] > 0:
                    mean = last_val * (array[0, 0] - min_hour)
                    for k in range(array.shape[0] - 1):
                        val = array[k, 1]
                        t = array[k + 1, 0] - array[k, 0]
                        mean += val * t
                    mean += array[-1, 1] * (max_hour - array[-1, 0])
                    mean /= (max_hour - min_hour)
                    last_val = array[-1, 1]
                results[i * 24 + j] = [min_hour, (i + 5) % 7 + 1, j, mean]
        df = pd.DataFrame(data=results, columns=['epoch', 'day', 'hour', 'demand'])
        df.to_csv(f'{edc_id}_discrete_demand.csv', index=False)

        secs = mdate.epoch2num(results[:, 0] - 25200)
        ax.plot_date(secs, results[:, 3], fmt='-', linewidth='3', label=edc_id)

    date_fmt = '%d/%m'
    date_formatter = mdate.DateFormatter(date_fmt)
    ax.xaxis.set_major_formatter(date_formatter)
    fig.autofmt_xdate()
    plt.ylim(bottom=0)

    plt.title("Average demand in San Francisco Bay area", fontsize=35)
    plt.legend(loc='upper left', fontsize=15)
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("users", fontsize=30)
    plt.xlabel("time", fontsize=30)
    plt.savefig('edc_demand.pdf')
    plt.show()


if __name__ == '__main__':
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams['axes.grid'] = True
    print_demand_profile('demand_until_june_6.csv')
