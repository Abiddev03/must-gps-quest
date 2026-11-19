"""SYNTHETIC dataset generator. No real people, places or MUST data.

Writes:
  data/road.geojson    - the road path the vehicles drive on (a loop)
  data/zone.geojson    - the campaign zone polygon
  data/pings.csv       - GPS pings in ARRIVAL order, each with a `label` column (answer key)
  data/expected.csv    - distance per driver per local day if the rules are followed (answer key)

The `label` column is for checking only. Calculations must NOT read it.
Deterministic: same seed -> same file every time.
"""
import csv
import json
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shapely.geometry import LineString, Point, Polygon, mapping  # noqa: E402

from src.geo import TO_LATLON, distance_m  # noqa: E402
from src.rules import LOCAL_TZ, PING_INTERVAL_S  # noqa: E402

SEED = 42
DATA = ROOT / "data"
OX, OY = 500000, 3873000  # origin in UTM 53N metres (synthetic area)

# Road loop in metres relative to origin (about 7 km around)
ROAD_REL = [(0, 0), (1000, 0), (1400, 300), (2000, 300), (2000, 1200), (0, 1200), (0, 0)]
# Zone covers the loop except the strip with x > 1500 m
ZONE_REL = [(-300, -300), (1500, -300), (1500, 1500), (-300, 1500), (-300, -300)]

DRIVERS = {"D01": (8, 0), "D02": (18, 0), "D03": (8, 30)}  # shift start, local time
DAYS = ["2026-11-02", "2026-11-03"]
SHIFT_MIN = 90

P_OFFROAD, P_SPEED, P_LATE, P_DUP = 0.025, 0.015, 0.03, 0.02


def to_ll(x, y):
    lon, lat = TO_LATLON.transform(OX + x, OY + y)
    return lat, lon


def geojson(rel_coords, kind):
    ll = [to_ll(x, y)[::-1] for x, y in rel_coords]  # GeoJSON is lon, lat
    geom = LineString(ll) if kind == "line" else Polygon(ll)
    return {"type": "Feature", "properties": {"synthetic": True}, "geometry": mapping(geom)}


def simulate_shift(rng, road, driver, day):
    """Return list of ping dicts for one driver on one local day."""
    h, m = DRIVERS[driver]
    start_local = datetime.fromisoformat(day).replace(hour=h, minute=m, tzinfo=LOCAL_TZ)
    t = start_local.astimezone(timezone.utc)
    end = t + timedelta(minutes=SHIFT_MIN)
    s = rng.uniform(0, road.length)
    speed, stop_left, prev_noise = 40.0, 0, False
    pings = []
    while t <= end:
        # speed model: cruise 25-55 km/h, sometimes stop at a light
        if stop_left > 0:
            v, stop_left = 0.0, stop_left - 1
        else:
            if rng.random() < 0.02:
                stop_left = rng.randint(3, 6)
            speed = min(55, max(25, speed + rng.uniform(-5, 5)))
            v = speed
        s = (s + v * PING_INTERVAL_S / 3.6) % road.length
        p = road.interpolate(s)
        x, y = p.x + rng.gauss(0, 4), p.y + rng.gauss(0, 4)  # normal GPS jitter ~4 m

        label = "clean"
        r = rng.random()
        if not prev_noise and r < P_OFFROAD:
            label = "noise_offroad"
            ahead = road.interpolate((s + 1) % road.length)
            dx, dy = ahead.x - p.x, ahead.y - p.y
            n = math.hypot(dx, dy) or 1
            for _ in range(20):  # push sideways until really >130 m from any road
                d = rng.uniform(150, 400) * rng.choice([-1, 1])
                x, y = p.x - dy / n * d, p.y + dx / n * d
                if road.distance(Point(x, y)) > 130:
                    break
        elif not prev_noise and r < P_OFFROAD + P_SPEED:
            label = "noise_speed"  # on the road, but jumped 900-1500 m ahead (>150 km/h)
            q = road.interpolate((s + rng.uniform(900, 1500)) % road.length)
            x, y = q.x + rng.gauss(0, 4), q.y + rng.gauss(0, 4)
        elif r < P_OFFROAD + P_SPEED + P_LATE:
            label = "out_of_order"
        prev_noise = label.startswith("noise")

        latency = rng.uniform(40, 120) if label == "out_of_order" else rng.uniform(1, 4)
        lat, lon = to_ll(x - OX, y - OY)
        pings.append({"driver_id": driver, "ts": t, "received": t + timedelta(seconds=latency),
                      "lat": lat, "lon": lon, "label": label})
        t += timedelta(seconds=PING_INTERVAL_S)

    dups = []
    for pg in pings:
        if pg["label"] == "clean" and rng.random() < P_DUP:
            dups.append({**pg, "received": pg["ts"] + timedelta(seconds=rng.uniform(15, 90)),
                         "label": "duplicate"})
    return pings + dups


def expected_by_rules(rows, zone):
    """Answer key: apply the rules using the labels (allowed here, not in the calculation)."""
    valid = [r for r in rows if r["label"] in ("clean", "out_of_order")]
    valid.sort(key=lambda r: (r["driver_id"], r["ts"]))
    totals = {}
    prev = None
    for r in valid:
        day = r["ts"].astimezone(LOCAL_TZ).date().isoformat()
        key = (r["driver_id"], day)
        totals.setdefault(key, 0.0)
        if prev and prev["driver_id"] == r["driver_id"] and prev_day == day:
            if zone.covers(Point(prev["lon"], prev["lat"])) and zone.covers(Point(r["lon"], r["lat"])):
                totals[key] += distance_m(prev["lat"], prev["lon"], r["lat"], r["lon"])
        prev, prev_day = r, day
    return totals


def main():
    rng = random.Random(SEED)
    road_m = LineString([(OX + x, OY + y) for x, y in ROAD_REL])
    road_gj, zone_gj = geojson(ROAD_REL, "line"), geojson(ZONE_REL, "poly")
    (DATA / "road.geojson").write_text(json.dumps(road_gj, indent=1))
    (DATA / "zone.geojson").write_text(json.dumps(zone_gj, indent=1))

    rows = []
    for day in DAYS:
        for driver in DRIVERS:
            rows += simulate_shift(rng, road_m, driver, day)
    rows.sort(key=lambda r: r["received"])  # file order = arrival order
    for i, r in enumerate(rows, 1):
        r["ping_id"] = f"P{i:05d}"

    with open(DATA / "pings.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ping_id", "driver_id", "ts_utc", "received_at_utc", "lat", "lon", "label"])
        for r in rows:
            w.writerow([r["ping_id"], r["driver_id"], r["ts"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        r["received"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        f"{r['lat']:.6f}", f"{r['lon']:.6f}", r["label"]])

    from shapely.geometry import shape
    zone = shape(zone_gj["geometry"])
    totals = expected_by_rules(rows, zone)
    with open(DATA / "expected.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["driver_id", "local_date", "expected_km"])
        for (d, day), m in sorted(totals.items()):
            w.writerow([d, day, f"{m / 1000:.3f}"])

    counts = {}
    for r in rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    print(f"SYNTHETIC dataset written: {len(rows)} pings")
    for k in sorted(counts):
        print(f"  {k:14s} {counts[k]}")


if __name__ == "__main__":
    main()
