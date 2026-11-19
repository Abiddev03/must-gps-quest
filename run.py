"""ONE COMMAND to reproduce everything:  python run.py

1. regenerate the synthetic dataset (seed 42, same file every time)
2. measure the three problems
3. run the noise checker (before / after per driver per day)
4. run all tests on the FIXED calculation        -> must PASS
5. run the regression tests on the OLD calculation -> must FAIL
6. (optional, add --mutation) break the filter on purpose -> tests must catch it
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def step(title, cmd, env=None):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}", flush=True)
    r = subprocess.run(cmd, cwd=ROOT, env={**os.environ, **(env or {}),
                                           "PYTHONWARNINGS": "ignore"})
    return r.returncode


def main():
    step("1. Generate synthetic dataset", [PY, "data/generate_dataset.py"])
    step("2. Measure the three problems", [PY, "tools/measure_problems.py"])
    step("3. Noise checker", [PY, "tools/noise_checker.py"])
    new = step("4. Tests on the FIXED calculation (must pass)",
               [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"])
    old = step("5. Regression tests on the OLD calculation (must fail)",
               [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--tb=no",
                "tests/test_regression.py"], env={"CALC_IMPL": "reference"})
    mut = 0
    if "--mutation" in sys.argv:
        mut = step("6. Mutation check (tests must catch every broken part)",
                   [PY, "tools/mutation_check.py"])

    ok = new == 0 and old != 0 and mut == 0
    print(f"\n{'=' * 78}")
    print(f"Fixed calculation tests: {'PASS' if new == 0 else 'FAIL'}")
    print(f"Regression on old code:  {'FAILS as expected' if old != 0 else 'PASSES (BAD: test proves nothing)'}")
    if "--mutation" in sys.argv:
        print(f"Mutation check:          {'all caught' if mut == 0 else 'SOME MISSED'}")
    print(f"OVERALL: {'OK' if ok else 'NOT OK'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
