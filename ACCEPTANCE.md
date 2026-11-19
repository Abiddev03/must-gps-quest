# Acceptance test (written BEFORE the fix, 18 Nov 2026, 00:15 PKT)

Problem picked: **GPS noise is counted as distance.**
Rule: a ping more than 100 m off the road path, or one that implies a speed above 150 km/h, is noise and must be ignored.

Dataset: `data/pings.csv` (synthetic, seed 42): 3,312 pings = 3,113 good, 133 noise (88 off-road, 45 speed), 66 duplicates.

## Pass criteria (all must be true)

| # | Check | Before (reference_calc.py) | Target after fix |
|---|---|---|---|
| A1 | Noise pings excluded | 0 of 133 | **133 of 133 (100%)** |
| A2 | Good pings wrongly dropped | 0 of 3,113 | **0 of 3,113** |
| A3 | Duplicate pings counted | 66 of 66 kept | **0 of 66** |
| A4 | Distance per driver per day vs target below | off by +158.0 km in total | **every row within 0.05 km** |
| A5 | Regression check | must FAIL on reference_calc.py | must PASS on the fixed calculation |

## A4 target, km per driver per day

Target = the rules applied using the answer-key labels. The day is still cut at **UTC** midnight, because the day-cut fault (problem 3) is out of scope. This way the number measures only the noise fix.

| Driver | Day (UTC) | Before | Target |
|---|---|---|---|
| D01 | 2026-11-01 | 41.541 | 22.719 |
| D01 | 2026-11-02 | 65.704 | 39.320 |
| D01 | 2026-11-03 | 15.444 | 10.352 |
| D02 | 2026-11-02 | 62.725 | 36.827 |
| D02 | 2026-11-03 | 74.558 | 39.043 |
| D03 | 2026-11-01 | 14.452 | 11.677 |
| D03 | 2026-11-02 | 61.168 | 34.745 |
| D03 | 2026-11-03 | 38.488 | 21.407 |
| **Total** | | **374.079** | **216.090** |

## Notes

- To detect noise correctly, the pings must first be sorted by their own timestamp, and duplicates must be removed. In arrival order, a speed check flags 41 good pings and catches only 47 of the 133 noise pings. This sorting also removes most of the out-of-order fault (problem 2). We state that openly; it is not the picked problem.
- Measured before building: MovingPandas `OutlierCleaner(v_max=150 km/h)` catches 45 of 45 speed-noise pings but only 3 of 88 off-road pings, and drops 1 good ping. So speed is reused, and the off-road check is the gap we build.
