"""Run one bounded head import/check in the already qualified Kali image.

No field solve, geometry modification, secret access, image pull or paid rental.
Retain the complete native mesh and logs before removing task-owned staging.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import time


INPUT_SHA = "4052bfb3deb225b403873a79f73f01279b63bbbe500808540076103c5f4c3118"
PROBE_SHA = "e6bca21f9c31812dcd73e7801b375ecda68d671eac8c1e421b41fda58ff937d2"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "export-report", "control-report", "control-source", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--ssh-destination", required=True)
    parser.add_argument("--host-key-alias", required=True)
    args = parser.parse_args()
    assert sha(args.input) == INPUT_SHA and sha(args.control_source) == PROBE_SHA
    exported = json.loads(args.export_report.read_text())
    control = json.loads(args.control_report.read_text())
    assert exported["msh_sha256"] == INPUT_SHA
    assert exported["all_native_readback_coordinates_cells_and_boundary_exact"]
    assert control["synthetic_import_and_mesh_check_passed"]
    spec = importlib.util.spec_from_file_location("retained_precision_control", args.control_source)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    ssh = ["ssh", "-6", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", "ForwardAgent=no", "-o", "UseKeychain=no", "-o", "ConnectTimeout=8",
           "-o", "HostKeyAlias=" + args.host_key_alias, args.ssh_destination]

    def remote(name, command, payload=None, seconds=60, allow_failure=False):
        result = subprocess.run([*ssh, command], input=payload, capture_output=True, timeout=seconds)
        (args.output / (name + ".stdout")).write_bytes(result.stdout)
        (args.output / (name + ".stderr")).write_bytes(result.stderr)
        (args.output / (name + "-execution.json")).write_text(json.dumps({"argv": [*ssh, command], "exit_code": result.returncode}, indent=2) + "\n")
        assert allow_failure or result.returncode == 0, "Remote step failed: " + name
        return result.stdout

    capacity_code = "import json,pathlib,shutil; m={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())}; print(json.dumps({'memory_available':m['MemAvailable'],'home_free':shutil.disk_usage(pathlib.Path.home()).free}))"
    capacity = json.loads(remote("capacity", "python3 -c " + shlex.quote(capacity_code)))
    assert capacity["memory_available"] >= 10 * 1024**3
    assert capacity["home_free"] >= args.input.stat().st_size + 10 * 1024**3
    work = remote("create", 'umask 077; mktemp -d "$HOME/935-native-head.XXXXXXXX"').decode().strip()
    assert re.fullmatch(r"/home/[^/]+/935-native-head\.[A-Za-z0-9]{8}", work)
    (args.output / "plan.json").write_text(json.dumps({"source_sha256": sha(Path(__file__)),
        "input_sha256": INPUT_SHA, "capacity": capacity, "private_work_directory": work,
        "image_id": helper.IMAGE, "cpus": 2, "memory_gib": 8, "swap_gib": 0,
        "convert_timeout_seconds": 300, "check_timeout_seconds": 180,
        "outer_timeout_seconds": 600, "new_paid_compute_usd": 0,
        "geometry_gate_scope": "Exact stored volume and boundary; extreme conditioning persists; diagnostic import only",
        "field_solve_permitted": False}, indent=2) + "\n")
    with args.input.open("rb") as stream:
        result = subprocess.run([*ssh, "cat > " + shlex.quote(work + "/head.msh")], stdin=stream, capture_output=True, timeout=180)
    (args.output / "upload-execution.json").write_text(json.dumps({"exit_code": result.returncode}) + "\n")
    assert result.returncode == 0
    assert remote("input-hash", "sha256sum " + shlex.quote(work + "/head.msh")).decode().split()[0] == INPUT_SHA
    remote("dictionary", "mkdir -p " + shlex.quote(work + "/system") + "; cat > " + shlex.quote(work + "/system/controlDict"), helper.CONTROL.encode())
    assert remote("image", "docker image inspect --format '{{.Id}}' " + helper.IMAGE).decode().strip() == helper.IMAGE
    inner = """cd /work || exit 90
mkdir -p constant
source /opt/openfoam14/etc/bashrc > foam-setup.log 2>&1 || exit 91
foamVersion > foam-version.log 2>&1
timeout --kill-after=10s 300s gmshToFoam -case /work /work/head.msh > convert.log 2>&1
convert=$?
check=-1
: > check.log
if test "$convert" -eq 0; then
    timeout --kill-after=10s 180s checkMesh -case /work > check.log 2>&1
    check=$?
fi
printf '{"convert_exit":%s,"check_exit":%s}\\n' "$convert" "$check" > receipt.json
"""
    cid = shlex.quote(work + "/container.id")
    command = "timeout --kill-after=15s 600s docker run --rm --pull=never --network none --read-only --cpus 2 --memory 8g --memory-swap 8g --pids-limit 64 --user \"$(id -u):$(id -g)\" --tmpfs /tmp:rw,nosuid,size=64m --cidfile " + cid + " --mount " + shlex.quote("type=bind,src=" + work + ",dst=/work") + " --entrypoint /bin/bash " + helper.IMAGE + " -c " + shlex.quote(inner)
    remote("container", command, seconds=630, allow_failure=True)
    container_id = remote("container-id", "cat " + cid).decode().strip()
    assert re.fullmatch(r"[0-9a-f]{64}", container_id)
    if remote("container-presence", "docker ps -a --filter id=" + container_id + " --format '{{.ID}}'").strip():
        remote("owned-container-stop", "docker rm -f " + container_id)
    assert not remote("container-closeout", "docker ps -a --filter id=\"$(cat " + cid + ")\" --format '{{.ID}}'").strip()
    manifest_code = "import hashlib,json,pathlib; r=pathlib.Path(" + repr(work) + "); d={str(p.relative_to(r)):{'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in r.rglob('*') if p.is_file() and p.name!='head.msh'}; print(json.dumps(d,sort_keys=True))"
    manifest = json.loads(remote("remote-manifest", "python3 -c " + shlex.quote(manifest_code), seconds=180))
    archive_path = args.output / "recovered.tar.gz"
    with archive_path.open("xb") as stream:
        result = subprocess.run([*ssh, "tar --exclude=./head.msh -czf - -C " + shlex.quote(work) + " ."], stdout=stream, stderr=subprocess.PIPE, timeout=300)
    assert result.returncode == 0
    recovered = args.output / "recovered"
    recovered.mkdir()
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(recovered, filter="data")
    for name, metadata in manifest.items():
        path = recovered / name
        assert path.stat().st_size == metadata["bytes"] and sha(path) == metadata["sha256"]
    receipt_path = recovered / "receipt.json"
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {"convert_exit": None, "check_exit": None}
    receipt["container_exit"] = json.loads((args.output / "container-execution.json").read_text())["exit_code"]
    check_path = recovered / "check.log"
    check = check_path.read_text() if check_path.exists() else ""
    passed = receipt["convert_exit"] == 0 and receipt["check_exit"] == 0 and "Mesh OK." in check
    remote("cleanup", "rm -rf -- " + shlex.quote(work))
    assert remote("staging-closeout", "test ! -e " + shlex.quote(work) + "; echo absent").decode().strip() == "absent"
    report = {"source_sha256": sha(Path(__file__)), "input_sha256": INPUT_SHA,
        "export_report_sha256": sha(args.export_report), "control_report_sha256": sha(args.control_report),
        "image_id": helper.IMAGE, "capacity": capacity, "native_exit": receipt,
        "native_import_and_check_mesh_passed": passed, "archive_sha256": sha(archive_path),
        "recovered_files_verified": len(manifest), "owned_container_absent": True,
        "owned_staging_cleaned_after_verified_recovery": True,
        "all_native_head_arrays_independently_read_back": False,
        "case_specific_solver_admission": False, "head_field_solve_executed": False,
        "physics_admitted": False, "manufacturing_qualified": False,
        "new_paid_compute_usd": 0, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
