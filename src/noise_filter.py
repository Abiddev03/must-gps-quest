"""GPS noise filter (the fix).

Order of steps:
  0. Sort by each ping's own timestamp and drop duplicates (same driver, same timestamp).
     Needed first: in arrival order a speed check flags good pings and misses noise.
  1. Off-road check  (BUILT here, the gap): ping more than 100 m from the road path -> noise.
     Uses shapely distance in metres (reused), the rule itself is ours.
  2. Speed check     (REUSED): MovingPandas OutlierCleaner with v_max = 150 km/h.
  3. Guards          (BUILT here) for two weak spots found by reading MovingPandas' code:
     a. it always keeps the first ping, so a noisy first ping is kept and good pings after it
        are dropped -> we check the first ping against the next two pings ourselves;
     b. if cleaning leaves < 2 points it silently returns the ORIGINAL data -> we raise instead.

Returns (kept_pings, rejected) where rejected is a list of dicts with ping, reason and value.
"""
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")  # MovingPandas warns about an optional smoother we do not use
    import geopandas as gpd
    import movingpandas as mpd
    import pandas as pd

from src.geo import Map, distance_m
from src.rules import MAX_OFFROAD_M, MAX_SPEED_KMH


def kmh(a, b):
    dt = abs((b["ts"] - a["ts"]).total_seconds())
    return float("inf") if dt == 0 else distance_m(a["lat"], a["lon"], b["lat"], b["lon"]) / dt * 3.6


def _speed_clean(pings):
    """Run MovingPandas OutlierCleaner on one driver's pings (sorted). Returns kept ping_ids."""
    if len(pings) < 3:
        return {p["ping_id"] for p in pings}
    df = pd.DataFrame(pings)
    df["t"] = pd.to_datetime(df["ts"]).dt.tz_localize(None)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326).set_index("t")
    traj = mpd.Trajectory(gdf, traj_id=pings[0]["driver_id"])
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)  # guard b: never accept the silent fallback
        cleaned = mpd.OutlierCleaner(traj).clean(v_max=MAX_SPEED_KMH, units=("km", "h"))
    return set(cleaned.df["ping_id"])


def clean(pings, geo_map=None):
    m = geo_map or Map()
    rejected = []

    # 0. sort by own timestamp, drop duplicates
    pings = sorted(pings, key=lambda p: (p["driver_id"], p["ts"]))
    unique, seen = [], set()
    for p in pings:
        key = (p["driver_id"], p["ts"])
        if key in seen:
            rejected.append({"ping": p, "reason": "duplicate", "value": 0.0})
        else:
            seen.add(key)
            unique.append(p)

    # 1. off-road (built)
    on_road = []
    for p in unique:
        off = m.offroad_m(p["lat"], p["lon"])
        if off > MAX_OFFROAD_M:
            rejected.append({"ping": p, "reason": "off_road", "value": off})
        else:
            on_road.append(p)

    # 2. speed (reused) + 3a guard, per driver
    kept = []
    for driver in sorted({p["driver_id"] for p in on_road}):
        track = [p for p in on_road if p["driver_id"] == driver]
        # guard a: first ping too fast to BOTH of the next two pings -> it is the spike
        if len(track) >= 3 and kmh(track[0], track[1]) > MAX_SPEED_KMH \
                and kmh(track[0], track[2]) > MAX_SPEED_KMH:
            rejected.append({"ping": track[0], "reason": "speed",
                             "value": kmh(track[0], track[1])})
            track = track[1:]
        ok = _speed_clean(track)
        prev = None
        for p in track:
            if p["ping_id"] in ok:
                kept.append(p)
                prev = p
            else:
                rejected.append({"ping": p, "reason": "speed",
                                 "value": kmh(prev, p) if prev else float("nan")})
    kept.sort(key=lambda p: (p["driver_id"], p["ts"]))
    return kept, rejected
