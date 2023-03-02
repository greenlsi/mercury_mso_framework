import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


REQ_TYPES = {
    'OpenSessRequest': 'Open session delay',
    'CloseSessRequest': 'Close session delay',
    'SrvRequest': 'Service request delay',
}


def plot_service_delay(dirname: str, sep: str = ',', client_id: str = None,
                       service_id: str = None, req_type: str = None, alpha: float = 1):
    df = pd.read_csv(f'{dirname}/transducer_srv_report_events.csv', sep=sep)
    if client_id is not None:
        df = df[df['client_id'] == client_id]
    if service_id is not None:
        df = df[df['service_id'] == service_id]
    if req_type is not None:
        df = df[df['req_type'] == req_type]
    if alpha != 1:
        df['t_delay'] = df['t_delay'].ewm(alpha=alpha).mean()

    plt.plot(df['time'], df['t_delay'])

    title = REQ_TYPES.get(req_type, 'Delay')
    if client_id is not None:
        title = f'{title} perceived by client {client_id}'
    if service_id is not None:
        title = f'{title} for service {service_id}'
    if alpha < 1:
        alpha_char = r'$\alpha$'
        title = f'{title} (EMA,{alpha_char}={alpha})'
    plt.title(title)
    plt.xlabel('time [s]', fontsize=12)
    plt.ylabel('delay [s]', fontsize=12)
    plt.show()


def plot_network_bw(time: pd.Series, bandwidth: pd.Series, rate: pd.Series,
                    efficiency: pd.Series, subtitle: str = None, alpha: float = 1):
    bandwidth_ = apply_ema(bandwidth, alpha)
    rate_ = apply_ema(rate, alpha)
    efficiency_ = apply_ema(efficiency, alpha)
    plt.plot(time, bandwidth_)
    plt.plot(time, rate_)
    plt.xlabel('time [s]', fontsize=12)
    plt.legend(['bandwidth [Hz]', 'bitrate [bps]'], prop={'size': 12})
    title = 'Bandwidth and bit rate' if subtitle is None else f'Bandwidth and bit rate {subtitle}'
    if alpha < 1:
        title += ' (EMA,alpha={})'.format(alpha)
    plt.title(title)
    plt.show()

    plt.plot(time, efficiency_)
    plt.xlabel('time [s]', fontsize=12)
    plt.ylabel('spectral efficiency [bps/Hz]', fontsize=12)
    title = 'Spectral efficiency' if subtitle is None else f'Spectral efficiency {subtitle}'
    if alpha < 1:
        title += ' (EMA,alpha={})'.format(alpha)
    plt.title(title)
    plt.show()


def plot_edc_power(time, edc_id, power, stacked=False, alpha=1, nature='Demand'):
    title = 'Edge Data Centers Power ' + nature
    if stacked:
        title = 'Stacked ' + title
    graph_data = {
        'xlabel': 'time [s]',
        'ylabel': 'power [W]',
        'title': title
    }
    if stacked:
        stacked_graph(time, edc_id, power, graph_data, alpha)
    else:
        multiple_graph(time, edc_id, power, graph_data, alpha)


def plot_edc_energy(time, edc_id, energy, alpha=1):
    xlabel = 'time [s]'
    ylabel = 'energy [W·h]'
    edcs = list(set(edc_id))
    df = pd.DataFrame(list(zip(time, edc_id, energy)), columns=['time', 'edc_id', 'energy'])
    for edc_id in edcs:
        time = df[df['edc_id'] == edc_id].time
        energy = df[df['edc_id'] == edc_id].energy
        energy_ = apply_ema(energy, alpha)
        plt.plot(time, energy_)
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    title = 'Edge Data Centers Stored Energy'
    if alpha < 1:
        title += ' (EMA,alpha={})'.format(alpha)
    plt.title(title)
    plt.legend(edcs, prop={'size': 12})
    plt.show()


def multiple_graph(time, classes, y_values, graph_data, alpha=1):
    class_labels = list(set(classes))
    class_labels.sort()
    n_labels = len(class_labels)

    data_array = np.zeros((len(y_values), len(class_labels)))
    for i in range(n_labels):
        for j in range(len(time)):
            if classes[j] == class_labels[i]:
                data_array[j:, i] = y_values[j]
    for i in reversed(range(n_labels)):
        data_array[:, i] = np.asarray(apply_ema(data_array[:, i].tolist(), alpha))
        plt.step(time, data_array[:, i], where='post')
    plt.xlabel(graph_data['xlabel'], fontsize=12)
    plt.ylabel(graph_data['ylabel'], fontsize=12)
    plt.legend(class_labels, prop={'size': 12})
    if alpha < 1:
        graph_data['title'] += ' (EMA,alpha={})'.format(alpha)
    plt.title(graph_data['title'])
    plt.show()
    return plt


def stacked_graph(time, classes, y_values, graph_data, alpha=1):
    class_labels = list(set(classes))
    n_labels = len(class_labels)

    data_array = np.zeros((len(y_values), len(class_labels)))
    for i in range(n_labels):
        last_value = 0
        for j in range(len(time)):
            if classes[j] == class_labels[i]:
                increment = y_values[j] - last_value
                data_array[j:, i:n_labels] += increment
                last_value = y_values[j]

    for i in reversed(range(n_labels)):
        data_array[:, i] = np.asarray(apply_ema(data_array[:, i].tolist(), alpha))
        plt.step(time, data_array[:, i], where='post')
    plt.xlabel(graph_data['xlabel'], fontsize=12)
    plt.ylabel(graph_data['ylabel'], fontsize=12)
    if alpha < 1:
        graph_data['title'] += ' (EMA,alpha={})'.format(alpha)
    plt.title(graph_data['title'])
    plt.legend(class_labels, prop={'size': 12})
    plt.show()


def delay_summary(ue_file_path):
    data = pd.read_csv(ue_file_path, sep=";")
    delay = data['delay'].values
    mean_delay = np.mean(delay)
    peak_delay = np.max(delay)
    print("Mean delay: {} seconds".format(mean_delay))
    print("Peak delay: {} seconds".format(peak_delay))


def power_summary(edc_file_path):
    data = pd.read_csv(edc_file_path, index_col=False, sep=";")
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
                power[i] = row['power_demand']
        max_power = max(max_power, np.sum(power))
    mean_power /= t_prev
    print("Mean power: {} Watts".format(mean_power))
    print("Peak power: {} Watts".format(max_power))


def apply_ema(data, alpha):
    assert 0 < alpha <= 1
    aux = np.asarray(data.copy())
    if alpha < 1:
        for i in range(1, aux.shape[0]):
            aux[i] = (1 - alpha) * aux[i - 1] + alpha * aux[i]
    return aux.tolist()
