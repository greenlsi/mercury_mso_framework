from math import log10, sqrt
from typing import Optional, Tuple


def euclidean_distance(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
    """Computes the euclidean distance between two points."""
    assert len(a) == len(b)
    return sqrt(sum(pow(x[0] - x[1], 2) for x in zip(a, b)))


def from_natural_to_db(x: float) -> Optional[float]:
    """Converts from linear to logarithmic."""
    return None if x == 0 else 10 * log10(x)


def from_db_to_natural(x: Optional[float]) -> float:
    """Converts from logarithmic to linear."""
    return 0 if x is None else pow(10, x / 10)


def from_watt_to_dbm(watt: float) -> Optional[float]:
    """Converts Watts to dBm."""
    return None if watt == 0 else from_natural_to_db(watt) + 30


def from_dbm_to_watt(dbm: Optional[float]) -> float:
    """Converts dBm to Watts."""
    return 0 if dbm is None else from_db_to_natural(dbm - 30)
