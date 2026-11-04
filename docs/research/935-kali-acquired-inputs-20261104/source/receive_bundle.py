#!/usr/bin/env python3
"""Receive an exact private input archive over native SSH; never replace a directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tempfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--archive-sha256", required=True)
    p.add_argument("--archive-bytes", type=int, required=True)
    p.add_argument("--contract-sha256", required=True)
    a = p.parse_args()
    if a.root.exists(): raise ValueError("Existing acquired-input directory refused")
    os.umask(0o077)
    a.root.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd, incoming = tempfile.mkstemp(prefix="935-acquired-incoming-", suffix=".tar", dir=a.root.parent)
    digest, size = hashlib.sha256(), 0
    with os.fdopen(fd, "wb") as stream:
        while block := sys.stdin.buffer.read(8*1024*1024):
            size += len(block)
            if size > a.archive_bytes: raise ValueError("Archive exceeds registered size")
            digest.update(block); stream.write(block)
    if size != a.archive_bytes or digest.hexdigest() != a.archive_sha256:
        raise ValueError("Incoming acquired archive checksum failed")
    with tarfile.open(incoming, "r:") as archive:
        members = archive.getmembers()
        if any(not m.isfile() or PurePosixPath(m.name).is_absolute() or ".." in PurePosixPath(m.name).parts for m in members):
            raise ValueError("Nonregular or escaping archive member refused")
        contract_bytes = archive.extractfile("input-contract.json").read()
        if hashlib.sha256(contract_bytes).hexdigest() != a.contract_sha256:
            raise ValueError("Incoming input contract changed")
        contract = json.loads(contract_bytes)
        allowed = {"input-contract.json", *(e["path"] for e in contract["files"])}
        if len(members) != len(allowed) or {m.name for m in members} != allowed:
            raise ValueError("Acquired archive does not match its exact file allowlist")
        a.root.mkdir(mode=0o700)
        archive.extractall(a.root, filter="data")
    print(json.dumps({"received_archive_sha256": digest.hexdigest(), "received_bytes": size,
                      "input_contract_sha256": a.contract_sha256, "regular_payload_files": len(members),
                      "private_directory_mode": oct(a.root.stat().st_mode & 0o777),
                      "existing_data_replaced": False, "incoming_archive": incoming}))


if __name__ == "__main__":
    main()
