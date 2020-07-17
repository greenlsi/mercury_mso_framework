import sys
import pandas as pd
from mercury.allocation_manager import AllocationManager
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def dist(a, b, ax=1):
    return np.linalg.norm(a - b, axis=ax)


def plot_scenario(data, aps, edcs):
    D_real = np.array(list(zip(data['x'], data['y'])))
    clusters_data_real = np.zeros(len(D_real))
    clusters_ap_real = np.zeros(len(aps))

    for i in range(len(aps)):
        distances = dist(aps[i], edcs)
        cluster = np.argmin(distances)
        clusters_ap_real[i] = cluster

    for i in range(len(D_real)):
        distances = dist(D_real[i], aps)
        cluster = np.argmin(distances)
        clusters_data_real[i] = 1
        # clusters_data_real[i] = clusters_ap_real[cluster]

    plt.figure(figsize=(10, 8))
    n_edcs = edcs.shape[0]

    palette1 = sns.color_palette(palette="pastel", n_colors=1)
    palette2 = sns.color_palette(palette="deep", n_colors=n_edcs)
    palette3 = sns.color_palette(palette=None, n_colors=n_edcs)
    sns.scatterplot(data['x'], data['y'], hue=clusters_data_real, palette=palette1, legend=False)
    sns.scatterplot(aps[:, 0], aps[:, 1], marker='s', s=200, hue=clusters_ap_real, palette=palette2,
                    legend=False)
    sns.scatterplot(edcs[:, 0], edcs[:, 1], hue=range(n_edcs), palette=palette3, marker='o', s=500,
                    legend=False)

    # L = plt.legend().get_texts()
    # for i in range(len(L)):
    #     L[i].set_text("edc_" + str(i))
    #     L[i].set_fontsize(20)
    # plt.title("APs and EDCs' location", fontsize=20)
    plt.title("San Francisco Bay Area", fontsize=40)
    plt.yticks(rotation=90, fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("y [m]", fontsize=30)
    plt.xlabel("x [m]", fontsize=30)
    plt.savefig('frisco.pdf')
    plt.show()


if __name__ == '__main__':
    ue_data = pd.read_csv('data/ue_mobility.csv', index_col=None)

    if len(sys.argv) > 1 and sys.argv[1].lower() == 'true':
        a = AllocationManager(ue_data, plot=True)
        a.allocate_aps(plot=True)
        a.allocate_edcs()
        a.store_scenario('data/')

    aps = pd.read_csv('data/ap_location.csv', index_col=None)[['x', 'y']].values
    edcs = pd.read_csv('data/edc_location.csv', index_col=None)[['x', 'y']].values
    plot_scenario(ue_data, aps, edcs)
