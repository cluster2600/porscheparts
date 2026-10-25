"""Private DVC artifact transfer with independent SHA-256 restore verification."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import shlex
import sys
import tempfile

from ft_common import (
    checked,
    load,
    new_directory,
    receipt,
    source_path,
    verify_inputs,
    write,
)


def private_root(path):
    path = Path(path).resolve()
    if any((parent / ".git").exists() for parent in [path, *path.parents]):
        raise ValueError("DVC workspace must be outside every Git checkout")
    return path


def dvc(args, workspace, timeout=120):
    env = dict(os.environ, DVC_NO_ANALYTICS="true", DO_NOT_TRACK="1")
    return checked([sys.executable, "-m", "dvc", *args], workspace, timeout, env)


def init(workspace):
    workspace = new_directory(private_root(workspace))
    dvc(["init", "--no-scm", "--quiet"], workspace)
    dvc(["config", "core.analytics", "false"], workspace)
    dvc(["config", "cache.dir", str(workspace / ".dvc/cache")], workspace)
    dvc(["config", "cache.type", "copy"], workspace)
    return workspace


def store_location(value, workspace):
    if str(value).startswith("ssh://"):
        raise ValueError(
            "SSH stores use the strict OpenSSH transfer adapter, never DVC's SSH backend"
        )
    path = private_root(value)
    if path.is_relative_to(workspace) or workspace.is_relative_to(path):
        raise ValueError("store and disposable workspace must be disjoint")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return str(path)


def ssh_transfer(value, local, receive, workspace):
    """Keep DVC local: the installed sshfs backend disables known-host checking."""
    from urllib.parse import urlsplit
    import re

    parsed = urlsplit(str(value))
    if (
        parsed.scheme != "ssh"
        or not parsed.hostname
        or not parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("explicit password-free SSH store required")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", parsed.username) or not re.fullmatch(
        r"[A-Za-z0-9_.-]+", parsed.hostname
    ):
        raise ValueError("explicit simple SSH identity required")
    if (
        not re.fullmatch(r"/[A-Za-z0-9_./-]+", parsed.path)
        or ".." in Path(parsed.path).parts
        or parsed.path in ("/", "/home")
    ):
        raise ValueError("dedicated absolute private store path required")
    ssh = [
        "ssh",
        "-p",
        str(parsed.port or 22),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ForwardAgent=no",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "ConnectTimeout=10",
    ]
    destination = parsed.username + "@" + parsed.hostname
    code = (
        "import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
        "assert p.is_absolute() and p.resolve()==p, 'canonical store path required'; "
        + (
            "assert p.is_dir(), 'remote store missing'"
            if receive
            else "p.mkdir(parents=True,exist_ok=True,mode=0o700); assert p.is_dir()"
        )
    )
    checked(
        ssh + [destination, shlex.join(["python3", "-c", code, parsed.path])],
        workspace,
        20,
    )
    remote = destination + ":" + parsed.path.rstrip("/") + "/"
    source, target = (
        (remote, str(local) + "/") if receive else (str(local) + "/", remote)
    )
    checked(
        [
            "rsync",
            "-r",
            "--no-links",
            "--no-devices",
            "--no-specials",
            "--protect-args",
            "--chmod=Du=rwx,Dgo=,Fu=rw,Fgo=",
            "-e",
            shlex.join(ssh),
            "--",
            source,
            target,
        ],
        workspace,
        120,
    )


def archive(manifest_path, root, workspace, store):
    manifest = load(manifest_path)
    verify_inputs(manifest, root)
    workspace = init(workspace)
    target = workspace / "payload"
    target.mkdir(mode=0o700)
    for item in manifest["inputs"]:
        destination = target / item["path"]
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copyfile(source_path(root, item["path"]), destination)
        destination.chmod(0o600)
    verify_inputs(manifest, target)
    write(workspace / "manifest.json", manifest)
    dvc(["add", "payload", "--quiet"], workspace)
    dvc(["remote", "add", "-d", "primary", store_location(store, workspace)], workspace)
    dvc(["push", "--quiet"], workspace)
    verify_inputs(manifest, root)
    report = receipt(
        "dvc", "archived", manifest["inputs"], checks={"SHA256_verified": True}
    )
    write(workspace / "archive-receipt.json", report)
    return report


def restore(metadata, workspace, store):
    metadata = Path(metadata).resolve(strict=True)
    manifest = load(source_path(metadata, "manifest.json"))
    workspace = init(workspace)
    if str(store).startswith("ssh://"):
        incoming = Path(
            tempfile.mkdtemp(prefix="incoming-store-", dir=workspace.parent)
        )
        ssh_transfer(store, incoming, True, workspace)
        store = incoming
    shutil.copyfile(source_path(metadata, "payload.dvc"), workspace / "payload.dvc")
    write(workspace / "manifest.json", manifest)
    dvc(["remote", "add", "-d", "source", store_location(store, workspace)], workspace)
    dvc(["pull", "--quiet"], workspace)
    verify_inputs(manifest, workspace / "payload")
    report = receipt(
        "dvc",
        "restored_sha256_verified",
        manifest["inputs"],
        checks={"fresh_workspace": True, "SHA256_verified": True},
    )
    write(workspace / "restore-receipt.json", report)
    return report


def replicate(metadata, store):
    workspace = private_root(metadata)
    manifest = load(workspace / "manifest.json")
    verify_inputs(manifest, workspace / "payload")
    remote = str(store).startswith("ssh://")
    local_store = (
        Path(tempfile.mkdtemp(prefix="export-store-", dir=workspace.parent))
        if remote
        else store
    )
    dvc(["remote", "add", "replica", store_location(local_store, workspace)], workspace)
    dvc(["push", "-r", "replica", "--quiet"], workspace)
    if remote:
        ssh_transfer(store, local_store, False, workspace)
    # A push is not recovery proof. A separate fresh restore is mandatory.
    return {"status": "replicated_restore_required", "restoration_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["archive", "restore", "replicate"])
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--store", required=True)
    args = parser.parse_args()
    if args.command == "archive":
        if not all([args.manifest, args.root, args.workspace]):
            parser.error("archive requires manifest, root and workspace")
        result = archive(args.manifest, args.root, args.workspace, args.store)
    elif args.command == "restore":
        if not args.metadata or not args.workspace:
            parser.error("restore requires metadata and workspace")
        result = restore(args.metadata, args.workspace, args.store)
    else:
        if not args.metadata:
            parser.error("replicate requires metadata")
        result = replicate(args.metadata, args.store)
    print(result["status"])


if __name__ == "__main__":
    main()
