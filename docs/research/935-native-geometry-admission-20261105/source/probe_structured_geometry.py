"""Bound geometry-only native checks after complete independent topology readback.

Exercises an analytic structured cube and its affine reflection before
the unchanged recovered head. No field solve, mesh edits or paid rental.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile
import time

import numpy as np


IMAGE = "sha256:1ae1a454429ed155bfecae63a25f90889aabb7981705ef688c46328ba2acad36"
PARENT_MANIFEST = "91fbc0ecc6dfdeb2b95949676698f0ea9a1a8605d783efdfa61e2fe3722ed64d"
HELPER_SHA = 'cf9a2aff75790a5b359703daa5baf8c943e2885a8151fe29cde01a03cf700689'


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, data):
    with path.open("x") as stream:
        stream.write(json.dumps(data, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--control-helper", type=Path, required=True)
    parser.add_argument("--frozen-reader", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ssh-destination", required=True)
    parser.add_argument("--host-key-alias", required=True)
    args = parser.parse_args()
    assert sha(args.parent / "manifest.json") == PARENT_MANIFEST
    witness = json.loads((args.parent / "independent-foam/report.json").read_text())
    assert witness["head"]["complete_topological_readback_passed"]
    assert witness["single_coordinate_corruption_refused"]
    expected = {row["path"]: row for row in json.loads((args.parent / "manifest.json").read_text())["files"]}
    assert sha(args.parent / "independent-foam/report.json") == expected["independent-foam/report.json"]["sha256"]
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    inputs = args.output / "inputs"
    inputs.mkdir()
    native = args.parent / "cloud-import-001/recovered"
    for name in ("head",):
        for path in sorted((native / name).rglob("*")):
            if not path.is_file():
                continue
            assert not path.is_symlink()
            relative = path.relative_to(native)
            target = inputs / relative
            assert sha(path) == expected[str(path.relative_to(args.parent))]["sha256"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    assert sha(args.control_helper) == HELPER_SHA
    spec = importlib.util.spec_from_file_location("structured_control_contract", args.control_helper)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.prepare(inputs / "control", native / "head/system/controlDict")
    shutil.copyfile(args.control_helper, inputs / "structured_control.py")
    assert sha(args.frozen_reader) == "fbcd4fc8dddb319aeff88131c678e26ccba6ae97decb988fcc185872c67644ae"
    spec = importlib.util.spec_from_file_location("frozen_native_list_reader", args.frozen_reader)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    folder = native / "head/constant/polyMesh"
    owners = reader.values(folder / "owner", 1, np.int64)
    neighbours = reader.values(folder / "neighbour", 1, np.int64)
    assert len(owners) == witness["head"]["faces"] and len(neighbours) == witness["head"]["internal_faces"]
    counts = np.bincount(owners[:len(neighbours)], minlength=witness["head"]["cells"])
    counts += np.bincount(neighbours, minlength=witness["head"]["cells"])
    assert counts.shape == (witness["head"]["cells"],) and np.all(counts <= 4)
    assert int(counts.sum()) == 2 * len(neighbours)
    boundary_text = (folder / "boundary").read_text()
    assert len(re.findall(r"\btype\s+patch\s*;", boundary_text)) == 1
    histogram = np.bincount(counts, minlength=5).tolist()
    write(args.output / "upstream-stencil-audit.json", {
        "frozen_reader_sha256": sha(args.frozen_reader),
        "native_points_cells_boundary_independently_exact": True,
        "uncoupled_boundary_patch_count": 1,
        "cells_by_internal_face_count_0_to_4": histogram,
        "minimum_exact_zero_internal_area_tensor_determinants": sum(histogram[:3]),
        "reason": "Rank of a sum of fewer than three outer products is below three; this is a neighbour-stencil metric, not a coordinate Jacobian",
        "native_extended_stencil_gate_known_to_fail": sum(histogram[:3]) > 0,
        "admission": "One unchanged geometry diagnostic only; no threshold tuning or field solve"})
    del counts, owners, neighbours
    files = [{"path": str(p.relative_to(inputs)), "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(inputs.rglob("*")) if p.is_file()]
    write(args.output / "input-manifest.json", {"files": files})
    archive_path = args.output / "inputs.tar.gz"
    with tarfile.open(archive_path, "w:gz", compresslevel=1) as archive:
        for row in files:
            archive.add(inputs / row["path"], arcname=row["path"], recursive=False)
    ssh = ["ssh", "-6", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", "ForwardAgent=no", "-o", "UseKeychain=no", "-o", "ConnectTimeout=8",
           "-o", "HostKeyAlias=" + args.host_key_alias, args.ssh_destination]

    def remote(name, command, payload=None, seconds=45, allow_failure=False):
        result = subprocess.run([*ssh, command], input=payload, capture_output=True, timeout=seconds)
        (args.output / (name + ".stdout")).write_bytes(result.stdout)
        (args.output / (name + ".stderr")).write_bytes(result.stderr)
        write(args.output / (name + "-execution.json"), {"argv": [*ssh, command], "exit_code": result.returncode})
        assert allow_failure or result.returncode == 0, name
        return result.stdout

    code = "import json,pathlib,shutil;m={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())};print(json.dumps({'available_memory':m['MemAvailable'],'home_free':shutil.disk_usage(pathlib.Path.home()).free}))"
    capacity = json.loads(remote("capacity", "python3 -c " + shlex.quote(code)))
    assert capacity["available_memory"] >= 10 * 1024**3 and capacity["home_free"] >= 8 * 1024**3
    plan = {"source_sha256": sha(Path(__file__)), "parent_manifest_sha256": PARENT_MANIFEST,
        "upstream_verdict": "Exact topology/readback passed; extreme conditioning and uncoupled stencil gate fail; one geometry diagnostic only",
        "control_helper_sha256": HELPER_SHA,
        "source_head_coordinates_cells_boundary_exact": True, "image_id": IMAGE,
        "capacity": capacity, "container_memory_gib": 8, "extra_swap_gib": 0, "cpus": 2,
        "control_timeout_seconds_each": 60, "head_timeout_seconds": 300,
        "outer_timeout_seconds": 600, "head_arguments": ["-noTopology", "-allGeometry"],
        "thresholds": "Unmodified native defaults; no relaxed acceptance criteria",
        "field_solve_permitted": False, "new_paid_compute_usd": 0}
    write(args.output / "plan.json", plan)
    work = remote("create", 'umask 077; mktemp -d "$HOME/935-native-geometry.XXXXXXXX"').decode().strip()
    assert re.fullmatch(r"/home/[^/]+/935-native-geometry\.[A-Za-z0-9]{8}", work)
    write(args.output / "remote-work.json", {"directory": work})
    with archive_path.open("rb") as stream:
        transferred = subprocess.run([*ssh, "cat > " + shlex.quote(work + "/inputs.tar.gz")], stdin=stream, capture_output=True, timeout=180)
    write(args.output / "upload-execution.json", {"exit_code": transferred.returncode, "bytes": archive_path.stat().st_size})
    assert transferred.returncode == 0
    assert remote("archive-hash", "sha256sum " + shlex.quote(work + "/inputs.tar.gz")).decode().split()[0] == sha(archive_path)
    remote("extract", "tar -xzf " + shlex.quote(work + "/inputs.tar.gz") + " -C " + shlex.quote(work), seconds=90)
    assert remote("image", "docker image inspect --format '{{.Id}}' " + IMAGE).decode().strip() == IMAGE
    inner = """cd /work || exit 90
source /opt/openfoam14/etc/bashrc > setup.log 2>&1 || exit 91
foamVersion > version.log 2>&1
timeout --kill-after=10s 60s blockMesh -case control > block-mesh.log 2>&1 || exit 92
python3 structured_control.py --root /work > control-contract.log 2>&1 || exit 93
timeout --kill-after=10s 60s checkMesh -case control > default-control.log 2>&1
standard=$?
timeout --kill-after=10s 60s checkMesh -noTopology -allGeometry -case control > geometry-control.log 2>&1
geometry=$?
timeout --kill-after=10s 60s checkMesh -noTopology -allGeometry -case inverted-control > inverted-control.log 2>&1
inverted=$?
head=-1
if test "$standard" -eq 0 && test "$geometry" -eq 0 && grep -q 'Mesh OK.' default-control.log && grep -q 'Mesh OK.' geometry-control.log && ! grep -q 'Mesh OK.' inverted-control.log && grep -qi negative inverted-control.log && grep -Eq 'Number of negative volume cells: *8' inverted-control.log && grep -q 'Cell determinant check OK.' geometry-control.log; then
    timeout --kill-after=10s 300s checkMesh -noTopology -allGeometry -case head > head-geometry.log 2>&1
    head=$?
fi
printf '{"default_control_exit":%s,"geometry_control_exit":%s,"inverted_control_exit":%s,"head_exit":%s}\\n' "$standard" "$geometry" "$inverted" "$head" > receipt.json
"""
    cidfile = shlex.quote(work + "/container.id")
    command = "timeout --kill-after=15s 600s docker run --rm --pull=never --network none --read-only --cpus 2 --memory 8g --memory-swap 8g --pids-limit 64 --user \"$(id -u):$(id -g)\" --tmpfs /tmp:rw,nosuid,size=64m --cidfile " + cidfile + " --mount " + shlex.quote("type=bind,src=" + work + ",dst=/work") + " --entrypoint /bin/bash " + IMAGE + " -c " + shlex.quote(inner)
    remote("container", command, seconds=625, allow_failure=True)
    cid = remote("container-id", "cat " + cidfile).decode().strip()
    assert re.fullmatch(r"[0-9a-f]{64}", cid)
    if remote("container-presence", "docker ps -a --filter id=" + cid + " --format '{{.ID}}'").strip():
        remote("owned-container-stop", "docker rm -f " + cid)
    assert not remote("container-closeout", "docker ps -a --filter id=" + cid + " --format '{{.ID}}'").strip()
    manifest_code = "import hashlib,json,pathlib;r=pathlib.Path(" + repr(work) + ");print(json.dumps({str(p.relative_to(r)):{'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in r.rglob('*') if p.is_file()}))"
    manifest = json.loads(remote("remote-manifest", "python3 -c " + shlex.quote(manifest_code), seconds=120))
    originals = {row["path"]: row for row in files}
    assert all(manifest[name]["sha256"] == row["sha256"] and manifest[name]["bytes"] == row["bytes"] for name, row in originals.items()), "Native check modified an input"
    assert manifest["inputs.tar.gz"]["sha256"] == sha(archive_path)
    generated = [name for name in manifest if name not in originals and name != "inputs.tar.gz"]
    list_payload = "\n".join(generated).encode() + b"\n"
    remote("recovery-list", "cat > " + shlex.quote(work + "/recovery-list.txt"), list_payload)
    recovered_archive = args.output / "results.tar.gz"
    with recovered_archive.open("xb") as stream:
        result = subprocess.run([*ssh, "tar -czf - -C " + shlex.quote(work) + " -T " + shlex.quote(work + "/recovery-list.txt")], stdout=stream, stderr=subprocess.PIPE, timeout=180)
    assert result.returncode == 0
    recovered = args.output / "recovered"
    recovered.mkdir()
    with tarfile.open(recovered_archive, "r:gz") as archive:
        archive.extractall(recovered, filter="data")
    for name in generated:
        assert (recovered / name).stat().st_size == manifest[name]["bytes"] and sha(recovered / name) == manifest[name]["sha256"]
    receipt_path = recovered / "receipt.json"
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {"head_exit": None}
    def log(name):
        path = recovered / name
        return path.read_text() if path.exists() else ""
    controls_passed = (receipt.get("default_control_exit") == receipt.get("geometry_control_exit") == 0
                       and "Mesh OK." in log("default-control.log") and "Mesh OK." in log("geometry-control.log")
                       and "Mesh OK." not in log("inverted-control.log")
                       and re.search(r"Number of negative volume cells:\s*8", log("inverted-control.log")) is not None
                       and "Cell determinant check OK." in log("geometry-control.log"))
    native_pass = controls_passed and receipt["head_exit"] == 0 and "Mesh OK." in log("head-geometry.log")
    remote("cleanup", "rm -rf -- " + shlex.quote(work))
    assert remote("staging-closeout", "test ! -e " + shlex.quote(work) + "; echo absent").decode().strip() == "absent"
    report = {**plan, "native_exit": receipt, "controls_passed": controls_passed,
        "control_contract": json.loads((recovered / "control-contract.json").read_text()) if (recovered / "control-contract.json").exists() else None,
        "upstream_stencil_audit": json.loads((args.output / "upstream-stencil-audit.json").read_text()),
        "native_head_geometry_selected_checks_passed": native_pass,
        "native_complete_topology_check_not_completed_by_this_selector": True,
        "all_original_case_files_rehashed_unchanged": True,
        "original_case_files_verified": len(files), "generated_files_recovered_and_verified": len(generated),
        "archive_sha256": sha(recovered_archive), "owned_container_absent": True,
        "owned_staging_cleaned_after_verified_recovery": True,
        "native_head_log_sha256": sha(recovered / "head-geometry.log") if (recovered / "head-geometry.log").exists() else None,
        "case_specific_operator_admission": False, "field_solve_executed": False,
        "physics_admitted": False, "manufacturing_qualified": False, "seconds": time.monotonic() - started}
    write(args.output / "report.json", report)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
