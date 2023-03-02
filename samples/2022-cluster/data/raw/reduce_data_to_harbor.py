import pandas as pd

min_lat = 37.78
max_lat = 37.81
min_long = -122.42
max_long = -122.39

JUNE_6 = 1212735600
JUNE_7 = 1212822000

input_filename = 'all_until_june_7.csv'
output_to_june_6 = 'harbor_until_june_6.csv'
output_june_6 = 'harbor_june_6.csv'

if __name__ == '__main__':
    df = pd.read_csv(input_filename)
    df = df[(min_long <= df['longitude']) & (df['longitude'] <= max_long) & (min_lat <= df['latitude']) & (df['latitude'] <= max_lat)]
    df[df['epoch'] < JUNE_6].to_csv(output_to_june_6, index=None)
    df[(df['epoch'] >= JUNE_6) & (df['epoch'] < JUNE_7)].to_csv(output_june_6, index=None)
