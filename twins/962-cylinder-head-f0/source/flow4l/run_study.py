"""Rebuild, export and inspect the fixed 4 L study without replacing previous runs."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import inspect_and_render as inspection

ROOT = Path(__file__).resolve().parents[4]
SOURCE = Path(__file__).resolve().parent


def run(installation, output):
    installation, output = installation.resolve(), output.resolve()
    if output.exists():
        raise ValueError("Run output must be new; rejected runs are retained")
    
    dotnet = installation / "sdk/dotnet"
    runtime = installation / "runtime"
    shape = installation / "libraries/LEAP71_ShapeKernel"
    lattice = installation / "libraries/LEAP71_LatticeLibrary"
    output.mkdir(parents=True)
    shutil.copytree(SOURCE, output / "source", ignore=shutil.ignore_patterns("bin", "obj", "__pycache__"))
    build = [str(dotnet), "build", str(SOURCE / "Engine.csproj"), "-c", "Release",
             "-p:PicoGKBinaryRoot=" + str(runtime), "-p:ShapeKernelRoot=" + str(shape),
             "-p:LatticeLibraryRoot=" + str(lattice), "-o", str(output / "bin")]
    with (output / "build.log").open("w") as log:
        subprocess.run(build, cwd=installation / "Workbench", check=True, stdout=log, stderr=subprocess.STDOUT)
    for path in runtime.glob("*.dylib"):
        shutil.copy2(path, output / "bin" / path.name)
    lock_spec = importlib.util.spec_from_file_location("native_lock", ROOT / "parts/picogk-catalog/tools/run_part.py")
    lock = importlib.util.module_from_spec(lock_spec); lock_spec.loader.exec_module(lock)
    command = [str(dotnet), str(output / "bin/Engine.dll"), str(SOURCE), str(output / "native")]
    receipt = dict(build_command=build, native_command=command,
                   sdk_version=subprocess.check_output([str(dotnet), "--version"], cwd=installation / "Workbench", text=True).strip(),
                   source_hashes={p.name: inspection.base.sha(p) for p in SOURCE.iterdir() if p.is_file()},
                   shared_native_lock=str(lock.LOCK))
    (output / "run.json").write_text(json.dumps(receipt, indent=2) + "\n")
    lock.acquire()
    try:
        with (output / "native.log").open("w") as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    finally:
        lock.LOCK.unlink(missing_ok=True)
    return inspection.inspect(output / "native", output / "bin", shape, output / "inspected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installation", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.installation, args.output)
