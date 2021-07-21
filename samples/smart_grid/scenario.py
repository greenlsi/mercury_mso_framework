import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def dist(a, b, ax=1):
    return np.linalg.norm(a - b, axis=ax)


def plot_scenario(data, aps, edcs):
    D_real = np.array(list(zip(data['x'], data['y'])))
    clusters_data_real = np.zeros(len(D_real))
    clusters_ap_real = np.zeros(len(aps))
    print('***********')
    print(aps)
    print(edcs)

    for i in range(len(aps)):
        distances = dist(aps[i], edcs)
        cluster = np.argmin(distances)
        clusters_ap_real[i] = cluster

    for i in range(len(D_real)):
        distances = dist(D_real[i], aps)
        cluster = np.argmin(distances)
        #clusters_data_real[i] = 1
        clusters_data_real[i] = clusters_ap_real[cluster]

    plt.figure(figsize=(10, 8))
    n_edcs = edcs.shape[0]

    palette1 = sns.color_palette(palette="pastel", n_colors=n_edcs)
    palette2 = sns.color_palette(palette="deep", n_colors=n_edcs)
    palette3 = sns.color_palette(palette=None, n_colors=n_edcs)
    sns.scatterplot(x=data['x'], y=data['y'], hue=clusters_data_real, palette=palette1, legend=False)
    sns.scatterplot(x=aps[:, 0], y=aps[:, 1], marker='*', s=500, hue=clusters_ap_real, palette=palette2,
                    legend=False)
    sns.scatterplot(x=edcs[:, 0], y=edcs[:, 1], hue=range(n_edcs), palette=palette3, marker='s', s=500,
                    legend=False)
    # L = plt.legend().get_texts()
    # for i in range(len(L)):
    #     L[i].set_text("edc_" + str(i))
    #     L[i].set_fontsize(20)
    # plt.title("APs and EDCs' location", fontsize=20)
    plt.title("Scenario", fontsize=40)
    plt.yticks(rotation=90, fontsize=20)
    plt.xticks(fontsize=20)
    plt.ylabel("y [m]", fontsize=30)
    plt.xlabel("x [m]", fontsize=30)
    plt.savefig('frisco.pdf')
    plt.show()


if __name__ == '__main__':
    plt.rcParams["font.family"] = "Times New Roman"
    data = pd.read_csv('data/mobility/2008-06-06-harbor-xy-traces.csv', sep=';', index_col=None)
    aps = pd.read_csv('ap_location.csv', sep=';', index_col=None)[['x', 'y']].values
    edcs = pd.read_csv('edc_location.csv', sep=';', index_col=None)[['x', 'y']].values
    plot_scenario(data, aps, edcs)
