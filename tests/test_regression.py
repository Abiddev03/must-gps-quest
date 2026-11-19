"""Regression check for the GPS-noise problem.

Run:  pytest                         -> fixed calculation, every test must PASS
      CALC_IMPL=reference pytest     -> old calculation, these tests must FAIL
Small hand-made tracks on the bottom road of the synthetic map (y = 0), inside the zone.
Expected distance = the same track without the noise ping, so no hard-coded metres.
"""
import csv
from pathlib import Path

import pytest

from conftest import ping
from src.geo import distance_m

ROOT = Path(__file__).resolve().parent.parent
TOL_KM = 0.001  # 1 metre


def path_km(points):
    return sum(distance_m(a["lat"], a["lon"], b["lat"], b["lon"])
               for a, b in zip(points, points[1:])) / 1000


def total(impl, geo_map, pings):
    return sum(impl.distance_per_driver_day(pings, geo_map).values())


def good_track(n=6, step=100):
    return [ping(i, 100 + i * step, 0) for i in range(n)]  # 36 km/h along the road


def test_off_road_ping_not_counted(impl, geo_map):
    good = good_track()
    noisy = good[:3] + [ping(3, 400, 300)] + good[4:]          # 300 m off the road
    expected = path_km(good[:3] + good[4:])
    assert total(impl, geo_map, noisy) == pytest.approx(expected, abs=TOL_KM)


def test_speed_spike_not_counted(impl, geo_map):
    good = good_track()
    noisy = good[:3] + [ping(3, 1000, 0)] + good[4:]           # on road (corner), 700 m in 10 s
    expected = path_km(good[:3] + good[4:])
    assert total(impl, geo_map, noisy) == pytest.approx(expected, abs=TOL_KM)


def test_noisy_first_ping_not_counted(impl, geo_map):
    # MovingPandas always keeps the first point; our guard must catch this
    good = good_track()
    noisy = [ping(0, 500, 1200)] + good[1:]                    # first ping on the far road, ~1.2 km away
    expected = path_km(good[1:])
    assert total(impl, geo_map, noisy) == pytest.approx(expected, abs=TOL_KM)


def test_off_road_ping_does_not_knock_out_next_good_ping(impl, geo_map):
    # Found in the dataset (P03119 -> P03120): a ping 410 m off-road passes the speed check
    # (~148 km/h) and then makes the next GOOD ping look like ~183 km/h.
    good = [ping(i, 100 + i * 150, 0) for i in range(6)]       # 54 km/h
    noisy = good[:2] + [ping(2, 250, 410)] + good[3:]
    expected = path_km(good[:2] + good[3:])
    assert total(impl, geo_map, noisy) == pytest.approx(expected, abs=TOL_KM)


def test_out_of_order_good_ping_is_not_treated_as_noise(impl, geo_map):
    good = good_track()
    arrived = good[:2] + good[3:] + [good[2]]                  # ping 2 arrives last
    assert total(impl, geo_map, arrived) == pytest.approx(path_km(good), abs=TOL_KM)


def test_duplicate_counted_once(impl, geo_map):
    good = good_track()
    with_dup = good[:4] + [dict(good[1], ping_id="DUP")] + good[4:]
    assert total(impl, geo_map, with_dup) == pytest.approx(path_km(good), abs=TOL_KM)


def test_dataset_matches_acceptance_target(impl, geo_map):
    """A4 from ACCEPTANCE.md: every driver-day within 0.05 km of the target."""
    target = {("D01", "2026-11-01"): 22.719, ("D01", "2026-11-02"): 39.320,
              ("D01", "2026-11-03"): 10.352, ("D02", "2026-11-02"): 36.827,
              ("D02", "2026-11-03"): 39.043, ("D03", "2026-11-01"): 11.677,
              ("D03", "2026-11-02"): 34.745, ("D03", "2026-11-03"): 21.407}
    got = impl.distance_per_driver_day(impl.load_pings(ROOT / "data" / "pings.csv"), geo_map)
    wrong = {k: round(got.get(k, 0), 3) for k in target if abs(got.get(k, 0) - target[k]) > 0.05}
    assert not wrong, f"driver-days off target: {wrong}"
