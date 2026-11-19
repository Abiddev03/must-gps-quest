"""Mutation check: break one part of the noise filter at a time and confirm the tests catch it.

Usage: python tools/mutation_check.py      (takes about 15 seconds)
Works on a temporary copy; the real code is never changed.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MUTATIONS = [
    ("off-road check removed", "if off > MAX_OFFROAD_M:", "if False:"),
    ("first-ping guard removed", "if len(track) >= 3 and kmh", "if False and kmh"),
    ("speed check (MovingPandas) removed", "ok = _speed_clean(track)",
     'ok = {p["ping_id"] for p in track}'),
    ("sort by timestamp removed", 'pings = sorted(pings, key=lambda p: (p["driver_id"], p["ts"]))',
     "pass"),
    ("duplicate removal removed", "if key in seen:", "if False:"),
    ("silent-fallback guard removed", 'warnings.simplefilter("error", UserWarning)',
     'warnings.simplefilter("ignore")'),
]


def main():
    caught = 0
    for name, old, new in MUTATIONS:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".git"))
            f = copy / "src" / "noise_filter.py"
            src = f.read_text()
            assert old in src, f"mutation pattern not found: {old}"
            f.write_text(src.replace(old, new, 1))
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                               cwd=copy, capture_output=True, text=True)
            last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
            ok = r.returncode != 0
            caught += ok
            print(f"  {'CAUGHT ' if ok else 'MISSED '} {name:38s} {last}")
    print(f"Mutations caught: {caught} of {len(MUTATIONS)}")
    return 0 if caught == len(MUTATIONS) else 1


if __name__ == "__main__":
    sys.exit(main())
