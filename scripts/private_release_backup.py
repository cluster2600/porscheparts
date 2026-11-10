#!/usr/bin/env python3
"""Back up an ignored work folder to a private GitHub release, then prove the restore.

Private outputs (STEP files, meshes, solver fields) must stay out of Git
(AGENTS.md), and an ignored ``work/`` folder on one disk is not a backup. This
tool copies chosen sub-folders into a release of a **private** repository:

``backup``  Read-only on the source. Hashes every file, packs them into
            gzip tar parts of at most ``--batch-bytes`` (uncompressed) each,
            uploads one part at a time and deletes it locally, so the
            staging folder never holds more than one part. Files modified in
            the last ``--quiet-minutes`` are skipped and listed, because
            another process may still be writing them. ``manifest.json`` is
            uploaded last.
``verify``  Downloads the manifest and every part, one at a time, and rehashes
            each file by streaming the archive (nothing is extracted to disk).
            Exit status 0 only if every manifest file comes back identical.

A push alone is not a verified backup: run ``verify`` and keep its report.
The release must already exist (``gh release create TAG -R OWNER/REPO``), and
the script refuses a public repository.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_BATCH_BYTES = 1_800_000_000   # GitHub release assets are limited to 2 GiB


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(src, roots, exclude, quiet_seconds, now):
    """Files to back up, files skipped and symbolic links, as manifest rows (no hashing).

    Links are recorded with their target and never hashed or archived: hashing
    would follow the link and claim content that tar does not store.
    """
    files, skipped, links = [], [], []
    for root in roots:
        base = src / root
        if not base.is_dir():
            raise FileNotFoundError(base)
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(src).as_posix()
            if path.is_symlink():
                links.append({"path": rel, "target": str(path.readlink())})
                continue
            if not path.is_file():
                continue
            st = path.stat()
            if any(rel.startswith(prefix) for prefix in exclude):
                skipped.append({"path": rel, "size": st.st_size, "reason": "excluded by prefix"})
            elif now - st.st_mtime < quiet_seconds:
                skipped.append({"path": rel, "size": st.st_size, "reason": "modified during the quiet window"})
            else:
                files.append({"path": rel, "size": st.st_size, "mtime": int(st.st_mtime)})
    return files, skipped, links


def batches(files, limit):
    """Greedy, order-preserving packing of files into parts of at most limit bytes."""
    out, current, size = [], [], 0
    for f in sorted(files, key=lambda f: f["path"]):
        if f["size"] > limit:
            raise ValueError(f"{f['path']} is larger than one part ({f['size']} > {limit} bytes)")
        if current and size + f["size"] > limit:
            out.append(current)
            current, size = [], 0
        current.append(f)
        size += f["size"]
    if current:
        out.append(current)
    return out


def gh(*args, **kw):
    return subprocess.run(["gh", *args], check=True, text=True, **kw)


def require_private(repo):
    visibility = gh("repo", "view", repo, "--json", "visibility", "-q", ".visibility",
                    capture_output=True).stdout.strip()
    if visibility != "PRIVATE":
        raise SystemExit(f"{repo} is {visibility or 'unknown'}; private outputs go to a private repository only")


def backup(args):
    require_private(args.repo)
    src, stage = args.src.resolve(), args.stage
    stage.mkdir(parents=True, exist_ok=False)
    now = time.time()
    files, skipped, links = collect(src, args.roots, args.exclude, args.quiet_minutes * 60, now)
    for f in files:
        before = (src / f["path"]).stat()
        f["sha256"] = sha256_file(src / f["path"])
        after = (src / f["path"]).stat()
        if (before.st_size, before.st_mtime) != (after.st_size, after.st_mtime):
            raise RuntimeError("File changed while hashing: " + f["path"])
    groups = batches(files, args.batch_bytes)
    parts = []
    for i, group in enumerate(groups, 1):
        name = f"{args.prefix}-part{i:02d}of{len(groups):02d}.tar.gz"
        part, listing = stage / name, stage / f"part{i:02d}.list"
        listing.write_text("".join(f["path"] + "\n" for f in group))
        with open(part, "wb") as out:
            tar = subprocess.Popen(["tar", "-C", str(src), "-cf", "-", "-T", str(listing)], stdout=subprocess.PIPE)
            subprocess.run(["gzip", "-6"], stdin=tar.stdout, stdout=out, check=True)
            if tar.wait() != 0:
                raise RuntimeError("tar failed for " + name)
        for f in group:
            if sha256_file(src / f["path"]) != f["sha256"]:
                raise RuntimeError("File changed while archiving: " + f["path"])
            f["part"] = name
        digest = sha256_file(part)
        gh("release", "upload", args.tag, str(part), "-R", args.repo)
        parts.append({"name": name, "bytes": part.stat().st_size, "sha256": digest, "files": len(group)})
        print(json.dumps(parts[-1]), flush=True)
        part.unlink()
        listing.unlink()
    manifest = {
        "schema": "private-release-backup/1",
        "source": args.label or str(src),
        "roots": list(args.roots),
        "snapshot_unix_time": int(now),
        "files": files,
        "skipped": skipped,
        "symlinks": links,
        "parts": parts,
        "restore": "download every part; tar -xzf each into one folder; check files[].sha256; recreate symlinks[]",
        "claims": "storage copy only",
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    gh("release", "upload", args.tag, str(stage / "manifest.json"), "-R", args.repo)
    print(f"uploaded {len(parts)} parts, {len(files)} files, {len(skipped)} skipped", flush=True)


def verify(args):
    dl = args.stage
    dl.mkdir(parents=True, exist_ok=False)
    gh("release", "download", args.tag, "-R", args.repo, "-p", "manifest.json", "-D", str(dl))
    manifest = json.loads((dl / "manifest.json").read_text())
    expected = {f["path"]: f["sha256"] for f in manifest["files"]}
    seen, bad = {}, []
    for part in manifest["parts"]:
        gh("release", "download", args.tag, "-R", args.repo, "-p", part["name"], "-D", str(dl))
        local = dl / part["name"]
        if sha256_file(local) != part["sha256"]:
            bad.append({"part": part["name"], "error": "archive hash differs from the manifest"})
        listing = subprocess.run(
            ["tar", "-xzf", str(local), "--to-command", 'sha256sum | cut -d" " -f1 | sed "s|$|  $TAR_FILENAME|"'],
            check=True, text=True, capture_output=True).stdout
        for line in listing.splitlines():
            digest, path = line.split("  ", 1)
            seen[path] = digest
        local.unlink()
        print(part["name"], "rehashed", flush=True)
    for path, digest in expected.items():
        if seen.get(path) != digest:
            bad.append({"path": path, "expected": digest, "restored": seen.get(path)})
    report = {"repo": args.repo, "tag": args.tag, "files_expected": len(expected),
              "files_restored": len(seen), "mismatches": bad,
              "verified": not bad and len(seen) == len(expected)}
    print(json.dumps(report, indent=2))
    return 0 if report["verified"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--src", type=Path, required=True, help="folder whose sub-folders are backed up")
    b.add_argument("--roots", nargs="+", required=True, help="sub-folders of --src to include")
    b.add_argument("--exclude", nargs="*", default=[], help="relative path prefixes to skip")
    b.add_argument("--quiet-minutes", type=float, default=15.0)
    b.add_argument("--batch-bytes", type=int, default=DEFAULT_BATCH_BYTES)
    b.add_argument("--prefix", required=True, help="asset name prefix")
    b.add_argument("--label", help="human description of the source recorded in the manifest")
    v = sub.add_parser("verify")
    for p in (b, v):
        p.add_argument("--repo", required=True, help="OWNER/REPO, must be private for backup")
        p.add_argument("--tag", required=True, help="existing release tag")
        p.add_argument("--stage", type=Path, required=True, help="new, empty staging folder")
    args = ap.parse_args(argv)
    if args.command == "backup":
        backup(args)
        return 0
    return verify(args)


if __name__ == "__main__":
    sys.exit(main())
