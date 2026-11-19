"""Acceptance A1 to A3 from ACCEPTANCE.md: checks the noise filter against the answer-key labels.
(A4 and A5 are in test_regression.py.) Runs on the fixed code only."""
import csv
from pathlib import Path

import pytest

from src import reference_calc
from src.noise_filter import clean

ROOT = Path(__file__).resolve().parent.parent
PINGS = ROOT / "data" / "pings.csv"


@pytest.fixture(scope="module")
def result(geo_map):
    labels = {r["ping_id"]: r["label"] for r in csv.DictReader(open(PINGS))}
    kept, rejected = clean(reference_calc.load_pings(PINGS), geo_map)
    return labels, kept, rejected


def test_a1_all_noise_excluded(result):
    labels, kept, _ = result
    noise_kept = [p["ping_id"] for p in kept if labels[p["ping_id"]].startswith("noise")]
    total_noise = sum(v.startswith("noise") for v in labels.values())
    assert total_noise == 133 and noise_kept == []


def test_a2_no_good_ping_dropped(result):
    labels, _, rejected = result
    good_dropped = [r["ping"]["ping_id"] for r in rejected
                    if labels[r["ping"]["ping_id"]] in ("clean", "out_of_order")]
    assert good_dropped == []


def test_a3_duplicates_not_counted(result):
    labels, kept, _ = result
    assert [p["ping_id"] for p in kept if labels[p["ping_id"]] == "duplicate"] == []
