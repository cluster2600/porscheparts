"""Prepare, execute and recover an owned local native-frame diagnostic.

The control profile is required before the paired-head profile. No rental,
solver field calculation, global Docker cleanup or source modification occurs.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile
import time


IMAGE = "ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f"
IMAGE_ID = "sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696"
PARENT_SHA = "91fbc0ecc6dfdeb2b95949676698f0ea9a1a8605d783efdfa61e2fe3722ed64d"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--ssh-destination", required=True)
    parser.add_argument("--host-key-alias", required=True)
    parser.add_argument("--head", action="store_true")
    parser.add_argument("--control-receipt", type=Path)
    args = parser.parse_args()
    assert sha(args.parent / "manifest.json") == PARENT_SHA
    parent = json.loads((args.parent / "manifest.json").read_text())
    parent_index = {row["path"]: row for row in parent["files"]}
    if args.head:
        assert args.control_receipt
        control = json.loads(args.control_receipt.read_text())
        assert control["terminal"] == "native_origin_controls_completed" and control["controls_passed"]
        assert control["all_original_inputs_rehashed_unchanged"]
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    inputs = args.output / "inputs"
    inputs.mkdir()

    def copy(source, relative):
        assert source.is_file() and not source.is_symlink()
        target = inputs / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert sha(target) == sha(source)

    source = args.repository / "docs/research"
    for name, relative in {
        "run_origin_pair.py": "935-exact-origin-20261105/source/run_origin_pair.py",
        "certify_translation.py": "935-exact-origin-20261105/source/certify_translation.py",
        "native_worker.py": "935-native-geometry-admission-20261105/source/run_native_geometry.py",
        "structured_control.py": "935-native-geometry-admission-20261105/source/structured_control.py",
        "native_reader.py": "935-native-solver-admission-20261105/source/inspect_foam_readback.py",
    }.items():
        ast.parse((source / relative).read_text())
        copy(source / relative, name)
    copy(args.parent / "manifest.json", "parent-native-manifest.json")
    native = args.parent / "cloud-import-001/recovered"
    for folder, target_folder in [("control", "precision-source")] + ([("head", "native-head")] if args.head else []):
        for path in sorted((native / folder).rglob("*")):
            if path.is_file():
                assert sha(path) == parent_index[str(path.relative_to(args.parent))]["sha256"]
                copy(path, str(Path(target_folder) / path.relative_to(native / folder)))
    copy(args.parent / "ascii-control/precision-control.npz", "precision-reference.npz")
    if args.head:
        copy(args.proof / "report.json", "translation-proof.json")
        copy(args.proof / "expected-translated-points.npz", "expected-translated-points.npz")
    plan = {"run_head_pair": args.head, "foam_setup": "/opt/openfoam13/etc/bashrc",
        "translation": [-10, -10, -10], "field_solve_permitted": False, "image": IMAGE}
    write(inputs / "pair-plan.json", plan)
    rows = [{"path": str(path.relative_to(inputs)), "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in sorted(inputs.rglob("*")) if path.is_file()]
    write(inputs / "input-manifest.json", {"files": rows})
    shutil.copyfile(inputs / "input-manifest.json", args.output / "input-manifest.json")
    shutil.copyfile(Path(__file__), args.output / "controller-at-execution.py")
    archive_path = args.output / "inputs.tar.gz"
    with tarfile.open(archive_path, "w:gz", compresslevel=1) as archive:
        for path in sorted(inputs.rglob("*")):
            if path.is_file():
                archive.add(path, arcname=str(path.relative_to(inputs)), recursive=False)
    assert shutil.disk_usage(args.output).free >= 4 * 1024**3
    ssh = ["ssh", "-6", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", "ForwardAgent=no", "-o", "UseKeychain=no", "-o", "ConnectTimeout=8",
           "-o", "HostKeyAlias=" + args.host_key_alias, args.ssh_destination]

    def remote(name, command, payload=None, seconds=45, allow_failure=False):
        value = subprocess.run([*ssh, command], input=payload, capture_output=True, timeout=seconds)
        (args.output / (name + ".stdout")).write_bytes(value.stdout)
        (args.output / (name + ".stderr")).write_bytes(value.stderr)
        write(args.output / (name + "-execution.json"), {"command": command, "exit_code": value.returncode})
        assert allow_failure or value.returncode == 0, name
        return value.stdout

    code = "import json,pathlib,shutil;m={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())};print(json.dumps({'available_memory':m['MemAvailable'],'home_free':shutil.disk_usage(pathlib.Path.home()).free}))"
    capacity = json.loads(remote("capacity", "python3 -c " + shlex.quote(code)))
    assert capacity["available_memory"] >= (10 if args.head else 1) * 1024**3
    assert capacity["home_free"] >= (11 if args.head else 1) * 1024**3
    inspected = json.loads(remote("image", "docker image inspect " + shlex.quote(IMAGE)))[0]
    assert inspected["Id"] == IMAGE_ID and inspected["Architecture"] == "amd64"
    assert IMAGE in inspected["RepoDigests"]
    write(args.output / "phase-ledger.json", {"source_sha256": sha(Path(__file__)), "image": IMAGE,
        "image_id": IMAGE_ID, "inputs": rows, "runtime_capacity": capacity,
        "container_memory_mib": 8192 if args.head else 512, "extra_swap_mib": 0,
        "cpus": 2, "field_solve_permitted": False, "run_head_pair": args.head,
        "upstream_verdict": "Exact source geometry and winding; extreme conditioning and stencil defects remain; diagnostic only",
        "phases": ["verify owned inputs", "native analytic and precision controls", "unchanged baseline if selected",
                   "native exact transform and full readback if baseline completes", "translated diagnostic", "recover and verify", "owned cleanup"],
        "thresholds": "Native defaults unchanged", "outer_deadline_seconds": 2400,
        "failure_policy": "No paired continuation after incomplete baseline; stop only exact owned container at planned deadline; preserve and recover negative evidence",
        "expected_outputs": ["terminal-state.json", "precision-io-admission.json", "frame-comparison.json if complete pair", "Docker state", "complete recovery manifest"],
        "new_paid_compute_usd": 0, "cumulative_previous_reservation_ceilings_usd": 9.30,
        "actual_total_invoice_not_established": True})
    work = remote("create", 'umask 077; mktemp -d "$HOME/935-origin-pair.XXXXXXXX"').decode().strip()
    assert re.fullmatch(r"/home/[^/]+/935-origin-pair\.[A-Za-z0-9]{8}", work)
    write(args.output / "owned-work.json", {"directory": work})
    with archive_path.open("rb") as stream:
        uploaded = subprocess.run([*ssh, "cat > " + shlex.quote(work + "/inputs.tar.gz")], stdin=stream, capture_output=True, timeout=240)
    write(args.output / "upload-execution.json", {"exit_code": uploaded.returncode, "bytes": archive_path.stat().st_size})
    assert uploaded.returncode == 0
    assert remote("upload-hash", "sha256sum " + shlex.quote(work + "/inputs.tar.gz")).decode().split()[0] == sha(archive_path)
    remote("extract", "tar -xzf " + shlex.quote(work + "/inputs.tar.gz") + " -C " + shlex.quote(work), seconds=120)
    uidgid = remote("identity", "id -u; id -g").decode().split()
    assert len(uidgid) == 2 and all(value.isdecimal() for value in uidgid)
    command = ["docker", "run", "-d", "--pull=never", "--network", "none", "--read-only", "--cpus", "2",
        "--memory", "8g" if args.head else "512m", "--memory-swap", "8g" if args.head else "512m",
        "--pids-limit", "64", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", ":".join(uidgid), "--tmpfs", "/tmp:rw,nosuid,size=64m",
        "-e", "OPENBLAS_NUM_THREADS=1", "-e", "OMP_NUM_THREADS=1", "-e", "PYTHONDONTWRITEBYTECODE=1",
        "--mount", "type=bind,src=" + work + ",dst=/work", "--entrypoint", "/opt/venv/bin/python", IMAGE, "/work/run_origin_pair.py"]
    cid = remote("start", shlex.join(command)).decode().strip()
    assert re.fullmatch(r"[0-9a-f]{64}", cid)
    write(args.output / "owned-container.json", {"id": cid})
    # This is an execution deadline, not a transient observation timeout. The
    # detached container remains inspectable if the remote connection is lost.
    wait_code = """import json,subprocess,sys
cid=sys.argv[1]
try:
 p=subprocess.run(['docker','wait',cid],capture_output=True,text=True,timeout=2400)
 print(json.dumps({'deadline_reached':False,'wait_exit':p.returncode,'container_exit':p.stdout.strip(),'stderr':p.stderr}))
except subprocess.TimeoutExpired:
 p=subprocess.run(['docker','kill',cid],capture_output=True,text=True,check=True)
 q=subprocess.run(['docker','wait',cid],capture_output=True,text=True,check=True)
 print(json.dumps({'deadline_reached':True,'kill_exit':p.returncode,'container_exit':q.stdout.strip()}))
"""
    remote("wait", "python3 -c " + shlex.quote(wait_code) + " " + cid, seconds=2450)
    state = json.loads(remote("stopped-state", "docker inspect --format '{{json .State}}' " + cid))
    assert state["Running"] is False
    write(args.output / "docker-state.json", state)
    remote("docker-log", "docker logs " + cid, allow_failure=True)
    # Recompute every byte after all writers stop, including after an OOM. Do
    # not depend on a worker completing its own manifest in the failure case.
    recovery_code = """import hashlib,json,pathlib,sys,tarfile
r=pathlib.Path(sys.argv[1]); rows=json.loads((r/'input-manifest.json').read_text())['files']
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
for x in rows:
 p=r/x['path'];assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
lookup={(x['sha256'],x['bytes']):x['path'] for x in rows}
files=[];copies=[]
for p in sorted(r.rglob('*')):
 assert not p.is_symlink()
 if not p.is_file() or p.name=='inputs.tar.gz':continue
 x={'path':str(p.relative_to(r)),'bytes':p.stat().st_size,'sha256':sha(p)}
 key=(x['sha256'],x['bytes'])
 if key in lookup:copies.append({**x,'matching_owner_input':lookup[key]})
 else:files.append(x)
m={'files':files,'verified_input_copies':copies,'all_original_inputs_rehashed_unchanged':True,'all_writers_stopped_before_recovery':True}
(r/'recovery-manifest.json').write_text(json.dumps(m,indent=2)+'\\n')
with tarfile.open(r/'recovery.tar.gz','w:gz',compresslevel=1) as a:
 for x in files:a.add(r/x['path'],arcname=x['path'],recursive=False)
 a.add(r/'recovery-manifest.json',arcname='recovery-manifest.json',recursive=False)
print(json.dumps({'archive_sha256':sha(r/'recovery.tar.gz'),'archive_bytes':(r/'recovery.tar.gz').stat().st_size,'unique_output_count':len(files),'verified_input_copies':len(copies)}))
"""
    recovery = json.loads(remote("prepare-recovery", "python3 -c " + shlex.quote(recovery_code) + " " + shlex.quote(work), seconds=300))
    archive_path = args.output / "results.tar.gz"
    with archive_path.open("xb") as stream:
        got = subprocess.run([*ssh, "cat " + shlex.quote(work + "/recovery.tar.gz")], stdout=stream, stderr=subprocess.PIPE, timeout=240)
    assert got.returncode == 0 and sha(archive_path) == recovery["archive_sha256"]
    recovered = args.output / "recovered"
    recovered.mkdir()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            assert member.isfile() and not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
        archive.extractall(recovered, filter="data")
    recovered_manifest = json.loads((recovered / "recovery-manifest.json").read_text())
    for row in recovered_manifest["files"]:
        path = recovered / row["path"]
        assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]
    originals = {row["path"]: row for row in rows}
    for row in recovered_manifest["verified_input_copies"]:
        owner = originals[row["matching_owner_input"]]
        assert row["sha256"] == owner["sha256"] and row["bytes"] == owner["bytes"]
    for row in rows:
        assert sha(inputs / row["path"]) == row["sha256"]
    remote("remove-owned-container", "docker rm " + cid)
    assert not remote("verify-container-absent", "docker ps -a --filter id=" + cid + " --format '{{.ID}}'").strip()
    remote("remove-owned-work", "rm -rf -- " + shlex.quote(work))
    assert remote("verify-work-absent", "test ! -e " + shlex.quote(work) + " && echo absent").strip() == b"absent"
    write(args.output / "closeout.json", {"all_unique_outputs_recovered_and_rehashed": True,
        "all_original_inputs_unchanged": True, "owned_container_absent": True, "owned_staging_absent": True,
        "docker_oom_killed": state["OOMKilled"], "container_exit_code": state["ExitCode"],
        "recovery": recovery, "seconds": time.monotonic() - started, "new_paid_compute_usd": 0})
    print(json.dumps({"completed": True, "head_profile": args.head, "recovered": str(recovered), "docker_state": state}), flush=True)


if __name__ == "__main__":
    main()
