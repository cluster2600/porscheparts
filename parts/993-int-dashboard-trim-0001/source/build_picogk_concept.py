#!/usr/bin/env python3
"""Rebuild the evidence-limited F0 dashboard-trim concept with PicoGK.

The current catalogue PicoGK configuration selects a topology study whose
ignored density fields are not in Git. This route uses its same numerical
parameters with the tracked base generator, without publishing a new part.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PART_ID = "993-INT-DASHBOARD-TRIM-0001"
SOURCE = ROOT / "parts" / PART_ID.lower() / "source" / "picogk.json"
CATALOGUE_RECORD = ROOT / "catalog" / "parts" / f"{PART_ID.lower()}.json"
GENERATOR = ROOT / "parts" / "picogk-catalog" / "body" / "DashboardTrim.cs"
PROJECT = GENERATOR.parent / "Body.csproj"
RUNNER_TOOLS = ROOT / "parts" / "picogk-catalog" / "tools"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_revision(path: Path) -> str | None:
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def concept_spec(source: dict) -> dict:
    """Select the base F0 generator; refuse a silent functional promotion."""
    if source.get("part_id") != PART_ID:
        raise ValueError("dashboard part ID does not match the catalogue variant")
    if source.get("catalogue_record") != CATALOGUE_RECORD.relative_to(ROOT).as_posix():
        raise ValueError("dashboard catalogue record reference changed")
    if source.get("safety_class") != "functional":
        raise ValueError("dashboard safety class changed; review the part record")
    if not str(source.get("status", "")).startswith("F0 concept geometry"):
        raise ValueError("only the F0 concept may use this build route")
    if source.get("generator") not in {"bionic_topology", "dashboard_trim_panel"}:
        raise ValueError("unexpected source generator; review before rebuilding")
    if not source.get("open_interfaces"):
        raise ValueError("open interfaces must remain explicit")
    params = source.get("parameters")
    if not isinstance(params, dict) or not params:
        raise ValueError("dashboard parameters are missing")
    for key, param in params.items():
        if not isinstance(param, dict):
            raise ValueError(f"{key}: parameter entry is invalid")
        value = param.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key}: parameter value must be finite")
        if key == "vehicle_width_bound_mm":
            if param.get("basis") != "published" or not param.get("source"):
                raise ValueError("vehicle-width bound needs its cited source")
        elif param.get("basis") != "assumption":
            raise ValueError(f"{key}: the F0 geometry must remain assumption-labelled")

    spec = copy.deepcopy(source)
    spec["generator"] = "dashboard_trim_panel"
    spec["name"] = "993 dashboard trim base F0 visual concept (no passenger airbag)"
    spec["picogk_enhancement"] = "Base PicoGK visual study; no topology-density inputs or measured attachments"
    spec["porsche_part_numbers"] = []
    spec["part_number_status"] = "Unresolved for the no-passenger-airbag target; PET 809-00 lists 055/056 00 with passenger airbag"
    spec["open_interfaces"].append("M564-to-Porsche-part-number mapping unresolved in the catalogue PET note")
    return spec


def run_logged(argv: list[str], output: Path, env: dict[str, str], timeout: int) -> None:
    try:
        result = subprocess.run(argv, env=env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        output.write_text(f"Timed out after {timeout} s\n", encoding="utf-8")
        raise RuntimeError(f"command timed out after {timeout} s: {argv[0]}") from exc
    output.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{argv[0]} exited {result.returncode}; see {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="new private output directory, normally under work/")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"output already exists; choose a fresh directory: {output}")
    if ROOT not in output.parents:
        raise SystemExit("output must stay within the repository's ignored work/ directory")
    if output.relative_to(ROOT).parts[0] != "work":
        raise SystemExit("output must stay within the repository's ignored work/ directory")

    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    record = json.loads(CATALOGUE_RECORD.read_text(encoding="utf-8"))
    if record.get("part_id") != PART_ID or record.get("validation", {}).get("status") != "concept":
        raise SystemExit("catalogue identity/status changed; review before an F0 rebuild")
    if record.get("geometry", {}).get("source_type") != "estimated":
        raise SystemExit("the F0 route requires an estimated-geometry catalogue record")
    spec = concept_spec(source)
    dotnet = os.environ.get("DOTNET") or shutil.which("dotnet")
    if not dotnet:
        raise SystemExit("dotnet not found; source the qualified PicoGK environment")
    upstream = Path(os.environ.get("UpstreamRoot", str(ROOT.parent / "upstream"))).resolve()
    if not (upstream / "PicoGK" / "PicoGK.csproj").is_file():
        raise SystemExit(f"PicoGK source checkout unavailable: {upstream}")

    output.mkdir(parents=True)
    spec_path = output / "concept-spec.json"
    spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    env = dict(os.environ)
    env["UpstreamRoot"] = str(upstream)
    native = upstream / "native"
    native_runtimes = sorted(native.glob("picogk.*.so"))
    if len(native_runtimes) != 1:
        raise SystemExit("expected one qualified PicoGK native runtime under native/")
    env["LD_LIBRARY_PATH"] = str(native) + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    build_dir = output / "build"
    run_logged([dotnet, "build", str(PROJECT), "-c", "Release", "-o", str(build_dir),
                "-p:GeneratePackageOnBuild=false", "-nologo", "-v:q"],
               output / "build.log", env, 300)

    sys.path.insert(0, str(RUNNER_TOOLS))
    from run_part import LOCK, acquire  # Same machine-wide native lock as catalogue builds.

    acquire(timeout_s=600)
    try:
        run_logged([dotnet, str(build_dir / "Body.dll"), str(spec_path), str(output)],
                   output / "run.log", env, 600)
    finally:
        LOCK.unlink(missing_ok=True)

    mesh = output / f"{PART_ID}.stl"
    report = output / f"{PART_ID}.report.json"
    if not mesh.is_file() or not report.is_file():
        raise RuntimeError("PicoGK returned without a mesh and report")
    manifest = {
        "part_id": PART_ID,
        "scope": "F0 visual concept for a 993 dashboard trim; target has no passenger airbag, exact part number unresolved",
        "input_basis": "assumed_geometry",
        "catalogue_status": "concept",
        "repository_revision": git_revision(ROOT),
        "picogk_source_revision": git_revision(upstream / "PicoGK"),
        "picogk_native_runtime_sha256": {native_runtimes[0].name: sha256(native_runtimes[0])},
        "catalogue_record_sha256": sha256(CATALOGUE_RECORD),
        "build_script_sha256": sha256(Path(__file__).resolve()),
        "source_config_sha256": sha256(SOURCE),
        "generator_source_sha256": sha256(GENERATOR),
        "concept_spec_sha256": sha256(spec_path),
        "mesh_sha256": sha256(mesh),
        "report_sha256": sha256(report),
        "report": json.loads(report.read_text(encoding="utf-8")),
        "open_interfaces": spec["open_interfaces"],
        "limitations": [
            "The span, surface, vent, opening, wall and rib dimensions are assumptions.",
            "The PET mapping of 055/056 00 to the no-passenger-airbag target is unresolved.",
            "No attachment coordinates or passenger-airbag interface are modeled.",
            "The mesh is a study output, not a print file or evidence of fit, function or safety.",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"F0 concept generated: {mesh}\nProvenance: {output / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
