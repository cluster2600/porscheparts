#!/usr/bin/env python3
"""Build DeliveryR2d and run it once, headless, under the machine-wide PicoGK lock.

    python generate.py --picogk <PicoGK.dll> --native <dir with picogk.26.2.so> \
        --study <study card> --bin <new build dir> --output <new output dir>

The lock is the one of parts/picogk-catalog/tools/run_part.py: parallel PicoGK
processes crashed the native kernel on this project. The run is software
rendered on purpose; a GPU driver is neither needed nor wanted for a voxel job.
Wrap this command in a memory cap (docs/LOCAL_HOST_SETUP.md section 3).

This is ../source-r2c/generate.py with the R2d project in place of the R2c one;
the R2 and R2c scripts are left as their receipts used them.
"""
import argparse
import hashlib
import json
import os
import runpy
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOCK = runpy.run_path(str(ROOT / "parts/picogk-catalog/tools/run_part.py"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for name in ("picogk", "native", "study", "bin", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.bin.exists():
        raise FileExistsError("Build and output directories must be new")
    dotnet = os.environ.get("DOTNET", "dotnet")
    subprocess.run([dotnet, "build", str(HERE / "DeliveryR2d.csproj"), "-c", "Release", "-nologo", "-v:q",
                    f"-p:PicoGKAssembly={args.picogk.resolve()}", "-o", str(args.bin)], check=True)
    libraries = sorted(p for p in args.native.iterdir() if ".so" in p.name)
    for library in libraries:
        shutil.copy2(library, args.bin / library.name)
    env = dict(os.environ, GALLIUM_DRIVER="llvmpipe", LIBGL_ALWAYS_SOFTWARE="1",
               LD_LIBRARY_PATH=str(args.bin.resolve()))
    LOCK["acquire"]()
    try:
        subprocess.run([dotnet, str(args.bin / "DeliveryR2d.dll"), str(args.study), str(args.output)],
                       env=env, check=True)
    finally:
        LOCK["LOCK"].unlink(missing_ok=True)
    receipt = {
        "status": "native_build_and_export_completed",
        "dotnet_version": subprocess.run([dotnet, "--version"], capture_output=True, text=True).stdout.strip(),
        "study": {"path": str(args.study.resolve().relative_to(ROOT)), "sha256": sha256(args.study)},
        "source_hashes": {str(p.relative_to(ROOT)): sha256(p) for p in (
            HERE / "Program.cs", HERE / "DeliveryR2d.csproj", ROOT / "parts/picogk-catalog/rotating/RotKit.cs",
            *sorted((ROOT / "parts/picogk-catalog/common").glob("*.cs")))},
        "binaries": {p.name: sha256(p) for p in (args.bin / "DeliveryR2d.dll", args.bin / "PicoGK.dll",
                                                 *(args.bin / q.name for q in libraries))},
        "generation": json.loads((args.output / "generation.json").read_text()),
        "outputs": {p.name: sha256(p) for p in sorted(args.output.glob("*.stl"))},
        "physical_fit_verified": False,
    }
    (args.output / "runtime-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt["outputs"], indent=2))


if __name__ == "__main__":
    main()
