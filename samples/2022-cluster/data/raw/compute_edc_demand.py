from collections import deque
import pandas as pd

EDCS = {
    'edc_0': (1931.3381, 953.6472),
    'edc_1': (881.1543, 2310.8103),
    'edc_2': (705.3681, 764.5343),
}

filepath = 'harbor_until_june_6_xy.csv'
window_size = 70

if __name__ == '__main__':
    df = pd.read_csv(filepath, index_col=None)
    df.sort_values(by='epoch', inplace=True)
    for edc_id, (edc_x, edc_y) in EDCS.items():
        df[edc_id] = ((df['x'] - edc_x) ** 2 + (df['y'] - edc_y) ** 2) ** 0.5

    edc_df = pd.DataFrame(columns=['epoch', 'edc_id', 'demand'])
    cab_hits = dict()
    cab_best_edc = dict()
    prev_edc_demand = {edc_id: None for edc_id in EDCS}
    timeline = deque()

    x = df['epoch'].unique()

    for time in df['epoch'].unique():
        new_edc_demand = {edc_id: demand if demand is not None else 0 for edc_id, demand in prev_edc_demand.items()}
        time_df = df[df['epoch'] == time]
        for index, row in time_df.iterrows():
            # first we clear the window
            while timeline and timeline[0][0] < time - window_size:
                last_time, cab_id = timeline.popleft()
                cab_hits[cab_id] -= 1
                if cab_hits[cab_id] == 0:
                    cab_hits.pop(cab_id)
                    edc_id = cab_best_edc.pop(cab_id)
                    new_edc_demand[edc_id] -= 1
            # then we compute the best EDC and update the demand
            cab_id = row['cab_id']
            _, best_edc = min((row[edc_id], edc_id) for edc_id in EDCS)
            if cab_id not in cab_hits:
                cab_hits[cab_id] = 0
            cab_hits[cab_id] += 1
            prev_edc = cab_best_edc.get(cab_id)
            cab_best_edc[cab_id] = best_edc
            if prev_edc != best_edc:
                new_edc_demand[best_edc] += 1
                if prev_edc is not None:
                    new_edc_demand[prev_edc] -= 1
            timeline.append((time, cab_id))
        for edc_id, edc_demand in new_edc_demand.items():
            if edc_demand != prev_edc_demand[edc_id]:
                edc_df.loc[len(edc_df.index)] = [time, edc_id, edc_demand]
        prev_edc_demand = new_edc_demand
    edc_df.to_csv('demand_until_june_6.csv', index=False)
