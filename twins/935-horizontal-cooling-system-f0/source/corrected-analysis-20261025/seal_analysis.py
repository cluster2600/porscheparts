"""Seal and verify the private corrected-rotor analysis and fluid-case inputs."""

import argparse
import hashlib
import json
from pathlib import Path
import tarfile


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    bound = json.loads((args.phase / "mac-checker-001/assessment.json").read_text())
    case = json.loads((args.phase / "fluid-case-001/receipt.json").read_text())
    if not bound["complete_containment_pass"] or case["candidate_off_sha256"] != bound["candidate_off_sha256"]:
        raise ValueError("The fluid case is not bound to the accepted analysis surface")
    files = sorted(path for path in args.phase.rglob("*") if path.is_file())
    if any(path.is_symlink() for path in args.phase.rglob("*")):
        raise ValueError("Symlinks are not valid science payloads")
    rows = [
        {"name": str(path.relative_to(args.phase)), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
    ]
    if sum(row["bytes"] for row in rows) > 2 * 1024**3:
        raise ValueError("Archive exceeds the bounded study size")
    args.output.mkdir(parents=True, exist_ok=False)
    archive = args.output / "corrected-analysis-001.tar.gz"
    manifest = args.output / "corrected-analysis-manifest-001.json"
    receipt = args.output / "corrected-analysis-receipt-001.json"
    manifest.write_text(json.dumps({"entries": rows, "CFD_accepted": False,
                                    "manufacturing_authorized": False}, indent=2) + "\n")
    with tarfile.open(archive, "x:gz", compresslevel=1) as stream:
        for path, row in zip(files, rows):
            stream.add(path, arcname="corrected-analysis/" + row["name"], recursive=False)
        stream.add(manifest, arcname=manifest.name, recursive=False)
    with tarfile.open(archive, "r:gz") as stream:
        if len(stream.getmembers()) != len(rows) + 1:
            raise ValueError("Archive member count changed")
        for path, row in zip(files, rows):
            member = stream.getmember("corrected-analysis/" + row["name"])
            if member.size != row["bytes"] or hashlib.file_digest(stream.extractfile(member), "sha256").hexdigest() != row["sha256"] or sha256(path) != row["sha256"]:
                raise ValueError("Archive member or source changed")
        if stream.extractfile(manifest.name).read() != manifest.read_bytes():
            raise ValueError("Archive manifest changed")
    result = {"schema": "935-corrected-analysis-archive-v1",
              "source_sha256": sha256(__file__), "archive_sha256": sha256(archive),
              "archive_bytes": archive.stat().st_size, "manifest_sha256": sha256(manifest),
              "files_verified": len(rows), "all_members_verified": True,
              "new_paid_instance_created": False, "CFD_accepted": False,
              "manufacturing_authorized": False}
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
