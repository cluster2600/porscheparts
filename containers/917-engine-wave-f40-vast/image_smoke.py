#!/usr/bin/env python3
"""Smoke hors ligne de la couche transport Vast et de la chute de privileges."""

from __future__ import annotations

import argparse
from importlib.metadata import version
import io
import json
import os
from pathlib import Path
import platform
import pwd
import shutil
import subprocess
import sys
import tarfile


ROOT = Path("/opt/917-engine-wave-f40-vast")
F39_SMOKE = Path("/opt/917-engine-wave-f39/smoke.py")
INBOX = Path("/workspace/inbox")
JOBS = Path("/workspace/jobs")
RESULTS = Path("/workspace/results")
JOB_ID = "image-smoke"
EXPECTED_PACKAGES = {
    "openssh-client": "1:9.2p1-2+deb12u10",
    "openssh-server": "1:9.2p1-2+deb12u10",
    "openssh-sftp-server": "1:9.2p1-2+deb12u10",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def command_stdout(command: list[str]) -> str:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    require(
        completed.returncode == 0,
        f"command failed ({completed.returncode}): {command[0]}: {completed.stderr}",
    )
    require(not completed.stderr, f"unexpected stderr from {command[0]}: {completed.stderr}")
    return completed.stdout


def package_audit(expect_runtime_authorized_keys: bool) -> dict[str, object]:
    installed = {
        package: command_stdout(["dpkg-query", "-W", "-f=${Version}", package]).strip()
        for package in EXPECTED_PACKAGES
    }
    require(installed == EXPECTED_PACKAGES, "OpenSSH package lock mismatch")
    require(Path("/usr/sbin/sshd").is_file(), "sshd binary missing")
    require(os.access("/usr/sbin/sshd", os.X_OK), "sshd binary is not executable")
    require(Path("/usr/lib/openssh/sftp-server").is_file(), "sftp-server missing")
    private_host_keys = sorted(Path("/etc/ssh").glob("ssh_host_*_key"))
    if not expect_runtime_authorized_keys:
        require(not private_host_keys, "baked SSH host private key detected")
    authorized_keys = Path("/root/.ssh/authorized_keys")
    if expect_runtime_authorized_keys:
        require(authorized_keys.is_file() and not authorized_keys.is_symlink(), "runtime authorized_keys missing")
        require(authorized_keys.stat().st_size > 0, "runtime authorized_keys empty")
        require(authorized_keys.stat().st_uid == 0, "runtime authorized_keys UID mismatch")
        require(authorized_keys.stat().st_mode & 0o777 == 0o600, "runtime authorized_keys mode mismatch")
    else:
        require(not authorized_keys.exists(), "baked authorized_keys detected")
    return {
        "packages": installed,
        "sshd_packaged": True,
        "sshd_started_by_image_smoke": False,
        "baked_host_private_key_count": 0,
        "runtime_host_private_key_count": (
            len(private_host_keys) if expect_runtime_authorized_keys else 0
        ),
        "baked_authorized_keys": False,
        "runtime_authorized_keys_expected": expect_runtime_authorized_keys,
        "runtime_authorized_keys_present": authorized_keys.exists(),
    }


def runtime_audit() -> dict[str, object]:
    require(platform.system() == "Linux", "Linux runtime required")
    require(platform.machine() == "x86_64", "linux/amd64 runtime required")
    require(os.geteuid() == 0 and os.getegid() == 0, "root transport identity required")
    account = pwd.getpwnam("engine-wave-f39")
    require(account.pw_uid == 9139 and account.pw_gid == 9139, "solver identity mismatch")
    require(Path("/workspace/inbox").stat().st_mode & 0o777 == 0o700, "inbox mode mismatch")
    for directory in (JOBS, RESULTS):
        require(directory.is_dir(), f"missing workspace directory: {directory}")
        require(directory.stat().st_uid == 0, f"workspace directory not root owned: {directory}")
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "transport_uid": os.geteuid(),
        "transport_gid": os.getegid(),
        "solver_uid": account.pw_uid,
        "solver_gid": account.pw_gid,
        "gpu_required": False,
        "external_api_required": False,
    }


def create_fixture_archive(path: Path) -> None:
    payload = b"f40-vast-image-smoke\n"
    with tarfile.open(path, mode="w") as archive:
        member = tarfile.TarInfo("payload.txt")
        member.size = len(payload)
        member.mode = 0o644
        member.mtime = 0
        member.uid = 0
        member.gid = 0
        archive.addfile(member, io.BytesIO(payload))


def privilege_drop_audit() -> dict[str, object]:
    archive = INBOX / f"{JOB_ID}.tar"
    job_dir = JOBS / JOB_ID
    result_dir = RESULTS / JOB_ID
    for path in (job_dir, result_dir):
        shutil.rmtree(path, ignore_errors=True)
    archive.unlink(missing_ok=True)
    create_fixture_archive(archive)
    try:
        staged = json.loads(
            command_stdout([str(ROOT / "stage_job.py"), str(archive), JOB_ID])
        )
        require(staged["target_uid"] == 9139, "staged job UID mismatch")
        require(staged["target_gid"] == 9139, "staged job GID mismatch")
        probe_code = (
            "import json, os, pathlib; "
            "p=pathlib.Path(os.environ['WAVE_RESULTS_DIR'])/'identity.json'; "
            "p.write_text(json.dumps({'uid':os.geteuid(),'gid':os.getegid(),"
            "'no_new_privs':open('/proc/self/status').read().split('NoNewPrivs:\\t')[1].splitlines()[0]}))"
        )
        command_stdout(
            [str(ROOT / "run_job.sh"), JOB_ID, sys.executable, "-c", probe_code]
        )
        identity = json.loads((result_dir / "identity.json").read_text(encoding="utf-8"))
        require(identity == {"uid": 9139, "gid": 9139, "no_new_privs": "1"}, "solver privilege drop failed")

        f39_output = command_stdout(
            [
                str(ROOT / "run_job.sh"),
                JOB_ID,
                "/usr/bin/env",
                "HOME=/tmp",
                sys.executable,
                str(F39_SMOKE),
            ]
        )
        f39 = json.loads(f39_output)
        require(f39["dependencies"]["aeolus1d"] == "0.3.3", "Aeolus1D mismatch")
        require(f39["runtime"]["uid"] == 9139, "F39 smoke did not run as solver")
        require(f39["benchmark"]["finite_positive_state_verified"] is True, "F39 smoke failed")
        return {
            "archive_validation_executed": True,
            "archive_special_members_allowed": False,
            "staged_target_uid": staged["target_uid"],
            "staged_target_gid": staged["target_gid"],
            "solver_effective_uid": identity["uid"],
            "solver_effective_gid": identity["gid"],
            "solver_no_new_privileges": identity["no_new_privs"] == "1",
            "solver_capability_bounding_set": "empty_by_launcher_contract",
            "aeolus1d": version("aeolus1d"),
            "generic_sod_benchmark_executed": True,
        }
    finally:
        archive.unlink(missing_ok=True)
        shutil.rmtree(job_dir, ignore_errors=True)
        shutil.rmtree(result_dir, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-runtime-authorized-keys", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = {
        "schema_version": "1.0.0",
        "phase": "F40-vast-image",
        "status": "offline_transport_smoke_passed_vast_and_engine_validation_blocked",
        "runtime": runtime_audit(),
        "ssh_transport": package_audit(args.expect_runtime_authorized_keys),
        "solver_isolation": privilege_drop_audit(),
        "claim_scope": {
            "vast_entrypoint_injection_executed": False,
            "vast_authorized_key_injection_verified": False,
            "vast_ssh_direct_handshake_verified": False,
            "f40_campaign_executed": False,
            "engine_model_physically_correlated": False,
            "target_1600_mechanical_hp_proven": False,
            "engine_start_authorized": False,
            "manufacturing_authorized": False,
        },
    }
    json.dump(report, sys.stdout, indent=2, sort_keys=True, allow_nan=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
