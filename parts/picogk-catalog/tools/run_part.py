#!/usr/bin/env python3
"""Build a generator group and run one part, under a machine-wide PicoGK lock.

Several PicoGK processes in parallel crashed the native kernel on this
project (see parts/picogk-993-batch-01/README.md), so every run takes a lock.

    python run_part.py <group> <PART_ID>

<group> is a folder of parts/picogk-catalog/ holding <Group>.csproj and its
generators. Parameters come from parts/<part-id>/source/picogk.json. Output:
parts/picogk-catalog/out/<PART_ID>.stl and .report.json (not committed).
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1]
ROOT = CATALOG.parents[1]
LOCK = Path(tempfile.gettempdir()) / "picogk-catalog.lock"
DOTNET = os.environ.get("DOTNET", r"C:\Program Files\dotnet\dotnet.exe" if os.name == "nt" else "dotnet")


def acquire(timeout_s=7200):
    start = time.time()
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {time.time()}".encode())
            os.close(fd)
            return
        except FileExistsError:
            if time.time() - LOCK.stat().st_mtime > 3600:      # stale: a run never takes an hour
                LOCK.unlink(missing_ok=True)
                continue
            if time.time() - start > timeout_s:
                raise SystemExit(f"lock {LOCK} held for over {timeout_s} s")
            time.sleep(5)


def main(group, part_id):
    gdir = CATALOG / group
    projects = list(gdir.glob("*.csproj"))
    if len(projects) != 1:
        raise SystemExit(f"expected one .csproj in {gdir}")
    params = ROOT / "parts" / part_id.lower() / "source" / "picogk.json"
    if not params.exists():
        raise SystemExit(f"missing {params}")
    env = dict(os.environ)
    env.setdefault("UpstreamRoot", str(ROOT.parent / "upstream"))
    bindir = Path(tempfile.gettempdir()) / "picogk-catalog" / group
    build = subprocess.run([DOTNET, "build", str(projects[0]), "-c", "Release", "-o", str(bindir),
                            "-p:GeneratePackageOnBuild=false", "-nologo", "-v:q"],
                           env=env, capture_output=True, text=True)
    if build.returncode:
        print(build.stdout[-4000:], build.stderr[-2000:])
        raise SystemExit("build failed")
    acquire()
    try:
        run = subprocess.run([DOTNET, str(bindir / (projects[0].stem + ".dll")), str(params), str(CATALOG / "out")],
                             env=env, capture_output=True, text=True)
    finally:
        LOCK.unlink(missing_ok=True)
    print(run.stdout.strip())
    if run.returncode:
        print(run.stderr[-3000:])
        raise SystemExit(f"run failed with exit code {run.returncode}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
