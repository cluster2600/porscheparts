#!/usr/bin/env python3
"""Build a deterministic, public-only F41 job bundle for remote execution."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "work/917-component-factory-f41-bundle"
BUNDLE_ROOT = "917-component-factory-f41"
PUBLIC_REMOTE_REF_RE = re.compile(
    r"refs/remotes/[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._/-]{0,254}"
)
FORBIDDEN_PATH_PARTS = {"raw-scans", ".ssh", "Downloads", ".git", "work"}
FORBIDDEN_CONTENT = (
    b"/Users/",
    b"BEGIN OPENSSH PRIVATE KEY",
    b"BEGIN PRIVATE KEY",
    b"VAST_API_KEY=",
    b"NVIDIA_API_KEY=",
    b"OPENBAO_TOKEN=",
)

ALLOWLIST = (
    "docs/917_COMPONENT_FACTORY_F41.md",
    "twins/reference-917-engine/component-factory-f41.json",
    "twins/reference-917-engine/rotating-assembly-cad-f35.json",
    "twins/reference-917-engine/source/execute_component_factory_f41.py",
    "twins/reference-917-engine/source/run_component_factory_f41_cad_job.sh",
    "twins/reference-917-engine/source/run_component_factory_f41_usd_job.sh",
    "twins/reference-917-engine/source/build_rotating_assembly_cad_f35.py",
    "twins/reference-917-engine/source/rotating_assembly_f35_math.py",
    "containers/simready-preflight/convert.py",
)


class BundleError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BundleError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_git(project_root: Path, *arguments: str, allow_failure: bool = False) -> subprocess.CompletedProcess[bytes]:
    environment = {
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", ""),
    }
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_root), *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=environment,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise BundleError(f"git_command_timeout:{arguments[0]}") from exc
    if not allow_failure:
        require(completed.returncode == 0, f"git_command_failed:{arguments[0]}:{completed.returncode}")
    return completed


def verified_source_revision(project_root: Path) -> tuple[str, list[str]]:
    status = run_git(project_root, "status", "--porcelain=v1", "--untracked-files=all").stdout
    require(status == b"", "git_worktree_must_be_clean_including_untracked_files")
    revision = run_git(project_root, "rev-parse", "--verify", "HEAD").stdout.decode("ascii").strip()
    require(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision) is not None, "invalid_git_HEAD_revision")

    remote_names = [
        line for line in run_git(project_root, "remote").stdout.decode("utf-8").splitlines() if line
    ]
    require(remote_names, "git_remote_required")
    tracking_refs = [
        line
        for line in run_git(
            project_root,
            "for-each-ref",
            "--format=%(refname)",
            "--points-at",
            revision,
            "refs/remotes",
        ).stdout.decode("utf-8").splitlines()
        if line and not line.endswith("/HEAD")
    ]
    verified: list[str] = []
    for tracking_ref in sorted(tracking_refs):
        if PUBLIC_REMOTE_REF_RE.fullmatch(tracking_ref) is None or ".." in tracking_ref or "//" in tracking_ref:
            continue
        match = next(
            (
                (remote, tracking_ref.removeprefix(f"refs/remotes/{remote}/"))
                for remote in sorted(remote_names, key=len, reverse=True)
                if tracking_ref.startswith(f"refs/remotes/{remote}/")
            ),
            None,
        )
        if match is None:
            continue
        remote, branch = match
        remote_result = run_git(
            project_root,
            "ls-remote",
            "--exit-code",
            "--refs",
            remote,
            f"refs/heads/{branch}",
            allow_failure=True,
        )
        if remote_result.returncode != 0:
            continue
        remote_lines = remote_result.stdout.decode("ascii", errors="strict").splitlines()
        if any(line.split("\t", 1)[0] == revision for line in remote_lines if "\t" in line):
            verified.append(tracking_ref)
    require(verified, "HEAD_must_be_visible_at_exact_remote_branch_revision")
    require(len(verified) <= 32, "too_many_public_remote_refs")
    return revision, verified


def committed_file(project_root: Path, revision: str, relative_path: str) -> tuple[bytes, str]:
    tree = run_git(project_root, "ls-tree", revision, "--", relative_path).stdout.decode("utf-8").strip()
    require(tree != "", f"bundle_source_not_committed:{relative_path}")
    fields = tree.split(None, 3)
    require(len(fields) == 4 and fields[1] == "blob", f"bundle_source_must_be_regular_blob:{relative_path}")
    mode = fields[0]
    require(mode in {"100644", "100755"}, f"bundle_source_mode_forbidden:{relative_path}:{mode}")
    payload = run_git(project_root, "show", f"{revision}:{relative_path}").stdout
    return payload, mode


def validate_source(relative_path: str, payload: bytes) -> bytes:
    parts = set(Path(relative_path).parts)
    require(not parts.intersection(FORBIDDEN_PATH_PARTS), f"forbidden_bundle_path:{relative_path}")
    require(not Path(relative_path).is_absolute() and ".." not in Path(relative_path).parts, f"unsafe_bundle_path:{relative_path}")
    require(b"\x00" not in payload, f"binary_bundle_payload_forbidden:{relative_path}")
    try:
        payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BundleError(f"non_UTF8_bundle_payload_forbidden:{relative_path}") from exc
    for token in FORBIDDEN_CONTENT:
        require(token not in payload, f"forbidden_bundle_content:{relative_path}:{token.decode(errors='replace')}")
    return payload


def tar_info(name: str, size: int, executable: bool) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name=f"{BUNDLE_ROOT}/{name}")
    info.size = size
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mode = 0o755 if executable else 0o644
    return info


def build_bundle(project_root: Path, output_root: Path) -> dict[str, Any]:
    source_revision, public_remote_refs = verified_source_revision(project_root)
    output_root.mkdir(parents=True, exist_ok=True)
    archive_path = output_root / "917-component-factory-f41-public.tar.gz"
    manifest_path = output_root / "bundle-manifest.json"
    require(not archive_path.exists(), f"archive_exists_refusing_overwrite:{archive_path}")
    require(not manifest_path.exists(), f"manifest_exists_refusing_overwrite:{manifest_path}")

    entries: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}
    payload_modes: dict[str, str] = {}
    for relative_path in sorted(ALLOWLIST):
        committed_payload, git_mode = committed_file(project_root, source_revision, relative_path)
        payload = validate_source(relative_path, committed_payload)
        payloads[relative_path] = payload
        executable = git_mode == "100755"
        payload_modes[relative_path] = "0755" if executable else "0644"
        entries.append({
            "path": relative_path,
            "sha256": sha256_bytes(payload),
            "size_bytes": len(payload),
            "mode": payload_modes[relative_path],
        })

    readme = (
        "# F41 remote job bundle\n\n"
        "Ce bundle public textuel ne contient aucun scan brut, géométrie ni secret.\n"
        "Il matérialise uniquement six familles F35 liées par SHA-256.\n\n"
        "Phase CAD (image cad-author-f28 liée par digest):\n\n"
        "```bash\n"
        "export F41_RUNTIME_IMAGE_REF='ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57'\n"
        "bash twins/reference-917-engine/source/run_component_factory_f41_cad_job.sh /workspace/output\n"
        "```\n\n"
        "Transférer ensuite le même dossier output vers la phase USD.\n\n"
        "Phase USD (image simready-workflow liée par digest):\n\n"
        "```bash\n"
        "export F41_RUNTIME_IMAGE_REF='ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe'\n"
        "bash twins/reference-917-engine/source/run_component_factory_f41_usd_job.sh /workspace/output\n"
        "python twins/reference-917-engine/source/execute_component_factory_f41.py finalize --project-root . --output /workspace/output\n"
        "```\n"
    ).encode("utf-8")
    payloads["REMOTE_JOB.md"] = readme
    payload_modes["REMOTE_JOB.md"] = "0644"
    entries.append({
        "path": "REMOTE_JOB.md",
        "sha256": sha256_bytes(readme),
        "size_bytes": len(readme),
        "mode": "0644",
    })
    entries.sort(key=lambda item: item["path"])

    embedded_manifest = {
        "schema_version": "1.1.0",
        "phase": "F41",
        "status": "public_transfer_bundle_file_manifest",
        "bundle_root": BUNDLE_ROOT,
        "source_revision": source_revision,
        "public_remote_refs": public_remote_refs,
        "source_repository_state": "clean_commit_visible_at_exact_remote_ref",
        "file_count": len(entries),
        "archive_member_count": len(entries) + 1,
        "files": entries,
        "all_payload_files_utf8_text": True,
        "binary_payload_included": False,
        "raw_scan_included": False,
        "private_absolute_path_included": False,
        "secret_included": False,
        "newly_generated_geometry_included": False,
        "required_runtime_images": [
            "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57",
            "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe",
        ],
    }
    embedded_bytes = (json.dumps(embedded_manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    payloads["BUNDLE-MANIFEST.json"] = embedded_bytes
    payload_modes["BUNDLE-MANIFEST.json"] = "0644"

    with tempfile.NamedTemporaryFile(dir=output_root, suffix=".tar", delete=False) as stream:
        temporary_tar = Path(stream.name)
    try:
        with tarfile.open(temporary_tar, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for relative_path in sorted(payloads):
                payload = payloads[relative_path]
                executable = payload_modes[relative_path] == "0755"
                archive.addfile(tar_info(relative_path, len(payload), executable), io.BytesIO(payload))
        with temporary_tar.open("rb") as source, archive_path.open("wb") as destination:
            with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0, compresslevel=9) as compressor:
                shutil_copyfileobj(source, compressor)
    finally:
        temporary_tar.unlink(missing_ok=True)

    report = {
        "schema_version": "1.1.0",
        "phase": "F41",
        "status": "passed_public_transfer_bundle_built",
        "archive": {
            "path": archive_path.name,
            "sha256": sha256(archive_path),
            "size_bytes": archive_path.stat().st_size,
        },
        "bundle_root": BUNDLE_ROOT,
        "source_revision": source_revision,
        "public_remote_refs": public_remote_refs,
        "source_repository_state": "clean_commit_visible_at_exact_remote_ref",
        "file_count": len(entries),
        "archive_member_count": len(payloads),
        "source_files": entries,
        "all_payload_files_utf8_text": True,
        "binary_payload_included": False,
        "raw_scan_included": False,
        "private_absolute_path_included": False,
        "secret_included": False,
        "newly_generated_geometry_included": False,
        "paid_instance_launched": False,
    }
    write_json(manifest_path, report)
    return report


def shutil_copyfileobj(source, destination, length: int = 1024 * 1024) -> None:
    while True:
        block = source.read(length)
        if not block:
            return
        destination.write(block)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_bundle(args.project_root.resolve(), args.output.resolve())
    except BundleError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
