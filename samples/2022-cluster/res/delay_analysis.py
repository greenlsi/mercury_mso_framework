import pandas as pd

JUNE_6 = 1212735600
DIRECTORY = '14_edge_slice_hybrid_50'
REQ_TYPES = {
    'OpenSessRequest': 'Open session requests (s)',
    'SrvRequest': 'Service requests (s)',
    'CloseSessRequest': 'Close session requests (s)',
}


def describe_srv_delay(dirname: str):
    df = pd.read_csv(f'{dirname}/transducer_srv_report_events.csv')
    df.drop(['client_id', 'service_id', 'req_n', 't_req_gen', 't_res_rcv', 'deadline_met',
             'acc_met_deadlines', 'acc_missed_deadlines', 'n_sess', 't_sess'], axis=1, inplace=True)
    for req_type, description in REQ_TYPES.items():
        req_df = df[df['req_type'] == req_type]['t_delay']
        print(f'{description}: {req_df.min()}; {req_df.mean()}; {req_df.max()}')


if __name__ == '__main__':
    describe_srv_delay(DIRECTORY)
