# Session log (raw notes for directive.md and evidence.md)

## Session 1: 17 Nov 2026 23:53 PKT to 18 Nov 2026 ~00:20 PKT

### AI (Claude) did
- Wrote data/generate_dataset.py (synthetic, seed 42, 3,312 pings, labelled), src/geo.py, src/rules.py.
- Checked labels against the rules: clean max 15 m off-road, off-road noise min 134 m; speed noise min 268 km/h, clean max 59 km/h.
- Wrote src/reference_calc.py (old behaviour) and tools/measure_problems.py (one fault at a time).
- Measured impact: out-of-order +84.6 km, noise +52.9 km, day cut 77.9 km moved between days (+0.6 km net), duplicates 0 km if sorted.
- Found: a speed check in arrival order flags 41 good pings and catches only 47 of 133 noise pings.
- Found: the UTC day cut joins the last ping of one shift to the first ping of the next shift (~22 h gap) as one segment.
- Checked existing libraries: MovingPandas OutlierCleaner, scikit-mobility filtering.filter. Ran MovingPandas on the data: 45/45 speed noise, 3/88 off-road, 1 good ping dropped.

### Human (Abid) checked or decided
- Ran the generator and the measurement on his MacBook (Python 3.9.6). First run FAILED: requirements were pinned to versions that need Python 3.10+ (shapely 2.2.0). AI changed them to ranges and re-tested on Python 3.9. Second run on the Mac matched every number exactly (3,312 pings, +52.886, +84.601, +158.612 km).
- Mac needs `python3` and a venv; README must say so.
- Decided to pick the noise problem, even though out-of-order is larger in this dataset (AI recommended out-of-order). Abid's reasons (chosen by him, 18 Nov 00:09 PKT):
  1. The noise tool can show the advertiser, ping by ping, why each one was removed (metres off-road or km/h). That is what rebuilds trust in the report.
  2. Detecting noise needs the pings sorted by timestamp first, so this fix also removes most of the out-of-order inflation along with the +52.9 km of noise.
  3. Out-of-order alone is a one-line sort. Noise needs business rules (100 m, 150 km/h) and edge cases that need real testing, which is the QA work this Quest is about.

## Session 2: 18 Nov 2026 from 00:11 PKT (end time: Abid's clock)

### AI (Claude) did
- Read MovingPandas OutlierCleaner source before using it. Found 2 weak spots: it always keeps the first point; if fewer than 2 points remain it returns the ORIGINAL trajectory with only a warning.
- Wrote src/noise_filter.py: sort + dedupe, off-road check (built, shapely), speed check (reused, MovingPandas v_max=150 km/h), guard for noisy first ping, warning turned into an error.
- Wrote src/fixed_calc.py (original calc fed with filtered pings), tools/noise_checker.py, tests, run.py, tools/mutation_check.py, README.
- First run: all acceptance numbers met (133/133 noise, 0 good dropped, 0 duplicates, all 8 driver-days exact, total 216.090 km).
- Root cause of the 1 good ping MovingPandas dropped alone: P03119 is 386 m off-road but passes the speed check (139 km/h), then makes good ping P03120 look like 168 km/h. Fix: run off-road BEFORE speed. Added a test for it.
- Cross-check: checker's per-ping "km added" sums to 52.886 km = the independent measurement from session 1.
- AI's own mistakes caught while writing tests: two test points were not where intended ((1300,0) is 180 m off-road, so a "speed" test would have tested off-road; the first-ping test point did not meet the guard's condition). Fixed before running.
- Regression: 16/16 pass on fixed; 7/7 regression tests fail on old code.
- Mutation testing: first round 4 of 6 caught. Sort removal and dedupe removal were NOT caught (km stayed right because MovingPandas sorts by time and drops 0-second duplicates as infinite speed, but the report showed the wrong reason or km/h). Added 2 tests; now 6 of 6 caught.
- Fresh Python 3.9 venv from zero: python run.py --mutation -> OVERALL: OK, dataset byte-identical.

### Human (Abid) checked or decided
- TODO: run `python run.py --mutation` on the Mac and send the screenshot.
