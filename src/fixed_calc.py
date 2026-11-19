"""FIXED calculation = the original calculation, fed only with pings that pass the noise filter.

The distance logic itself is not rewritten: we reuse reference_calc.distance_per_driver_day,
so the only change is the noise filter in front of it. The day is still cut at UTC
(problem 3, out of scope, listed as not solved).
"""
from src import reference_calc
from src.geo import Map
from src.noise_filter import clean

load_pings = reference_calc.load_pings


def distance_per_driver_day(pings, geo_map=None):
    m = geo_map or Map()
    kept, _ = clean(pings, m)
    return reference_calc.distance_per_driver_day(kept, m)
