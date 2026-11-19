"""Unit checks on the noise filter itself (fixed code only)."""
import warnings

import pytest

from conftest import ping
from src.noise_filter import _speed_clean, clean


def test_good_ping_after_off_road_noise_is_kept(geo_map):
    # MovingPandas alone drops the good ping (P03120 case); off-road first must keep it.
    good = [ping(i, 100 + i * 150, 0) for i in range(6)]
    noise = ping(2, 250, 410)
    track = good[:2] + [noise] + good[3:]
    assert good[3]["ping_id"] not in _speed_clean(track)         # shows the library weakness
    kept, rejected = clean(track, geo_map)
    assert good[3] in kept                                         # our order fixes it
    assert [(r["ping"]["ping_id"], r["reason"]) for r in rejected] == [(noise["ping_id"], "off_road")]


def test_silent_fallback_is_an_error_not_a_pass(geo_map):
    # If MovingPandas would leave < 2 points it returns the ORIGINAL data with a warning.
    track = [ping(0, 100, 0), ping(1, 1000, 0), ping(2, 100, 1200)]
    with pytest.raises(UserWarning):
        _speed_clean(track)


def test_duplicate_reported_as_duplicate_not_as_speed(geo_map):
    # Found by mutation testing: without our own duplicate step, MovingPandas still drops the copy
    # (0 s apart = infinite speed), so km stay right but the report gives the wrong reason.
    track = [ping(i, 100 + i * 100, 0) for i in range(5)]
    track.append(dict(track[2], ping_id="DUP"))
    _, rejected = clean(track, geo_map)
    assert [(r["ping"]["ping_id"], r["reason"]) for r in rejected] == [("DUP", "duplicate")]


def test_report_does_not_depend_on_arrival_order(geo_map):
    # Found by mutation testing: without sorting first, the km/h shown for a spike is measured
    # against the wrong previous ping.
    track = [ping(i, 100 + i * 100, 0) for i in range(6)]
    track[3] = ping(3, 1000, 0)

    def summary(pings):
        _, rejected = clean(pings, geo_map)
        return sorted((r["ping"]["ping_id"], r["reason"], round(r["value"])) for r in rejected)

    assert summary(track[::-1]) == summary(track)


@pytest.mark.parametrize("off_m, is_noise", [(95, False), (105, True)])
def test_off_road_threshold_100_m(geo_map, off_m, is_noise):
    track = [ping(i, 100 + i * 100, 0) for i in range(5)]
    track[2] = ping(2, 300, off_m)
    _, rejected = clean(track, geo_map)
    assert (track[2]["ping_id"] in {r["ping"]["ping_id"] for r in rejected}) == is_noise
