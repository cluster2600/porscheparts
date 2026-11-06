"""Exercise the actual Kali OpenFOAM importer on the synthetic native control.

Only the two-cell synthetic MSH is transferred. Existing image identity and
strict SSH host checking are required; no credentials or host settings change.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import time


IMAGE = "sha256:1ae1a454429ed155bfecae63a25f90889aabb7981705ef688c46328ba2acad36"
CONTROL = """FoamFile
{
    version 2.0;
    format ascii;
    class dictionary;
    object controlDict;
}
application checkMesh;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 0;
deltaT 1;
writeControl timeStep;
writeInterval 1;
writeFormat ascii;
runTimeModifiable false;
"""


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--ssh-destination", required=True)
    parser.add_argument("--host-key-alias", required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    assert sha(args.input) == "40854f4211df2d1d524abe338ff3c1086d1cac85a91e272ab7ba31bc5764158f"
    started = time.monotonic()
    ssh = ["ssh", "-6", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ForwardAgent=no",
           "-o", "UseKeychain=no", "-o", "ConnectTimeout=8", "-o", "HostKeyAlias=" + args.host_key_alias, args.ssh_destination]

    def remote(name, command, payload=None, seconds=180):
        result = subprocess.run([*ssh, command], input=payload, capture_output=True, timeout=seconds)
        (args.output / (name + ".stdout")).write_bytes(result.stdout)
        (args.output / (name + ".stderr")).write_bytes(result.stderr)
        (args.output / (name + "-execution.json")).write_text(json.dumps({"argv": [*ssh, command], "exit_code": result.returncode}, indent=2) + "\n")
        assert result.returncode == 0, "Remote step failed: " + name
        return result.stdout

    work = remote("create", "umask 077; mktemp -d /tmp/935-native-interop.XXXXXXXX").decode().strip()
    assert re.fullmatch(r"/tmp/935-native-interop\.[A-Za-z0-9]{8}", work)
    (args.output / "remote-progress.json").write_text(json.dumps({"private_work_directory": work, "only_synthetic_control": True}) + "\n")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, content in (("control.msh", args.input.read_bytes()), ("system/controlDict", CONTROL.encode())):
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = 0o600
            archive.addfile(info, io.BytesIO(content))
    remote("upload", "tar -xf - -C " + shlex.quote(work), buffer.getvalue())
    transferred = remote("input-hash", "sha256sum " + shlex.quote(work + "/control.msh")).decode().split()[0]
    assert transferred == sha(args.input)
    image_id = remote("image", "docker image inspect --format '{{.Id}}' " + IMAGE).decode().strip()
    assert image_id == IMAGE
    inner = """cd /work || exit 90
mkdir -p constant
ccx -v > ccx-version.log 2>&1
source /opt/openfoam14/etc/bashrc > foam-setup.log 2>&1 || exit 91
foamVersion > foam-version.log 2>&1
command -v gmshToFoam > converter-path.log 2>&1
timeout 60s gmshToFoam -case /work /work/control.msh > convert.log 2>&1
convert=$?
check=-1
: > check.log
if test "$convert" -eq 0; then
    timeout 60s checkMesh -case /work > check.log 2>&1
    check=$?
fi
printf '{"convert_exit":%s,"check_exit":%s}\n' "$convert" "$check" > receipt.json
"""
    command = "docker run --rm --pull=never --network none --read-only --cpus 1 --memory 512m --pids-limit 64 --user \"$(id -u):$(id -g)\" --tmpfs /tmp:rw,nosuid,size=64m --cidfile " + shlex.quote(work + "/container.id") + " --mount " + shlex.quote("type=bind,src=" + work + ",dst=/work") + " --entrypoint /bin/bash " + IMAGE + " -c " + shlex.quote(inner)
    remote("container", command)
    active = remote("container-closeout", "docker ps -a --filter id=\"$(cat " + shlex.quote(work + "/container.id") + ")\" --format '{{.ID}}'").decode().strip()
    assert not active, "Owned control container still exists"
    archive_bytes = remote("recovery", "tar -cf - -C " + shlex.quote(work) + " .")
    recovered = args.output / "recovered"
    recovered.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        archive.extractall(recovered, filter="data")
    assert sha(recovered / "control.msh") == sha(args.input)
    receipt = json.loads((recovered / "receipt.json").read_text())
    convert_log = (recovered / "convert.log").read_text()
    check_log = (recovered / "check.log").read_text()
    passed = receipt["convert_exit"] == 0 and receipt["check_exit"] == 0 and "Mesh OK." in check_log
    remote("cleanup", "rm -rf -- " + shlex.quote(work))
    result = {"source_sha256": sha(Path(__file__)), "input_sha256": sha(args.input), "input_scope": "Synthetic two-cell bipyramid only; no head or scan transferred",
              "image_id": image_id, "registry_source_build_attestation": False, "network": "none", "read_only_image": True,
              "cpus": 1, "memory_mib": 512, "command_timeout_seconds_each": 60,
              "calculix_version_output": (recovered / "ccx-version.log").read_text().strip(),
              "openfoam_version_output": (recovered / "foam-version.log").read_text().strip(),
              "converter_exit": receipt["convert_exit"], "check_mesh_exit": receipt["check_exit"], "synthetic_import_and_mesh_check_passed": passed,
              "convert_log_sha256": sha(recovered / "convert.log"), "check_log_sha256": sha(recovered / "check.log"),
              "converter_reports_ascii_only": "ASCII" in convert_log and receipt["convert_exit"] != 0,
              "owned_container_absent": True, "owned_staging_cleaned_after_recovery": True,
              "head_import_admitted": False, "head_field_solve_executed": False,
              "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
              "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
