"""Recover unique native-origin outputs only after the worker is terminal."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
import time


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    ssh = json.loads((root / "ssh-argv.json").read_text())
    work = json.loads((root / "remote-work.json").read_text())["directory"]
    assert not (root / "origin-results.tar.gz").exists()
    source_inputs = json.loads((root / "inputs/input-manifest.json").read_text())["files"]

    def remote(name, code, seconds):
        command = "/opt/venv/bin/python -B -c " + shlex.quote(code)
        value = subprocess.run([*ssh, command], capture_output=True, text=True, timeout=seconds)
        (root / (name + "-execution.json")).write_text(json.dumps({"command": command, "exit_code": value.returncode}, indent=2) + "\n")
        assert value.returncode == 0, name
        return json.loads(value.stdout)

    code = """import hashlib,json,pathlib,time
r=pathlib.Path(WORK)
for _ in range(25):
 if (r/'result-manifest.json').exists():
  pid=json.loads((r/'pair-pid.json').read_text())['pid'];p=pathlib.Path('/proc')/str(pid)/'stat'
  state=p.read_text().rsplit(')',1)[1].split()[0] if p.exists() else 'absent'
  if state in ('Z','absent'):
   rows=json.loads((r/'input-manifest.json').read_text())['files']
   for x in rows:
    with (r/x['path']).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==x['sha256']
   print(json.dumps({'worker_pid':pid,'worker_state':state,'all_original_inputs_rehashed_unchanged':True,'manifest':json.loads((r/'result-manifest.json').read_text()),'terminal':json.loads((r/'terminal-state.json').read_text())}));break
 time.sleep(2)
else:raise RuntimeError('Worker not terminal; recovery refused')
""".replace("WORK", repr(work))
    state = remote("terminal-before-recovery", code, 100)
    (root / "terminal-before-recovery.json").write_text(json.dumps(state, indent=2) + "\n")
    manifest = state["manifest"]
    inputs = {row["path"]: row for row in source_inputs}
    for row in manifest["verified_input_copies"]:
        owner = inputs[row["matching_owner_input"]]
        assert row["sha256"] == owner["sha256"] and row["bytes"] == owner["bytes"]
        assert sha(root / "inputs" / owner["path"]) == row["sha256"]
    code = """import json,pathlib,sys,tarfile
r=pathlib.Path(WORK);m=json.loads((r/'result-manifest.json').read_text())
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',compresslevel=1) as archive:
 for row in m['files']:archive.add(r/row['path'],arcname=row['path'],recursive=False)
 archive.add(r/'result-manifest.json',arcname='result-manifest.json',recursive=False)
""".replace("WORK", repr(work))
    command = "/opt/venv/bin/python -B -c " + shlex.quote(code)
    archive_path = root / "origin-results.tar.gz"
    started = time.monotonic()
    with archive_path.open("xb") as stream:
        value = subprocess.run([*ssh, command], stdout=stream, stderr=subprocess.PIPE, timeout=600)
    (root / "results-transfer.json").write_text(json.dumps({"exit_code": value.returncode,
        "seconds": time.monotonic() - started, "bytes": archive_path.stat().st_size}, indent=2) + "\n")
    assert value.returncode == 0
    recovered = root / "recovered"
    recovered.mkdir(mode=0o700)
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            assert member.isfile() and not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
        archive.extractall(recovered, filter="data")
    assert json.loads((recovered / "result-manifest.json").read_text()) == manifest
    for row in manifest["files"]:
        path = recovered / row["path"]
        assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]
    result = {"archive_sha256": sha(archive_path), "source_sha256": sha(Path(__file__)),
        "worker_terminal": state["terminal"], "worker_confirmed_terminal_before_recovery": True,
        "all_original_inputs_rehashed_unchanged": True, "all_recovered_bytes_match": True,
        "unique_outputs_verified": len(manifest["files"]),
        "duplicate_input_copies_verified": len(manifest["verified_input_copies"]),
        "field_solve_executed": False, "physics_admitted": False, "manufacturing_qualified": False}
    with (root / "recovery-verification.json").open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
