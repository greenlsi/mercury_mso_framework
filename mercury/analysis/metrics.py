import pandas as pd
from typing import Dict, List, Optional, Tuple


def integrate_col(df: pd.DataFrame, val_col: str, class_col: str = 'edc_id') -> Dict[str, float]:
    res: Dict[str, float] = dict()
    for class_id in df[class_col].unique():
        val = 0
        prev_t = 0
        prev_val = 0
        sub_df = df[df[class_col] == class_id]
        for _, row in sub_df.iterrows():
            new_t = row['time']
            new_val = row[val_col]
            val += prev_val * (new_t - prev_t)
            prev_t = new_t
            prev_val = new_val
        res[class_id] = val
    return res


def mean_value(df: pd.DataFrame, val_col: str, class_col: str = 'edc_id') -> Dict[str, float]:
    total_t = df['time'].max() - df['time'].min()
    return {class_id: val / total_t for class_id, val in integrate_col(df, val_col, class_col).items()}


def energy_per_edc(path: str, sep: str = ',', edc_col: str = 'edc_id',
                   pwr_col: str = 'power_demand') -> Dict[str, float]:
    return {edc_id: joules / 3600 for edc_id, joules in integrate_col(pd.read_csv(path, sep), pwr_col, edc_col).items()}


def mean_delay_per_service(path: str, sep: str = ',', ue_id: Optional[str] = None,
                           action: Optional[str] = None) -> Dict[str, float]:
    res: Dict[str, float] = dict()
    df = pd.read_csv(path, sep)
    if ue_id is not None:
        df = df[df['ue_id'] == ue_id]
    if action is not None:
        df = df[df['action'] == action]
    for srv_id in df['service_id'].unique():
        srv_df = df[df['service_id'] == srv_id]
        res[srv_id] = srv_df['delay'].mean()
    return res


def create_energy_report(consumers_path: str, offers_path: str, output_path: str, sep: str = ',',
                         consumer_col: str = 'consumer_id', pwr_col: str = 'power_consumption'):
    res = pd.DataFrame(columns=['time', consumer_col, pwr_col, 'acc_return', 'acc_energy', 'acc_cost'], index=None)

    # First, we process providers offers
    offers_df = pd.read_csv(offers_path, sep)
    offers: Dict[str, List[Tuple[float, float]]] = dict()
    """
    for provider in offers_df['provider_id'].unique():
        offers[provider] = deque((row['time'], row['electricity_cost']) for _, row in offers_df.iterrows())
    """
    offers['default'] = [(row['time'], row['electricity_cost']) for _, row in offers_df.iterrows()]

    consumers_df = pd.read_csv(consumers_path, sep)
    for consumer in consumers_df[consumer_col].unique():
        # provider_id = c_df['provider_id'].iloc[0]
        provider_id = 'default'
        offer = offers[provider_id]
        next_offer_i = 0
        prev_t, prev_offer, prev_power, acc_return, acc_energy, acc_cost = 0, 0, 0, 0, 0, 0
        for _, row in consumers_df[consumers_df[consumer_col] == consumer].iterrows():
            new_t = row['time']
            new_power = row[pwr_col]
            if new_t >= offer[next_offer_i][0]:
                t_offer, new_offer = offer[next_offer_i]
                next_offer_i += 1
                delta_energy = prev_power * (t_offer - prev_t) / 3600 if prev_power > 0 else 0
                delta_cost = delta_energy * prev_offer
                prev_t = t_offer
                prev_offer = new_offer
                acc_energy += delta_energy
                acc_cost += delta_cost
                res = res.append({'time': prev_t, consumer_col: consumer, pwr_col: prev_power,
                                  'acc_energy': acc_energy, 'acc_cost': acc_cost}, ignore_index=True)
            delta_return = prev_power * (new_t - prev_t) / 3600 if prev_power < 0 else 0
            delta_energy = prev_power * (new_t - prev_t) / 3600 if prev_power > 0 else 0
            delta_cost = delta_energy * prev_offer
            prev_t = new_t
            prev_power = new_power
            acc_return += delta_return
            acc_energy += delta_energy
            acc_cost += delta_cost
            res = res.append({'time': prev_t, consumer_col: consumer, pwr_col: prev_power, 'acc_return': acc_return,
                              'acc_energy': acc_energy, 'acc_cost': acc_cost}, ignore_index=True)
    res.sort_values('time', inplace=True)
    res.to_csv(output_path, sep, index=False)


def time_to_epoch(initial_epoch: int, input_path: str, output_path: str, sep: str = ','):
    df = pd.read_csv(input_path, sep, index_col=None)
    df['time'] = (df['time'] + initial_epoch).round().astype(int)
    df.rename(columns={'time': 'epoch'}, inplace=True)
    df.to_csv(output_path, sep, index=False)
