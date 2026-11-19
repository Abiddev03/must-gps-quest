"""Pick which calculation the tests run against.

  CALC_IMPL=fixed      (default) -> src/fixed_calc.py      (must PASS)
  CALC_IMPL=reference            -> src/reference_calc.py  (old behaviour, must FAIL)
"""
import importlib
import os
import sys
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore", message=".*Stone Soup.*")

from src.geo import TO_LATLON, Map  # noqa: E402

OX, OY = 500000, 3873000  # same synthetic origin as data/generate_dataset.py
T0 = datetime(2026, 11, 5, 1, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="session")
def impl():
    name = os.environ.get("CALC_IMPL", "fixed")
    return importlib.import_module(f"src.{name}_calc")


@pytest.fixture(scope="session")
def geo_map():
    return Map()


def ping(i, x, y, driver="T1", sec=None):
    """Ping number i at (x, y) metres on the synthetic map, 10 s apart unless sec is given."""
    lon, lat = TO_LATLON.transform(OX + x, OY + y)
    return {"ping_id": f"T{i:03d}", "driver_id": driver,
            "ts": T0 + timedelta(seconds=10 * i if sec is None else sec), "lat": lat, "lon": lon}
