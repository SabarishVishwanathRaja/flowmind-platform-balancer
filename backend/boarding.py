"""Platform geometry and the boarding-time model.

Boarding time is derived from a simplified door-flow relation: per-door
passenger throughput degrades as platform density rises above ~1 pax/m2.
The constants here are illustrative and NOT calibrated against field data.
"""

from .config import *

ZONE_INDEX = {z: i for i, z in enumerate(ZONES)}


def zone_distance(a, b):
    return abs(ZONE_INDEX[a] - ZONE_INDEX[b])


def flow_rate(density):
    """Pax per door per second at a given platform density."""
    factor = 1.0 - 0.18 * max(0.0, density - 1.0)
    return BASE_FLOW * max(FLOW_FLOOR, factor)


def zone_boarding_time(count, density):
    if count <= 0:
        return 0.0
    return count / (DOORS_PER_ZONE * flow_rate(density))
