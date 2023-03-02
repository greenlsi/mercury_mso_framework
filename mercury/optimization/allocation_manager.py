import pandas as pd
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from copy import deepcopy
import random


def dist(a, b, ax=1):
    return np.linalg.norm(a - b, axis=ax)


class AllocationManager:
    def __init__(self, data, time_window=60, grid_res=40):
        self.time_window = time_window
        self.grid_res = grid_res
        self.data = data.copy()
        self.aps = None
        self.edcs = None

        df = data.copy()
        df['epoch'] = np.round(df['epoch'] / self.time_window)
        x_grid = (np.max(df['x']) + 1) / self.grid_res
        y_grid = (np.max(df['y']) + 1) / self.grid_res

        self.grid_step = np.minimum(x_grid, y_grid)

        self.grid = np.zeros(
            [int(np.floor(np.max(df['x']) / self.grid_step)), int(np.floor(np.max(df['y']) / self.grid_step))])

        for e in df['epoch'].unique():
            aux_x = (df[df['epoch'] == e]['x'] / self.grid_step).apply(np.floor).astype(np.int32)
            aux_y = (df[df['epoch'] == e]['y'] / self.grid_step).apply(np.floor).astype(np.int32)
            d = pd.DataFrame(data={'aux_x': aux_x, 'aux_y': aux_y})

            for (i, j), reps in d.groupby(list(d.columns)).apply(lambda x: list(x.index)).iteritems():
                if i >= len(self.grid) or j >= len(self.grid[0]):
                    continue

                nu = df.iloc[reps]['cab_id'].nunique()
                if nu > self.grid[i, j]:
                    self.grid[i, j] = nu

    def plot_grid(self, title="Scenario density", pdf_path=None):
            plt.figure(figsize=(10, 8))

            ax = sns.heatmap(data=self.grid.transpose(), annot=True, xticklabels=False, yticklabels=False)
            ax.invert_yaxis()
            plt.title(title, fontsize=40)
            if pdf_path is not None:
                plt.savefig(pdf_path)
            plt.show()

    def allocate_aps(self, plot=False):
        x = []
        y = []
        z = []
        for i in range(self.grid.shape[0]):
            for j in range(self.grid.shape[1]):
                x.append(i)
                y.append(j)
                z.append(self.grid[i, j])
        d = {'x': x, 'y': y, 'z': z}
        data = pd.DataFrame(data=d)

        X = data.x
        Y = data.y
        D = np.array(list(zip(X, Y)))
        flag = 0
        # Number of clusters
        k = 1
        # X coordinates of random centroids
        C_x = np.random.uniform(0, np.max(X), size=k)
        # Y coordinates of random centroids
        C_y = np.random.uniform(0, np.max(Y), size=k)

        clusters = np.zeros(len(D))
        dense_cluster = 0
        len_list = []

        while flag != 1:
            flag = 1
            if len(C_x) != k:
                candidates = []
                for j in range(len(D)):
                    if clusters[j] == dense_cluster:
                        candidates.append(D[j, :])
                cand = random.choice(candidates)

                C_x_aux = [cand[0]]
                C_y_aux = [cand[1]]
                C_x = np.concatenate((C_x, C_x_aux), axis=0)
                C_y = np.concatenate((C_y, C_y_aux), axis=0)

            C = np.array(list(zip(C_x, C_y)), dtype=np.float32)
            # To store the value of centroids when it updates
            C_old = np.zeros(C.shape)
            # Cluster Lables(0, 1, 2)
            # Error func. - Distance between new centroids and old centroids
            error = dist(C, C_old)
            # Loop will run till the error becomes zero
            while sum(error) != 0:
                # Assigning each value to its closest cluster
                for i in range(len(D)):
                    distances = dist(D[i], C)
                    cluster = np.argmin(distances)
                    clusters[i] = cluster
                # Storing the old centroid values
                C_old = deepcopy(C)
                # Finding the new centroids by taking the average value
                for i in range(k):
                    points_x = [np.repeat(D[j, 0], data.z[j]) for j in range(len(D)) if clusters[j] == i]
                    l_x = []
                    for item in points_x:
                        l_x = np.concatenate((l_x, item), axis=0)

                    points_y = [np.repeat(D[j, 1], data.z[j]) for j in range(len(D)) if clusters[j] == i]
                    l_y = []
                    for item in points_y:
                        l_y = np.concatenate((l_y, item), axis=0)

                    if np.isnan(np.mean(l_x)):
                        C[i] = np.array([-1, -1])
                        break
                    else:
                        C[i] = np.array([np.mean(l_x), np.mean(l_y)])

                error = dist(C, C_old)
                print(error, k)

            l_max = 0
            for i in range(k):
                points_x = [np.repeat(D[j, 0], data.z[j]) for j in range(len(D)) if clusters[j] == i]
                l_x = []
                for item in points_x:
                    l_x = np.concatenate((l_x, item), axis=0)
                len_list.append(len(l_x))
                if len(l_x) > l_max:
                    l_max = len(l_x)
                    dense_cluster = i
                if len(l_x) > 200 and flag != -1:
                    flag = 0
                if len(l_x) == 0:
                    flag = -1
                print(i, len(l_x))
            if flag == -1:
                k = k - 1
            C_x = C[:, 0]
            C_y = C[:, 1]
            k = k + 1
        k = k - 1
        mean_density = np.sum(len_list) / k

        print('Clusters:', k)
        print('Mean density:', mean_density)
        print('Max_cluster:', np.max(len_list))
        print('Min_cluster:', np.min(len_list))
        print(len_list)

        C_aux = C
        count = 0
        for i in range(k):
            p = 0
            p = [p + 0 for j in range(len(D)) if clusters[j] == i]

            points_x = [np.repeat(D[j, 0], data.z[j]) for j in range(len(D)) if clusters[j] == i]
            l_x = []
            for item in points_x:
                l_x = np.concatenate((l_x, item), axis=0)

            points_y = [np.repeat(D[j, 1], data.z[j]) for j in range(len(D)) if clusters[j] == i]
            l_y = []
            for item in points_y:
                l_y = np.concatenate((l_y, item), axis=0)
            if len(l_x) == 0:
                C_aux = np.delete(C_aux, i - count, 0)
                count = count + 1
            else:
                print(C[i], len(l_x), len(p))
        C = C_aux
        k = len(C)
        self.aps = C * self.grid_step

        print(k)

        if plot:
            plt.figure(figsize=(10, 8))
            ax = sns.heatmap(data=clusters.reshape(self.grid.shape).transpose(), annot=True, cbar=False)
            ax.invert_yaxis()
            ax.scatter(C[:, 0], C[:, 1], marker='*', s=100, color='yellow')
            plt.title("APs clusters by density", fontsize=20)
            plt.show()

            plt.figure(figsize=(10, 8))
            ax = sns.heatmap(data=self.grid.transpose(), annot=True)
            ax.invert_yaxis()
            ax.scatter(C[:, 0], C[:, 1], marker='*', s=100, color='yellow')
            plt.title("APs clusters and scenario density", fontsize=20)
            plt.show()

    def allocate_edcs(self, opt='n', n=3, EDC_min=2, EDC_max=2):
        flag2 = 0
        if opt == 'n':
            E_n = n
            kmeans = KMeans(n_clusters=E_n, random_state=0).fit(self.aps)
            E = kmeans.cluster_centers_
            C_EDC = kmeans.predict(self.aps)
            print(E)
            print(len(E))

        elif opt == 'max':
            E_n = len(self.aps)
            while flag2 != 1:
                kmeans = KMeans(n_clusters=E_n, random_state=0).fit(self.aps)
                E = kmeans.cluster_centers_
                C_EDC = kmeans.predict(self.aps)
                for i in range(E_n):
                    if (C_EDC.tolist()).count(i) > EDC_max:
                        flag2 = 1
                E_n = E_n - 1
            E_n = E_n + 2
            kmeans = KMeans(n_clusters=E_n, random_state=0).fit(self.aps)
            E = kmeans.cluster_centers_
            C_EDC = kmeans.predict(self.aps)
            print(E)
            print(len(E))

        elif opt == 'min':
            E_n = 1
            while flag2 != 1:
                kmeans = KMeans(n_clusters=E_n, random_state=0).fit(self.aps)
                E = kmeans.cluster_centers_
                C_EDC = kmeans.predict(self.aps)
                for i in range(E_n):
                    if (C_EDC.tolist()).count(i) < EDC_min:
                        flag2 = 1
                E_n = E_n + 1
            E_n = E_n - 2
            kmeans = KMeans(n_clusters=E_n, random_state=0).fit(self.aps)
            E = kmeans.cluster_centers_
            C_EDC = kmeans.predict(self.aps)
            print(E)
            print(len(E))

        elif opt == 'minmax':
            flag3 = 0
            C_E_aux = self.aps
            E_n = 1
            r_c = []
            while flag3 != 1:
                # print(r_c)
                while flag2 != 1:
                    kmeans = KMeans(n_clusters=E_n, random_state=0).fit(C_E_aux)
                    E = kmeans.cluster_centers_
                    C_EDC = kmeans.predict(C_E_aux)
                    # print(C_EDC)
                    for i in range(E_n):
                        if (C_EDC.tolist()).count(i) < EDC_max:
                            flag2 = 1
                    E_n = E_n + 1
                flag2 = 0
                E_n = E_n - 1
                kmeans = KMeans(n_clusters=E_n, random_state=0).fit(C_E_aux)
                E = kmeans.cluster_centers_
                C_EDC = kmeans.predict(C_E_aux)
                # print('now')
                # print(C_EDC)
                f = []
                # print(C_E_aux)
                # print(E)
                count = 0
                # print(C_E_aux)
                for index, item in enumerate(C_EDC.tolist()):
                    # print(index,item)
                    if len(C_EDC.tolist()) / EDC_max < 1:
                        r_c = np.vstack((r_c, E))
                        flag3 = 1
                    if (C_EDC.tolist()).count(item) <= EDC_max:
                        C_E_aux = np.delete(C_E_aux, index - count, 0)
                        count = count + 1
                        if item not in f:
                            if len(r_c) == 0:
                                r_c = np.concatenate((r_c, E[item]), axis=0)
                            else:
                                r_c = np.vstack((r_c, E[item]))
                            f.append(item)
                if len(C_E_aux) <= EDC_max:
                    flag3 = 1
            # print(r_c)
            kmeans = KMeans(n_clusters=len(r_c), init=r_c)
            E = r_c
            C_EDC = kmeans.fit_predict(self.aps)
            print(E)
            # print(kmeans.cluster_centers_)
            E_n = len(E)
            print(len(E))
        self.edcs = E

    def plot_scenario(self, title="Scenario", pdf_path=None):
        D_real = np.array(list(zip(self.data['x'], self.data['y'])))
        clusters_data_real = np.zeros(len(D_real))
        clusters_ap_real = np.zeros(len(self.aps))
        print('***********')
        print(self.aps)
        print(self.edcs)

        for i in range(len(self.aps)):
            distances = dist(self.aps[i], self.edcs)
            cluster = np.argmin(distances)
            clusters_ap_real[i] = cluster

        for i in range(len(D_real)):
            distances = dist(D_real[i], self.aps)
            cluster = np.argmin(distances)
            clusters_data_real[i] = clusters_ap_real[cluster]

        plt.figure(figsize=(10, 8))
        n_edcs = self.edcs.shape[0]

        palette1 = sns.color_palette(palette="pastel", n_colors=n_edcs)
        palette2 = sns.color_palette(palette="deep", n_colors=n_edcs)
        palette3 = sns.color_palette(palette=None, n_colors=n_edcs)
        sns.scatterplot(x=self.data['x'], y=self.data['y'], hue=clusters_data_real, palette=palette1, legend=False)
        sns.scatterplot(x=self.aps[:, 0], y=self.aps[:, 1], marker='s', s=200, hue=clusters_ap_real, palette=palette2, legend=False)
        sns.scatterplot(x=self.edcs[:, 0], y=self.edcs[:, 1], hue=range(n_edcs), palette=palette3, marker='o', s=500, legend=False)

        L = plt.legend().get_texts()
        for i in range(len(L)):
            L[i].set_text("edc_" + str(i))
            L[i].set_fontsize(20)
        plt.title(title, fontsize=40)
        plt.yticks(rotation=90, fontsize=20)
        plt.xticks(fontsize=20)
        plt.ylabel("y [m]", fontsize=30)
        plt.xlabel("x [m]", fontsize=30)
        if pdf_path is not None:
            plt.savefig(pdf_path)
        plt.show()
