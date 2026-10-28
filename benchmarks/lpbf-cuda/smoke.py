"""Build upstream CPU programs and check thermal functions; CUDA is untested."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cxx", default="c++")
    args = parser.parse_args()
    source = args.source.resolve()
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if revision != "b81c9a0d8abae302c9a4eeacf384502d2220d360":
        raise ValueError("Unreviewed LPBF-CUDA source revision")
    subprocess.run(["git", "-C", str(source), "diff", "--exit-code", "HEAD", "--", "thermal", "dynamics"], check=True)
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    thermal = source / "thermal"
    control = Path(__file__).with_name("thermal_control.cpp").resolve()
    compiler = subprocess.check_output([args.cxx, "--version"], text=True).splitlines()[0]
    common = [str(thermal / name) for name in ("particle.cpp", "thermal.cpp", "utility.cpp")]
    with (output / "build.log").open("w") as log:
        for name, inputs in (
            ("cpu_thermal", [str(thermal / "cpu_thermal.cpp"), *common]),
            ("cpu_dynamic", [str(source / "dynamics" / "deposition_sim.cpp")]),
            ("thermal_control", [str(control), *common]),
        ):
            # Upstream particle.cpp uses time() without including <ctime>; GCC requires it.
            result = subprocess.run([args.cxx, "-std=c++11", "-O2", "-include", "ctime", "-I", str(thermal), *inputs,
                                     "-o", str(output / name)], stdout=log, stderr=log, timeout=120)
            if result.returncode:
                log.flush()
                print((output / "build.log").read_text())
                result.check_returncode()
    subprocess.run([str(output / "thermal_control")], check=True, timeout=30)
    report = {
        "status": "passed_cpu_build_and_thermal_controls",
        "source_commit": revision,
        "compiler": compiler,
        "control_sha256": hashlib.sha256(control.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "binary_sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                          for name in ("cpu_thermal", "cpu_dynamic", "thermal_control")},
        "full_deposition_or_scan_executed": False,
        "cuda_validated": False,
        "manufacturing_qualified": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
