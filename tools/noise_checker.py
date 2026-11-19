"""Noise checker: shows WHERE and WHY GPS noise inflates the distance report.

Usage:  python tools/noise_checker.py [path/to/pings.csv]

Output:
  - table per driver per day: original km, fixed km, km added by noise
  - every noise ping with its reason (metres off-road or km/h) and the km it added
  - reports/noise_report.csv with the same per-ping list (for the advertiser or the team)
  - if the file has a `label` column (our synthetic answer key), a self-check of the tool
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import fixed_calc, reference_calc  # noqa: E402
from src.geo import Map, distance_m  # noqa: E402
from src.noise_filter import clean  # noqa: E402


def segment_m(m, a, b):
    if a is None or b is None or a["ts"].date() != b["ts"].date():
        return 0.0
    if not (m.in_zone(a["lat"], a["lon"]) and m.in_zone(b["lat"], b["lon"])):
        return 0.0
    return distance_m(a["lat"], a["lon"], b["lat"], b["lon"])


def km_added(m, kept, noise):
    """For each noise ping: (prev->noise + noise->next) - (prev->next), prev/next = nearest kept pings."""
    by_driver = defaultdict(list)
    for p in kept:
        by_driver[p["driver_id"]].append(p)
    out = {}
    for r in noise:
        p = r["ping"]
        track = by_driver[p["driver_id"]]
        prev = next((q for q in reversed(track) if q["ts"] < p["ts"]), None)
        nxt = next((q for q in track if q["ts"] > p["ts"]), None)
        out[p["ping_id"]] = (segment_m(m, prev, p) + segment_m(m, p, nxt) - segment_m(m, prev, nxt)) / 1000
    return out


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "pings.csv"
    m = Map()
    pings = reference_calc.load_pings(path)
    before = reference_calc.distance_per_driver_day(pings, m)
    after = fixed_calc.distance_per_driver_day(pings, m)
    kept, rejected = clean(pings, m)
    noise = [r for r in rejected if r["reason"] != "duplicate"]
    added = km_added(m, kept, noise)

    noise_km = defaultdict(float)
    for r in noise:
        p = r["ping"]
        noise_km[(p["driver_id"], p["ts"].date().isoformat())] += added[p["ping_id"]]

    print(f"Pings read: {len(pings)}   noise found: {len(noise)} "
          f"(off_road {sum(r['reason'] == 'off_road' for r in noise)}, "
          f"speed {sum(r['reason'] == 'speed' for r in noise)})   "
          f"duplicates removed: {len(rejected) - len(noise)}\n")
    print(f"{'driver':6s} {'day (UTC)':10s} {'original km':>12s} {'fixed km':>9s} {'noise km':>9s}")
    for k in sorted(set(before) | set(after)):
        print(f"{k[0]:6s} {k[1]:10s} {before.get(k, 0):12.3f} {after.get(k, 0):9.3f} {noise_km[k]:9.3f}")
    print(f"{'TOTAL':17s} {sum(before.values()):12.3f} {sum(after.values()):9.3f} "
          f"{sum(noise_km.values()):9.3f}")
    print("(original - fixed is larger than 'noise km' because sorting by timestamp also removes the"
          " out-of-order inflation; see evidence.md)\n")

    out = ROOT / "reports" / "noise_report.csv"
    out.parent.mkdir(exist_ok=True)
    rows = sorted(noise, key=lambda r: -added[r["ping"]["ping_id"]])
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ping_id", "driver_id", "ts_utc", "lat", "lon", "reason", "value", "km_added"])
        for r in rows:
            p = r["ping"]
            unit = "m off road" if r["reason"] == "off_road" else "km/h"
            w.writerow([p["ping_id"], p["driver_id"], p["ts"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        p["lat"], p["lon"], r["reason"], f"{r['value']:.0f} {unit}",
                        f"{added[p['ping_id']]:.3f}"])
    print("Top 5 noise pings by km added:")
    for r in rows[:5]:
        p = r["ping"]
        unit = "m off road" if r["reason"] == "off_road" else "km/h"
        print(f"  {p['ping_id']} {p['driver_id']} {p['ts']:%Y-%m-%d %H:%M:%S}Z  "
              f"{r['reason']:8s} {r['value']:5.0f} {unit:10s} +{added[p['ping_id']]:.3f} km")
    print(f"Full list: {out.relative_to(ROOT)}\n")

    with open(path) as f:
        labels = {r["ping_id"]: r.get("label") for r in csv.DictReader(f)}
    if all(labels.values()):
        flagged = {r["ping"]["ping_id"] for r in noise}
        true_noise = {k for k, v in labels.items() if v.startswith("noise")}
        print("Self-check against answer-key labels:")
        print(f"  noise caught {len(flagged & true_noise)} of {len(true_noise)}, "
              f"good pings wrongly flagged {len(flagged - true_noise)}")


if __name__ == "__main__":
    main()
