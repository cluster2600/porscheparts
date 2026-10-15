#!/usr/bin/env python3
"""Assemble a Linux LEAP root with the layout run_leap_f16.py expects, and its hashed receipt.

The Mac run used an installation receipt written when that machine was set up.
On Linux the two LEAP libraries are git checkouts: their revisions are verified
with git on clean trees instead of being taken from a receipt. PicoGK 2.3.0 and
SkiaSharp come from the NuGet packages F15 builds against; the native runtime
is the host's picogk.26.2.so with its bundled dependencies. Every file copied is
hashed into setup/installation.json, which run_leap_f16.py checks before building.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess

REVISIONS = {"leap71/LEAP71_ShapeKernel": "554bce4791d2676ed00bd6704f6eb010111a7fd3",
             "leap71/LEAP71_LatticeLibrary": "81c3c7b2064c19e573c38d76ac09bf1cd2f562d5"}
PICOGK_NUGET, SKIASHARP_NUGET = "2.3.0", "3.119.0"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""): h.update(block)
    return h.hexdigest()


def git(directory, *args):
    return subprocess.run(["git", "-C", str(directory), *args], check=True, capture_output=True, text=True).stdout.strip()


def prepare(picogk_home, nuget, dotnet_root, root):
    if root.exists():
        raise ValueError("Use a new LEAP root directory; earlier roots are retained")
    libraries = []
    for repo, revision in REVISIONS.items():
        checkout = picogk_home / repo.split("/")[1]
        if git(checkout, "rev-parse", "HEAD") != revision or git(checkout, "status", "--porcelain"):
            raise ValueError("Checkout is not the reviewed clean revision: " + str(checkout))
        if "Apache License" not in (checkout / "LICENSE").read_text(errors="replace")[:2000]:
            raise ValueError("Unexpected licence: " + str(checkout))
        libraries.append({"repository": repo, "revision": revision, "license": "Apache-2.0",
                          "verified_by": "git rev-parse HEAD on a clean checkout"})
    native = picogk_home / "native"
    copies = {"runtime/PicoGK.dll": nuget / f"picogk/{PICOGK_NUGET}/lib/net9.0/PicoGK.dll",
              "runtime/SkiaSharp.dll": nuget / f"skiasharp/{SKIASHARP_NUGET}/lib/net8.0/SkiaSharp.dll",
              "libraries/PicoGK/assets/ViewerEnvironment.zip": picogk_home / "PicoGK/assets/ViewerEnvironment.zip"}
    copies.update({"runtime/" + p.name: p for p in sorted(native.glob("*.so*"))})
    root.mkdir(parents=True)
    for target, source in copies.items():
        (root / target).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, root / target)
    for repo in REVISIONS:
        name = repo.split("/")[1]
        shutil.copytree(picogk_home / name, root / "libraries" / name, ignore=shutil.ignore_patterns(".git"))
    (root / "sdk").symlink_to(dotnet_root.resolve())
    hashed = sorted(p for p in root.rglob("*") if p.is_file() and not p.is_relative_to(root / "sdk"))
    receipt = {"platform": f"{platform.system()} {platform.machine()} {platform.release()}",
               "picogk_nuget": PICOGK_NUGET, "skiasharp_nuget": SKIASHARP_NUGET,
               "native_runtime_commit": (native / "RUNTIME_COMMIT").read_text().strip(),
               "dotnet_sdk": subprocess.run([str(dotnet_root / "dotnet"), "--version"], check=True,
                                            capture_output=True, text=True).stdout.strip(),
               "libraries": libraries,
               "sha256": {str(p.relative_to(root)): sha256(p) for p in hashed}}
    (root / "setup").mkdir()
    (root / "setup/installation.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--picogk-home", type=Path, default=home / "picogk")
    parser.add_argument("--nuget", type=Path, default=home / ".nuget/packages")
    parser.add_argument("--dotnet-root", type=Path, default=home / ".dotnet")
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    r = prepare(a.picogk_home, a.nuget, a.dotnet_root, a.output.resolve())
    print(json.dumps({k: r[k] for k in ("platform", "native_runtime_commit", "dotnet_sdk")} | {"files": len(r["sha256"])}, indent=1))
