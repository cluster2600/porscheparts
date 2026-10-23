#!/usr/bin/env python3
"""Run the gyroid-core variant of one part, under the machine-wide PicoGK lock.

    python run_gyroid.py <PART_ID>

Same build and lock as tools/run_part.py (which is SHA-pinned by a study's
refinement report and stays unchanged), with parameters from
parts/<part-id>/source/gyroid.json. Two differences: a lock whose holder
process is gone counts as stale (a memory-cap SIGKILL skips the release), and
the generator's core statistics (" cm3" lines) are printed on success.
Output: parts/picogk-catalog/out/<PART_ID>.stl, .report.json and .gyroid.json.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_part  # noqa: E402


def holder_alive():
    try:
        pid = int(run_part.LOCK.read_text().split()[0])
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (OSError, ValueError, IndexError):     # unreadable or another user's process: assume alive
        return True
    return True


def main(part_id):
    gdir = run_part.CATALOG / "bionic"
    project = gdir / "Bionic.csproj"
    params = run_part.ROOT / "parts" / part_id.lower() / "source" / "gyroid.json"
    if not params.exists():
        raise SystemExit(f"missing {params}; run prep_gyroid.py first")
    env = dict(os.environ)
    env.setdefault("UpstreamRoot", str(run_part.ROOT.parent / "upstream"))
    bindir = Path(tempfile.gettempdir()) / "picogk-catalog" / "bionic"
    build = subprocess.run([run_part.DOTNET, "build", str(project), "-c", "Release", "-o", str(bindir),
                            "-p:GeneratePackageOnBuild=false", "-nologo", "-v:q"],
                           env=env, capture_output=True, text=True)
    if build.returncode:
        print(build.stdout[-4000:], build.stderr[-2000:])
        raise SystemExit("build failed")
    if run_part.LOCK.exists() and not holder_alive():
        run_part.LOCK.unlink(missing_ok=True)
    run_part.acquire()
    try:
        run = subprocess.run([run_part.DOTNET, str(bindir / "Bionic.dll"), str(params), str(run_part.CATALOG / "out")],
                             env=env, capture_output=True, text=True)
    finally:
        run_part.LOCK.unlink(missing_ok=True)
    print(run.stdout.strip())
    print("\n".join(line for line in run.stderr.splitlines() if " cm3" in line and line.startswith("  [")))
    if run.returncode:
        print(run.stderr[-3000:])
        raise SystemExit(f"run failed with exit code {run.returncode}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
