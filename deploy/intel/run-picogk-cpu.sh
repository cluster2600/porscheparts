#!/usr/bin/env bash
set -euo pipefail

# Reuse the station's extracted, hash-checked runtime without a system install.
if [[ $# -ne 4 ]]; then
    echo 'Usage: run-picogk-cpu.sh BUNDLE_DIR NEW_OUTPUT_DIR SPAN_MM VOXEL_MM' >&2
    exit 2
fi
bundle=$(realpath "$1")
output=$(realpath -m "$2")
test -f "$bundle/bundle-manifest.json"
test ! -e "$output"
umask 077
exec 9>"$bundle/../.cpu-job.lock"
flock -n 9 || { echo "Kali1 CPU calculation already running" >&2; exit 75; }
mkdir -p "$output"

systemd-run --user --scope --quiet \
    -p CPUQuota=200% -p MemoryMax=2G -p MemorySwapMax=0 \
    -p TasksMax=128 -p RuntimeMaxSec=300 \
    /usr/bin/nice -n 10 /usr/bin/python3 - "$bundle" "$output" "$3" "$4" "$0" <<'PY'
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

bundle, output = (Path(value) for value in sys.argv[1:3])
span, voxel = (float(value) for value in sys.argv[3:5])
assert 20 <= span <= 80 and 0.1 <= voxel <= 0.5
manifest = json.loads((bundle / "bundle-manifest.json").read_text())
for record in manifest["files"]:
    path = bundle / record["path"]
    assert path.is_file() and not path.is_symlink()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
cgroup = Path("/sys/fs/cgroup") / Path("/proc/self/cgroup").read_text().strip().split("::", 1)[1].lstrip("/")
limits = {name: (cgroup / name).read_text().strip() for name in ["cpu.max", "memory.max", "memory.swap.max", "pids.max"]}
assert limits["memory.max"] == "2147483648" and limits["memory.swap.max"] == "0"
quota, period = map(int, limits["cpu.max"].split())
assert quota / period == 2
# Only fixed runtime variables are forwarded; workload credentials are unnecessary.
env = {"PATH": "/usr/bin:/bin", "HOME": str(output), "DOTNET_ROOT": str(bundle / "dotnet"),
       "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1", "DOTNET_PROCESSOR_COUNT": "2",
       "LD_LIBRARY_PATH": str(bundle / "native") + ":" + str(bundle / "native/lib")}
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
begin = time.monotonic()
commands = [("native-witness", [str(bundle / "witness/RuntimeWitness.dll"), str(output / "native-witness")]),
            ("demo", [str(bundle / "demo/StationDemo.dll"), str(output / "geometry"), str(span), str(voxel)])]
runs = []
for name, args in commands:
    before = time.monotonic()
    with (output / (name + ".log")).open("x") as log:
        run = subprocess.run([str(bundle / "dotnet/dotnet"), *args], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=240)
    runs.append({"task": name, "exit_code": run.returncode, "elapsed_seconds": round(time.monotonic() - before, 6)})
    if run.returncode:
        break
records = [{"path": str(p.relative_to(output)), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
           for p in sorted(output.rglob("*")) if p.is_file()]
report = {"schema_version": "1.0.0", "host": os.uname().nodename, "uid": os.getuid(),
          "started_at_utc": started, "finished_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "elapsed_seconds": round(time.monotonic() - begin, 6), "source_image_id": manifest["source_image_id"],
          "bundle_archive_sha256": manifest["archive_sha256"], "all_bundle_file_hashes_verified": True,
          "launcher_sha256": hashlib.sha256(Path(sys.argv[5]).read_bytes()).hexdigest(),
          "limits": limits, "wall_time_limit_seconds": 300, "nice": os.getpriority(os.PRIO_PROCESS, 0),
          "memory_peak_bytes": int((cgroup / "memory.peak").read_text()),
          "memory_events": (cgroup / "memory.events").read_text(),
          "children_max_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
          "span_mm": span, "voxel_mm": voxel, "runs": runs, "artifacts": records,
          "passed": len(runs) == 2 and all(run["exit_code"] == 0 for run in runs),
          "gpu_used": False, "manufacturing_validated": False}
(output / "execution.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({key: report[key] for key in ["host", "passed", "elapsed_seconds", "memory_peak_bytes", "span_mm", "voxel_mm"]}))
raise SystemExit(0 if report["passed"] else 1)
PY
