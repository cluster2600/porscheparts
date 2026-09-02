#!/usr/bin/env python3
"""Smoke hors ligne du transport Vast et du vrai round-trip CAO/STEP."""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import io
import json
import math
import os
from pathlib import Path
import platform
import pwd
import shutil
import subprocess
import sys
import tarfile


ROOT = Path("/opt/917-component-factory-f41-vast")
SSHD_WRAPPER = Path("/usr/sbin/sshd")
SSHD_REAL = Path("/usr/lib/openssh/sshd.real")
SSHD_WRAPPER_TARGET = ROOT / "sshd_runtime_wrapper.sh"
RUNTIME_HOST_KEY_MARKER = Path("/run/sshd/f41-runtime-host-keys.ready")
NO_AUTO_TMUX_MARKER = Path("/root/.no_auto_tmux")
INBOX = Path("/workspace/inbox")
JOBS = Path("/workspace/jobs")
RESULTS = Path("/workspace/results")
JOB_ID = "image-smoke"
BUNDLE_ROOT = "917-component-factory-f41"
PROBE_RELATIVE = "twins/reference-917-engine/source/execute_component_factory_f41.py"
PROBE_PATH = f"{BUNDLE_ROOT}/{PROBE_RELATIVE}"
F28_RUNTIME_IMAGE = (
    "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:"
    "18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57"
)
USD_RUNTIME_IMAGE = (
    "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:"
    "41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe"
)
EXPECTED_PACKAGES = {
    "openssh-client": "1:9.2p1-2+deb12u10",
    "openssh-server": "1:9.2p1-2+deb12u10",
    "openssh-sftp-server": "1:9.2p1-2+deb12u10",
}
CAD_PROBE = r'''from __future__ import annotations

import json
import math
import os
from pathlib import Path

import OCP
import build123d
from build123d import Align, Box, Cylinder, Pos, export_step, import_step


def bounds(shape):
    box = shape.bounding_box()
    return [round(float(box.size.X), 9), round(float(box.size.Y), 9), round(float(box.size.Z), 9)]


results = Path(os.environ["CAD_RESULTS_DIR"])
step_path = results / "synthetic-fixture.step"
body = Box(20.0, 12.0, 8.0, align=(Align.MIN, Align.MIN, Align.MIN))
cutter = Pos(10.0, 6.0, -2.0) * Cylinder(
    2.0, 12.0, align=(Align.CENTER, Align.CENTER, Align.MIN)
)
source = body - cutter
export_step(source, step_path)
reopened = import_step(step_path)
expected_volume = 20.0 * 12.0 * 8.0 - math.pi * 2.0**2 * 8.0
status_rows = {
    key: value.strip()
    for key, value in (
        line.split(":", 1)
        for line in Path("/proc/self/status").read_text(encoding="ascii").splitlines()
        if ":" in line
    )
}
solids = list(reopened.solids())
report = {
    "status": "passed_synthetic_build123d_step_roundtrip_via_cad_launcher",
    "uid": os.geteuid(),
    "gid": os.getegid(),
    "no_new_privileges": status_rows["NoNewPrivs"] == "1",
    "capability_bounding_set_empty": int(status_rows["CapBnd"], 16) == 0,
    "build123d": build123d.__version__,
    "ocp": OCP.__version__,
    "source_valid": bool(source.is_valid and source.is_manifold),
    "reopened_valid": bool(reopened.is_valid and reopened.is_manifold),
    "reopened_solid_count": len(solids),
    "reopened_closed": len(solids) == 1 and len(solids[0].shells()) == 1,
    "expected_volume_mm3": round(expected_volume, 9),
    "reopened_volume_mm3": round(sum(solid.volume for solid in solids), 9),
    "bounds_size_mm": bounds(reopened),
    "step_bytes": step_path.stat().st_size,
    "step_sha256": "sha256:" + __import__("hashlib").sha256(step_path.read_bytes()).hexdigest(),
    "vehicle_geometry_used": False,
    "manufacturing_authorized": False,
}
if not (
    report["uid"] == 9178
    and report["gid"] == 9178
    and report["no_new_privileges"]
    and report["capability_bounding_set_empty"]
    and report["build123d"] == "0.11.1"
    and report["ocp"] == "7.9.3.1"
    and report["source_valid"]
    and report["reopened_valid"]
    and report["reopened_closed"]
    and math.isclose(report["reopened_volume_mm3"], expected_volume, rel_tol=0.0, abs_tol=1e-6)
    and report["bounds_size_mm"] == [20.0, 12.0, 8.0]
    and report["step_bytes"] > 1000
):
    raise SystemExit("synthetic CAD/STEP smoke rejected")
(results / "cad-probe.json").write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
'''


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


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def package_audit(expect_runtime_authorized_keys: bool) -> dict[str, object]:
    installed = {
        package: command_stdout(["dpkg-query", "-W", "-f=${Version}", package]).strip()
        for package in EXPECTED_PACKAGES
    }
    require(installed == EXPECTED_PACKAGES, "OpenSSH package lock mismatch")
    require(SSHD_WRAPPER.is_symlink(), "sshd runtime wrapper symlink missing")
    require(
        SSHD_WRAPPER.resolve() == SSHD_WRAPPER_TARGET,
        "sshd runtime wrapper target mismatch",
    )
    require(os.access(SSHD_WRAPPER, os.X_OK), "sshd runtime wrapper is not executable")
    require(SSHD_REAL.is_file(), "real sshd binary missing")
    require(not SSHD_REAL.is_symlink(), "real sshd binary must not be a symlink")
    require(os.access(SSHD_REAL, os.X_OK), "real sshd binary is not executable")
    require(Path("/usr/lib/openssh/sftp-server").is_file(), "sftp-server missing")
    require(
        NO_AUTO_TMUX_MARKER.is_file() and not NO_AUTO_TMUX_MARKER.is_symlink(),
        "Vast no-auto-tmux marker missing",
    )
    require(
        NO_AUTO_TMUX_MARKER.stat().st_uid == 0
        and NO_AUTO_TMUX_MARKER.stat().st_gid == 0
        and NO_AUTO_TMUX_MARKER.stat().st_mode & 0o777 == 0o600,
        "Vast no-auto-tmux marker metadata mismatch",
    )
    private_host_keys = sorted(Path("/etc/ssh").glob("ssh_host_*_key"))
    if expect_runtime_authorized_keys:
        require(private_host_keys, "runtime SSH host private keys missing")
        require(
            RUNTIME_HOST_KEY_MARKER.is_file()
            and not RUNTIME_HOST_KEY_MARKER.is_symlink(),
            "runtime SSH host-key marker missing",
        )
        require(
            RUNTIME_HOST_KEY_MARKER.stat().st_uid == 0
            and RUNTIME_HOST_KEY_MARKER.stat().st_gid == 0
            and RUNTIME_HOST_KEY_MARKER.stat().st_mode & 0o777 == 0o600,
            "runtime SSH host-key marker metadata mismatch",
        )
        for private_host_key in private_host_keys:
            require(
                private_host_key.is_file() and not private_host_key.is_symlink(),
                "runtime SSH host private key must be a regular file",
            )
            require(
                private_host_key.stat().st_uid == 0
                and private_host_key.stat().st_gid == 0
                and private_host_key.stat().st_mode & 0o777 == 0o600,
                "runtime SSH host private key metadata mismatch",
            )
    else:
        require(not private_host_keys, "baked SSH host private key detected")
        require(
            not RUNTIME_HOST_KEY_MARKER.exists(),
            "runtime SSH host-key marker present in image",
        )
    authorized_keys = Path("/root/.ssh/authorized_keys")
    if expect_runtime_authorized_keys:
        require(
            authorized_keys.is_file() and not authorized_keys.is_symlink(),
            "runtime authorized_keys missing",
        )
        require(authorized_keys.stat().st_size > 0, "runtime authorized_keys empty")
        require(authorized_keys.stat().st_uid == 0, "runtime authorized_keys UID mismatch")
        require(
            authorized_keys.stat().st_mode & 0o777 == 0o600,
            "runtime authorized_keys mode mismatch",
        )
    else:
        require(not authorized_keys.exists(), "baked authorized_keys detected")
    return {
        "packages": installed,
        "sshd_packaged": True,
        "sshd_started": False,
        "sshd_runtime_wrapper_installed": True,
        "real_sshd_binary_separated": True,
        "noninteractive_ssh_auto_tmux_disabled": True,
        "baked_host_private_key_count": 0,
        "runtime_host_private_key_count": len(private_host_keys),
        "runtime_host_keys_expected": expect_runtime_authorized_keys,
        "runtime_host_keys_generated_by_wrapper": (
            expect_runtime_authorized_keys and RUNTIME_HOST_KEY_MARKER.exists()
        ),
        "baked_authorized_keys": False,
        "runtime_authorized_keys_expected": expect_runtime_authorized_keys,
        "runtime_authorized_keys_present": authorized_keys.exists(),
    }


def runtime_audit() -> dict[str, object]:
    require(platform.system() == "Linux", "Linux runtime required")
    require(platform.machine() == "x86_64", "linux/amd64 runtime required")
    require(os.geteuid() == 0 and os.getegid() == 0, "root transport identity required")
    account = pwd.getpwnam("cad-author")
    require(account.pw_uid == 9178 and account.pw_gid == 9178, "CAD identity mismatch")
    require(account.pw_shell == "/usr/sbin/nologin", "CAD login shell must remain disabled")
    require(Path("/usr/bin/setpriv").is_file(), "setpriv missing")
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
        "cad_uid": account.pw_uid,
        "cad_gid": account.pw_gid,
        "cad_login_shell": account.pw_shell,
        "gpu_required": False,
        "external_api_required": False,
    }


def add_tar_member(archive: tarfile.TarFile, name: str, payload: bytes, mode: int) -> None:
    member = tarfile.TarInfo(name)
    member.size = len(payload)
    member.mode = mode
    member.mtime = 0
    member.uid = 0
    member.gid = 0
    archive.addfile(member, io.BytesIO(payload))


def create_fixture_archive(path: Path) -> None:
    probe = CAD_PROBE.encode("utf-8")
    manifest = {
        "all_payload_files_utf8_text": True,
        "archive_member_count": 2,
        "binary_payload_included": False,
        "bundle_root": BUNDLE_ROOT,
        "file_count": 1,
        "files": [
            {
                "mode": "0755",
                "path": PROBE_RELATIVE,
                "sha256": sha256(probe),
                "size_bytes": len(probe),
            }
        ],
        "newly_generated_geometry_included": False,
        "phase": "F41",
        "private_absolute_path_included": False,
        "public_remote_refs": ["refs/remotes/origin/synthetic-smoke"],
        "raw_scan_included": False,
        "required_runtime_images": [F28_RUNTIME_IMAGE, USD_RUNTIME_IMAGE],
        "schema_version": "1.1.0",
        "secret_included": False,
        "source_repository_state": "clean_commit_visible_at_exact_remote_ref",
        "source_revision": "0" * 40,
        "status": "public_transfer_bundle_file_manifest",
    }
    manifest_payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with tarfile.open(path, mode="w") as archive:
        add_tar_member(
            archive, f"{BUNDLE_ROOT}/BUNDLE-MANIFEST.json", manifest_payload, 0o644
        )
        add_tar_member(archive, PROBE_PATH, probe, 0o755)


def cad_launcher_audit() -> dict[str, object]:
    archive = INBOX / f"{JOB_ID}.tar"
    job_dir = JOBS / JOB_ID
    result_dir = RESULTS / JOB_ID
    for path in (job_dir, result_dir):
        shutil.rmtree(path, ignore_errors=True)
    archive.unlink(missing_ok=True)
    create_fixture_archive(archive)
    try:
        staged = json.loads(command_stdout([str(ROOT / "stage_job.py"), str(archive), JOB_ID]))
        require(staged["target_uid"] == 9178, "staged job UID mismatch")
        require(staged["target_gid"] == 9178, "staged job GID mismatch")
        require(staged["private_assets_included"] is False, "private asset gate opened")
        require(staged["secret_material_included"] is False, "secret gate opened")
        require(staged["regular_payloads_utf8_text_only"] is True, "text-only gate failed")
        command_stdout([str(ROOT / "run_job.sh"), JOB_ID, sys.executable, PROBE_PATH])
        probe = json.loads((result_dir / "cad-probe.json").read_text(encoding="utf-8"))
        require(probe["status"] == "passed_synthetic_build123d_step_roundtrip_via_cad_launcher", "CAD probe rejected")
        require(probe["uid"] == 9178 and probe["gid"] == 9178, "CAD privilege drop failed")
        require(probe["no_new_privileges"] is True, "NoNewPrivs gate failed")
        require(probe["capability_bounding_set_empty"] is True, "capability gate failed")
        require(probe["reopened_closed"] is True, "STEP round-trip did not preserve a closed solid")
        return {
            "public_archive_validation_executed": True,
            "f41_bundle_manifest_hashes_verified": True,
            "archive_special_members_allowed": False,
            "private_geometry_input_allowed": False,
            "transferred_payloads_utf8_text_only": True,
            "synthetic_source_provenance_live_verified": False,
            "staged_target_uid": staged["target_uid"],
            "staged_target_gid": staged["target_gid"],
            "cad_effective_uid": probe["uid"],
            "cad_effective_gid": probe["gid"],
            "cad_no_new_privileges": probe["no_new_privileges"],
            "cad_capability_bounding_set_empty": probe["capability_bounding_set_empty"],
            "build123d": version("build123d"),
            "cadquery_ocp_novtk": version("cadquery-ocp-novtk"),
            "lib3mf": version("lib3mf"),
            "ocp": probe["ocp"],
            "synthetic_step_roundtrip_executed": True,
            "synthetic_step_bytes": probe["step_bytes"],
            "synthetic_closed_solid_after_roundtrip": probe["reopened_closed"],
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
        "phase": "F41-vast-cad-image",
        "status": "offline_transport_and_cad_step_smoke_passed_vast_f41_and_manufacturing_validation_blocked",
        "runtime": runtime_audit(),
        "ssh_transport": package_audit(args.expect_runtime_authorized_keys),
        "cad_isolation": cad_launcher_audit(),
        "claim_scope": {
            "vast_entrypoint_injection_executed": False,
            "vast_authorized_key_injection_verified": False,
            "vast_ssh_direct_handshake_verified": False,
            "f41_component_factory_executed": False,
            "f41_geometry_dimensionally_validated": False,
            "engine_model_physically_correlated": False,
            "omniverse_simready_validated": False,
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
