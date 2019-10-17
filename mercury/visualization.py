import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def plot_ue_service_delay(file_path, x_axis='time', y_axis='delay', alpha=1):
    data = pd.read_csv(file_path, delimiter=';')
    time = data[x_axis].values
    delay = apply_ema(data[y_axis].values, alpha)

    plt.plot(time, delay)
    plt.xlabel('time [s]', fontsize=12)
    plt.ylabel('perceived delay [s]', fontsize=12)
    title = 'Service Delay Perceived by User Equipments'
    if alpha < 1:
        title += ' (EMA,alpha={})'.format(alpha)
    plt.title(title)
    plt.show()


def plot_bw(file_path, x_axis='time', bw_axis='bandwidth', rate_axis='rate', efficiency_axis='efficiency',
            link='Uplink', alpha=1):
    data = pd.read_csv(file_path, delimiter=';')
    time = data[x_axis].values
    bandwidth = apply_ema(data[bw_axis].values, alpha)
    rate = apply_ema(data[rate_axis].values, alpha)
    efficiency = apply_ema(data[efficiency_axis].values, alpha)

    plt.plot(time, bandwidth)
    plt.plot(time, rate)
    plt.xlabel('time [s]', fontsize=12)
    plt.legend(['bandwidth [Hz]', 'bitrate [bps]'], prop={'size': 12})
    title = '{} bandwidth and bit rate'.format(link)
    if alpha < 1:
        title += ' (EMA,alpha={})'.format(alpha)
    plt.title(title)
    plt.show()

    plt.plot(time, efficiency)
    plt.xlabel('time [s]', fontsize=12)
    plt.ylabel('spectral efficiency [bps/Hz]', fontsize=12)
    title = '{} spectral efficiency'.format(link)
    if alpha < 1:
        title += ' (EMA,alpha={})'.format(alpha)
    plt.title(title)
    plt.show()


def plot_edc_utilization(edc_file_path, stacked=False, alpha=1):
    data = pd.read_csv(edc_file_path, index_col=False, delimiter=';')
    title = 'Edge Data Centers Utilization Factor'
    if stacked:
        title = 'Stacked ' + title
    graph_data = {
        'xlabel': 'time [s]',
        'ylabel': 'utilization factor [%]',
        'title': title
    }
    if stacked:
        stacked_graph(data, 'time', 'overall_std_u', 'edc_id', graph_data, alpha)
    else:
        multiple_graph(data, 'time', 'overall_std_u', 'edc_id', graph_data, alpha)


def plot_edc_power(edc_file_path, stacked=False, alpha=1):
    data = pd.read_csv(edc_file_path, index_col=False, delimiter=';')
    title = 'Edge Data Centers Power Consumption'
    if stacked:
        title = 'Stacked ' + title
    graph_data = {
        'xlabel': 'time [s]',
        'ylabel': 'power [W]',
        'title': title
    }
    if stacked:
        stacked_graph(data, 'time', 'overall_power', 'edc_id', graph_data, alpha)
    else:
        multiple_graph(data, 'time', 'overall_power', 'edc_id', graph_data, alpha)


def multiple_graph(data, x_column, y_column, class_column, graph_data, alpha=1):
    class_labels = data[class_column].unique().tolist()
    n_labels = len(class_labels)
    x = data[x_column].values.tolist()

    data_array = np.zeros((len(x), len(class_labels)))
    for i in range(n_labels):
        for index, row in data.iterrows():
            if row[class_column] == class_labels[i]:
                data_array[index:, i] = row[y_column]
    for i in reversed(range(n_labels)):
        data_array[:, i] = apply_ema(data_array[:, i], alpha)
        plt.step(x, data_array[:, i], where='post')
    plt.xlabel(graph_data['xlabel'], fontsize=12)
    plt.ylabel(graph_data['ylabel'], fontsize=12)
    plt.legend(class_labels, prop={'size': 12})
    if alpha < 1:
        graph_data['title'] += ' (EMA,alpha={})'.format(alpha)
    plt.title(graph_data['title'])
    plt.show()


def stacked_graph(data, x_column, y_column, class_column, graph_data, alpha=1):
    class_labels = data[class_column].unique().tolist()
    n_labels = len(class_labels)
    x = data[x_column].values.tolist()

    data_array = np.zeros((len(x), len(class_labels)))
    for i in range(n_labels):
        last_value = 0
        for index, row in data.iterrows():
            if row[class_column] == class_labels[i]:
                increment = row[y_column] - last_value
                data_array[index:, i:n_labels] += increment
                last_value = row[y_column]

    for i in reversed(range(n_labels)):
        data_array[:, i] = apply_ema(data_array[:, i], alpha)
        plt.step(x, data_array[:, i], where='post')
    plt.xlabel(graph_data['xlabel'], fontsize=12)
    plt.ylabel(graph_data['ylabel'], fontsize=12)
    if alpha < 1:
        graph_data['title'] += ' (EMA,alpha={})'.format(alpha)
    plt.title(graph_data['title'])
    plt.legend(class_labels, prop={'size': 12})
    plt.show()


def delay_summary(ue_file_path):
    data = pd.read_csv(ue_file_path)
    delay = data['delay'].values
    mean_delay = np.mean(delay)
    peak_delay = np.max(delay)
    print("Mean delay: {} seconds".format(mean_delay))
    print("Peak delay: {} seconds".format(peak_delay))


def power_summary(edc_file_path):
    data = pd.read_csv(edc_file_path, index_col=False)
    edc_ids = data['edc_id'].unique().tolist()
    n_edcs = len(edc_ids)
    max_power = 0
    t_prev = 0
    power = np.zeros(n_edcs)
    mean_power = 0
    for index, row in data.iterrows():
        mean_power += np.sum(power) * (row['time'] - t_prev)
        t_prev = row['time']
        for i in range(n_edcs):
            if row['edc_id'] == edc_ids[i]:
                power[i] = row['overall_power']
        max_power = max(max_power, np.sum(power))
    mean_power /= t_prev
    print("Mean power: {} Watts".format(mean_power))
    print("Peak power: {} Watts".format(max_power))


def apply_ema(data, alpha):
    assert 0 < alpha <= 1
    aux = data.copy()
    if alpha < 1:
        for i in range(1, aux.shape[0]):
            aux[i] = (1 - alpha) * aux[i - 1] + alpha * aux[i]
    return aux
