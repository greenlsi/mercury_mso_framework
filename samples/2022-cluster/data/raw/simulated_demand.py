import pandas as pd


def simulated_demand():
    for edc_id in 'edc_0', 'edc_1', 'edc_2':
        for extension in 'hourly', 'friday':
            df = pd.read_csv(f'{edc_id}_{extension}_demand.csv')
            df['hour'] = df['hour'] - df['hour'].min()
            df.to_csv(f'../{edc_id}_demand_{extension}.csv', index=False)


if __name__ == '__main__':
    simulated_demand()
