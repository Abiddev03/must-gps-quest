# Directive (how the work was done)

## Approach
1. **Sort** pings by timestamp, then **remove duplicates**.
2. **Off-road check** (the gap we built): drop pings more than **100 m** from the road, using shapely.
3. **Speed check** (reused, not rebuilt): MovingPandas `OutlierCleaner` with `v_max = 150 km/h`.
4. Recalculate distance per vehicle per UTC day.

## Why off-road runs before speed
Off-road ping P03119 (386 m from the road) passed the speed check, and it made the next good ping, P03120, look like 168 km/h. Running speed first would have dropped the good ping and kept the bad one. So the order matters, and a test locks it in.

## Rules for working with AI
- Claude wrote and ran the code. I set the problem, the rules and the acceptance numbers, reviewed every change, and ran everything again on my own Mac (Python 3.9).
- Every number in the evidence was reproduced on my machine, not only in the AI's environment.
- Tests must fail on the old code. A test that passes on both old and new code proves nothing.
- Mutation testing checks that the tests would catch a broken fix.

## How to run
```bash
pip install -r requirements.txt
python run.py              # cleaning + distance report
python run.py --mutation   # tests + mutation check, should print OVERALL: OK
```
