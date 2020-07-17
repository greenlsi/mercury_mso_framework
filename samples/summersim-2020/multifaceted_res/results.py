import pandas as pd


models = ['classic', 'shortcut', 'lite']
scenarios = [i * 10 for i in range(1, 11)]


def prepare_edc_data():
    col_names = ['time']
    for model in models:
        col_names.extend(['{}_u'.format(model), '{}_power'.format(model)])

    for scenario in scenarios:
        dfs = dict()
        for model in models:
            u = '{}_u'.format(model)
            power = '{}_power'.format(model)
            aux_col_names = ['index', 'time', 'edc_id', u, 'u_max', 'pue',
                         power, 'i1', 'i2', 'i3', 'i4', 'i5', 'i6', 'i7']
            data = pd.read_csv('{}/{}/edc_report.csv'.format(model, scenario), sep='\t',
                               header=None, names=aux_col_names, index_col=0)
            data = data[['time', 'edc_id', u, power]]
            for edc_id in data['edc_id'].unique():
                if edc_id not in dfs:
                    df = pd.DataFrame(columns=col_names).set_index('time', drop=False)
                else:
                    df = dfs[edc_id]
                data_edc = data.loc[data['edc_id'] == edc_id]

                data_edc_new = data_edc.loc[~data_edc['time'].isin(df['time'])]
                data_edc_hit = data_edc.loc[data_edc['time'].isin(df['time'])]
                df = df.append(data_edc_new, sort=True)
                for index, row in data_edc_hit.iterrows():
                    df.loc[(df['time'] == row.time), u] = row[u]
                    df.loc[(df['time'] == row.time), power] = row[power]
                dfs[edc_id] = df

        for edc_id, df in dfs.items():
            df.sort_values('time', inplace=True)
            cols = list(df.columns)
            cols = [cols[-1]] + cols[:-1]
            df = df[cols]
            df = df.fillna(method='ffill')
            for i in ['u', 'power']:
                for model_1 in models:
                    label_1 = '{}_{}'.format(model_1, i)
                    flag = False
                    for model_2 in models:
                        label_2 = '{}_{}'.format(model_2, i)
                        if model_1 == model_2:
                            flag = True
                        elif flag:
                            df['{}_{}_vs_{}'.format(i, model_2, model_1)] = df[label_2] - df[label_1]
            df.to_csv('filtered/edc/{}_{}.csv'.format(scenario, edc_id), sep=';', index=False)


if __name__ == '__main__':
    prepare_edc_data()
