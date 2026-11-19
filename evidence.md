# Evidence

All numbers below were reproduced on my own Mac (Python 3.9).

## Data
- 3,312 pings: **133 noise** (88 off-road, 45 speed), **66 duplicates**, **120 out-of-order**.

## Impact of each problem (one at a time)
| Problem | Effect on distance |
|---|---|
| Out-of-order pings | +84.6 km |
| GPS noise | +52.9 km |
| Day cut (UTC vs UTC+9) | 77.9 km on the wrong day (out of scope) |

## Result
- Before: **374.079 km**. After: **216.090 km**. Target: **216.090 km**. Match.
- Noise caught: **133 / 133**. Good pings dropped: **0**.

## Tests
- **16/16** tests pass on the fixed code.
- **7/7** regression tests fail on the old code, so they really detect the bug.
- **6/6** mutations caught. `python run.py --mutation` prints `OVERALL: OK`.

## Findings
1. **Order matters.** Off-road ping P03119 (386 m) passed the speed check and made good ping P03120 look like 168 km/h. Off-road must run before speed.
2. **Library edge cases.** MovingPandas always keeps the first ping, and it silently returns the original data if fewer than 2 points remain. I added guards and tests for both.
3. **My tests had gaps at first.** Mutation testing caught only 4 of 6 mutations (sort and dedupe were not covered). I added two tests, and now 6 of 6 are caught.
4. **The AI made mistakes.** It placed 2 test points in the wrong spot. I caught and fixed them before running.
5. **Setup issue.** The first install on my Mac failed because of version pins that needed Python 3.10+. I changed them to version ranges and tested on 3.9.
