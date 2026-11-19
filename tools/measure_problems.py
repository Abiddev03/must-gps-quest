"""Measure how many km each fault adds or moves, one fault at a time.

This is analysis, so it is allowed to read the `label` answer key.
Usage: python tools/measure_problems.py
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import reference_calc  # noqa: E402
from src.geo import Map, distance_m  # noqa: E402
from src.rules import LOCAL_TZ  # noqa: E402

PINGS = ROOT / "data" / "pings.csv"


def load_labelled():
    with open(PINGS) as f:
        return [{"driver_id": r["driver_id"], "label": r["label"],
                 "ts": datetime.fromisoformat(r["ts_utc"].replace("Z", "+00:00")),
                 "lat": float(r["lat"]), "lon": float(r["lon"])} for r in csv.DictReader(f)]


def calc(rows, m, keep_noise=False, keep_dups=False, arrival_order=False, utc_day=False):
    """Rule-correct calculation, with switches to put ONE fault back in."""
    rows = [r for r in rows
            if (keep_noise or not r["label"].startswith("noise"))
            and (keep_dups or r["label"] != "duplicate")]
    if not arrival_order:
        rows = sorted(rows, key=lambda r: (r["driver_id"], r["ts"]))
    totals, last = {}, {}
    for r in rows:
        day = (r["ts"] if utc_day else r["ts"].astimezone(LOCAL_TZ)).date().isoformat()
        key = (r["driver_id"], day)
        totals.setdefault(key, 0.0)
        p = last.get(key)
        if p and m.in_zone(p["lat"], p["lon"]) and m.in_zone(r["lat"], r["lon"]):
            totals[key] += distance_m(p["lat"], p["lon"], r["lat"], r["lon"])
        last[key] = r
    return {k: v / 1000 for k, v in totals.items()}


def compare(name, got, expected):
    keys = sorted(set(got) | set(expected))
    abs_err = sum(abs(got.get(k, 0) - expected.get(k, 0)) for k in keys)
    net = sum(got.values()) - sum(expected.values())
    print(f"{name:34s} net {net:+8.3f} km   sum |error| per driver-day {abs_err:8.3f} km")
    return abs_err


def main():
    m = Map()
    rows = load_labelled()
    expected = calc(rows, m)
    exp_file = {(r["driver_id"], r["local_date"]): float(r["expected_km"])
                for r in csv.DictReader(open(ROOT / "data" / "expected.csv"))}
    assert all(abs(expected[k] - v) < 0.001 for k, v in exp_file.items()), "answer key mismatch"

    print(f"Expected total (rules followed): {sum(expected.values()):.3f} km\n")
    print("One fault at a time:")
    compare("1. GPS noise counted", calc(rows, m, keep_noise=True), expected)
    compare("2. Arrival order (out-of-order)", calc(rows, m, arrival_order=True), expected)
    compare("   Duplicates counted", calc(rows, m, keep_dups=True), expected)
    compare("3. Day cut at UTC, not UTC+9", calc(rows, m, utc_day=True), expected)
    print("\nOriginal reference calculation (all faults together):")
    ref = reference_calc.distance_per_driver_day(reference_calc.load_pings(PINGS), m)
    compare("   reference_calc.py", ref, expected)
    print("\nPer driver-day, reference vs expected:")
    for k in sorted(set(ref) | set(expected)):
        print(f"   {k[0]} {k[1]}  reference {ref.get(k, 0):7.3f}  expected {expected.get(k, 0):7.3f}")


if __name__ == "__main__":
    main()
