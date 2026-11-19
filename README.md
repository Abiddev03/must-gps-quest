# GPS noise in vehicle-advertising distance: checker, fix and regression check

MUST Quest submission by Abid Ali Shah. **All data here is synthetic** (seed 42). No real people, places or MUST data.

Advertisers pay per km driven inside a campaign zone, and drivers are paid on the same km. GPS noise (pings more than 100 m off the road, or implying more than 150 km/h) was being counted as distance. This repo finds that noise, shows where and why it inflates the report, fixes the calculation, and adds a check so the problem cannot come back.

## Run it (one command)

Python 3.9 to 3.13. On macOS, use `python3` for the first two lines.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                      # add --mutation for the mutation check (~15 s more)
```

The last line should be `OVERALL: OK`. That means the fixed calculation passes all 16 tests, and the regression tests FAIL on the old calculation, as they must.

## What is where

| Path | What it is |
|---|---|
| `data/generate_dataset.py` | Builds the synthetic dataset: 3,312 pings, each labelled `clean`, `noise_offroad`, `noise_speed`, `duplicate` or `out_of_order` (answer key). |
| `data/pings.csv` | The pings, in arrival order. The calculations never read `label`. |
| `src/reference_calc.py` | The ORIGINAL calculation (old behaviour, wrong). Not edited. |
| `src/noise_filter.py` | The fix: sort and dedupe, then the off-road check (built), the speed check (MovingPandas, reused), and two guards. |
| `src/fixed_calc.py` | The original calculation fed only with pings that pass the filter. |
| `tools/noise_checker.py` | **The QA tool.** Before/after km per driver per day, every noise ping with its reason and the km it added. Writes `reports/noise_report.csv`. |
| `tools/measure_problems.py` | Measures each of the three problems one at a time (used for the ranking). |
| `tools/mutation_check.py` | Breaks each part of the filter on purpose and checks that a test fails. |
| `tests/` | Acceptance (A1 to A4), regression and filter unit tests. `CALC_IMPL=reference pytest` runs them on the old code. |
| `ACCEPTANCE.md` | The acceptance test as numbers, written before the fix. |

## Result

| | Before | After | Target |
|---|---|---|---|
| Total km (8 driver-days, UTC day) | 374.079 | 216.090 | 216.090 |
| Noise pings excluded | 0 of 133 | 133 of 133 | 133 of 133 |
| Good pings wrongly dropped | 0 | 0 | 0 |
| Duplicates counted | 66 | 0 | 0 |

Run the checker on your own file: `python tools/noise_checker.py path/to/pings.csv`. It needs the columns `ping_id, driver_id, ts_utc, lat, lon`. Note that the road and zone are fixed to `data/road.geojson` and `data/zone.geojson`.

See `intent.md` and `evidence.md` for the full story, and `directive.md` for how AI was used.
