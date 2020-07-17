import numpy as np
import matplotlib.pyplot as plt
from mercury.fog_model.transducers.transducers_mysql import MySQLEdgeDataCenterTransducer
from mercury.visualization import apply_ema

plt.rcParams["font.family"] = "Times New Roman"
plt.rc('font', size=16)


def multiple_graph(ax, time, classes, y_values, alpha):
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
        ax.step(time, data_array[:, i], where='post')
    plt.legend(class_labels, loc='lower right')


if __name__ == '__main__':
    model_to_description = {'classic': 'Original', 'shortcut': 'Bypassed', 'lite': 'Simplified'}
    n_ues = 100
    host = 'localhost'
    port = 3306
    user = 'root'
    password = None
    classes = ['edc_0', 'edc_1', 'edc_2']
    alpha = 1

    fig, axs = plt.subplots(1, 3, figsize=(15, 4))

    model_to_axis = {'classic': axs[0], 'shortcut': axs[1], 'lite': axs[2]}
    title = 'Edge Data Centers Utilization Factor for 100 UEs'
    if alpha < 1:
        title += ' (EMA, ' + r'$\alpha$' + ' = {})'.format(alpha)
    # fig.suptitle(title, size=18)
    # plt.subplots_adjust(top=0.6)

    for ax in axs.flat:
        ax.set(xlabel='time [s]', ylabel='EDC utilization [%]')
    # Hide x labels and tick labels for top plots and y ticks for right plots.
    for ax in axs.flat:
        ax.label_outer()

    for model, name in model_to_description.items():
        db = 'summersim20_{}_{}'.format(model, n_ues)
        transducer = MySQLEdgeDataCenterTransducer(host, port, user, password, db)
        time, edc_id, data = transducer.get_edc_utilization_data()
        data = [item / 10 for item in data]
        ax = model_to_axis[model]
        ax.set_title(name + ' Model', size=18)

        filename = '{}.pdf'.format(db)

        multiple_graph(ax, time, edc_id, data, alpha)
    plt.draw()
    plt.savefig('edcs_u_{}.pdf'.format(alpha), bbox_inches='tight', dpi=fig.dpi)
    # plt.savefig('edcs_u_{}.pdf'.format(alpha), bbox_inches='tight')
    plt.show()
