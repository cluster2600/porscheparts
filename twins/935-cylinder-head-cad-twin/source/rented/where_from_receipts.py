"""Write where.json for each run made on the rented machine, from the receipts that machine wrote.

Usage: python -I where_from_receipts.py SYNCED_DX TARGET_DX IMAGE RUN...
  SYNCED_DX  the copy of /root/dx brought back (receipts/, memlog.txt, witness/, RUN.log, RUN/)
  TARGET_DX  the private build-sim-dolfinx folder that record reads
Copies each RUN folder, its log and its launch hash, and the machine's witness into TARGET_DX, then
writes TARGET_DX/RUN/where.json. Nothing here is typed by hand: every value is read from a receipt.
"""
import json
import re
import shutil
import sys
from pathlib import Path

synced, target, image, runs = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4:]
peaks = {}
for line in (synced / "memlog.txt").read_text().splitlines():
    for name, mib in re.findall(r"(\S+)=(\d+)MiB", line):
        peaks[name] = max(peaks.get(name, 0), int(mib))
wit_dir = target / "witness-vast-20261121"
wit_dir.mkdir(exist_ok=True)
shutil.copy2(synced / "witness" / "witness.json", wit_dir / "witness.json")
assert json.loads((wit_dir / "witness.json").read_text())["passed"]
for run in runs:
    level, solver, procs = re.fullmatch(r"(.+)-(blr)-(\d+)p", run).groups()
    receipts = sorted((synced / "receipts").glob(f"env-run-{level}-*.txt"))
    assert len(receipts) == 1, (run, receipts)
    text = receipts[0].read_text()
    field = lambda key: re.search(rf"^{key}\s+(.+)$", text, re.M).group(1).strip()
    quota, period = (int(v) for v in field("cgroup_cpu").split())
    exit_code = int((synced / f"{run}.exit").read_text())
    assert exit_code == 0, (run, exit_code)
    assert (synced / f"{run}.script.sha256").read_text().split()[0] == field("script_sha256")
    for item in (run, f"{run}.log", f"{run}.script.sha256", f"{run}.exit"):
        src = synced / item
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, target / item)
    where = {
        "machine": "a rented container instance (Vast.ai), the image pulled by digest",
        "cpu": field("model name").lstrip(": ").strip(),
        "cpus_allowed": round(quota / period, 2),
        "memory_allowed_GiB": round(int(field("cgroup_mem")) / 2**30, 1),
        "image": image,
        "tool_reported": field("dolfinx"),
        "processes": int(procs),
        "started_utc": field("date"),
        "largest_resident_GiB_sampled_each_minute": round(peaks[run] / 1024, 1),
        "witness": "witness-vast-20261121/witness.json",
    }
    (target / run / "where.json").write_text(json.dumps(where, indent=1) + "\n")
    print(run, json.dumps(where))
