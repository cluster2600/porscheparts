"""Build and inspect one bionic family geometry in a new, retained directory."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

import inspect_family as inspection

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[3]


def run(installation, config, output):
    installation, config, output = installation.resolve(), config.resolve(), output.resolve()
    if output.exists():
        raise ValueError("Output must be new; rejected runs are retained")
    inspection.verify_libraries(installation)
    output.mkdir(parents=True)
    shutil.copytree(SOURCE, output / "source", ignore=shutil.ignore_patterns("bin", "obj", "__pycache__"))
    shutil.copy2(config, output / "input.json")
    dotnet, runtime = installation / "sdk/dotnet", installation / "runtime"
    build = [str(dotnet), "build", str(SOURCE / "Engine.csproj"), "-c", "Release",
             "-p:PicoGKBinaryRoot=" + str(runtime),
             "-p:ShapeKernelRoot=" + str(installation / "libraries/LEAP71_ShapeKernel"),
             "-p:LatticeLibraryRoot=" + str(installation / "libraries/LEAP71_LatticeLibrary"),
             "-o", str(output / "bin")]
    with (output / "build.log").open("w") as log:
        subprocess.run(build, cwd=installation / "Workbench", check=True, stdout=log, stderr=subprocess.STDOUT)
    for path in runtime.glob("*.dylib"):
        shutil.copy2(path, output / "bin" / path.name)
    lock = inspection.load("family_native_lock", ROOT / "parts/picogk-catalog/tools/run_part.py")
    command = [str(dotnet), str(output / "bin/Engine.dll"), str(output / "input.json"), str(output / "native")]
    receipt = dict(build_command=build, native_command=command, config_sha256=inspection.sha(config),
                   sdk_version=subprocess.check_output([str(dotnet), "--version"], cwd=installation / "Workbench", text=True).strip(),
                   source_hashes={str(p.relative_to(ROOT)): inspection.sha(p) for p in SOURCE.iterdir() if p.is_file()},
                   shared_native_lock=str(lock.LOCK))
    (output / "run.json").write_text(json.dumps(receipt, indent=2) + "\n")
    lock.acquire()
    try:
        with (output / "native.log").open("w") as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    finally:
        lock.LOCK.unlink(missing_ok=True)
    return inspection.inspect(output / "native", output / "input.json", output / "inspected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("installation", "config", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = run(args.installation, args.config, args.output)
    print(json.dumps(dict(status=result["status"], clearance_mm=result["sampled_water_dry_clearance_mm"],
                          metrics=result["mesh_metrics"]), indent=2))
