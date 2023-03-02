import math
import pandas as pd

R = 6378137  # Radius of Earth in meters


class SphereToPlane:
    def __init__(self, radius):
        self.radius = radius
        self.lon_0 = None
        self.lat_0 = None

    def distance(self, lat1, lon1, lat2, lon2):
        """
        Havesine formula for computing distance between two points on a sphere

        :param lat1:
        :param lon1:
        :param lat2:
        :param lon2:
        :return:
        """
        d_lat = lat2 * math.pi / 180 - lat1 * math.pi / 180
        d_lon = lon2 * math.pi / 180 - lon1 * math.pi / 180
        a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180) \
            * math.sin(d_lon / 2) * math.sin(d_lon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        d = self.radius * c
        return d

    def to_x(self, lon: float):
        return self.distance(self.lat_0, lon, self.lat_0, self.lon_0)

    def to_y(self, lat: float):
        return self.distance(lat, self.lon_0, self.lat_0, self.lon_0)

    def to_x_y(self, lat, lon):
        return self.to_x(lon), self.to_y(lat)

    def set_reference_point(self, df):
        aux = df.min()
        self.lon_0 = aux['longitude']
        self.lat_0 = aux['latitude']


filepath_day = 'harbor_june_6.csv'
filepath_until = 'harbor_until_june_6.csv'

if __name__ == '__main__':
    converter = SphereToPlane(R)

    df = pd.read_csv(filepath_day, index_col=None)
    converter.set_reference_point(df)
    df['x'] = df['longitude'].apply(lambda lon: converter.to_x(lon))
    df['y'] = df['latitude'].apply(lambda lat: converter.to_y(lat))
    df = df[['cab_id', 'epoch', 'x', 'y']]
    df.to_csv('harbor_june_6_xy.csv', index=None)

    df = pd.read_csv(filepath_until, index_col=None)
    df['x'] = df['longitude'].apply(lambda lon: converter.to_x(lon))
    df['y'] = df['latitude'].apply(lambda lat: converter.to_y(lat))
    df = df[['cab_id', 'epoch', 'x', 'y']]
    df.to_csv('harbor_until_june_6_xy.csv', index=None)
