"""SimReady row: STEP -> OpenUSD with NVIDIA usd-convert-cad, then NVIDIA validation.

For every STEP given, this script

  1. converts it to a binary OpenUSD stage with the packaged NVIDIA converter
     (`usd-convert-cad`, a separate process and a separate virtual environment:
     the converter embeds its own OpenUSD and HOOPS Exchange runtime);
  2. re-opens the result and records what the converter authored (default
     prim, metersPerUnit, upAxis, prim / mesh / triangle counts);
  3. runs the NVIDIA validator (`nvidia_usd_validate`, package
     usd-validation-nvidia, the successor of omni.asset_validator) on it.

`--existing-stage` runs the same validator on a stage this script did not
convert (the T4 stage written by export_usd.py) and writes its own summary.

Only scalars reach the summaries: tool versions, hashes, counts, units, axis,
one line per validator rule that reported an issue, and wall-clock seconds.
The stages, the converter log and the raw validator reports stay in OUT_DIR,
which must be a private (git-ignored) directory.

A validator pass shows a well-formed stage. It asserts no fit, no measurement,
no physical property and no SimReady profile conformance. The independent
geometry check of the converted stage is simready_check.py, which shares no
code with this file and runs in another interpreter.

Interpreter: the one that holds `usd-validation-nvidia` and its OpenUSD
runtime (`pxr`), never the converter's and never the twin's build123d venv.

Usage:
  simready_convert.py --converter BIN --out-dir OUT_DIR --summary SUMMARY.json
                      [--validator BIN] [--up-axis file|y|z] [--tess-lod 0-4]
                      [--accurate-tessellation]
                      [--existing-stage STAGE --existing-stage-summary JSON]
                      [STEP ...]

Exit status: 0 every conversion succeeded and every validated stage passed;
1 a tool failed (conversion, validator crash, unreadable stage); 3 the tools
ran but at least one stage has validator findings. The summaries are written
in all three cases and carry the status; a failed run is never relabelled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCHEMA = "935-cad-twin-simready/1"
CLAIMS = ("study twin; a validator pass shows a well-formed stage only: not SimReady-certified, "
          "not measured, not fitted, not functional, not released")
CREATOR = "porscheparts-935-cad-twin"
SEVERITIES = ("FAILURE", "ERROR", "WARNING", "INFO")
BLOCKING = ("FAILURE", "ERROR")
MESSAGE_CHARS = 240


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(temporary, path)


def identifier(stem: str) -> str:
    """Output basename the converter can use as a prim name without transcoding."""
    name = re.sub(r"[^A-Za-z0-9_]", "_", stem)
    return name if re.match(r"[A-Za-z_]", name) else f"_{name}"


def package_version(executable: Path, distribution: str) -> str | None:
    """Version of a distribution installed beside a console script."""
    python = executable.parent / "python"
    if not python.exists():
        return None
    done = subprocess.run(
        [str(python), "-I", "-c",
         f"import importlib.metadata as m; print(m.version({distribution!r}))"],
        capture_output=True, text=True, check=False)
    return done.stdout.strip() or None


def validator_tools(validator: Path) -> dict:
    """Versions and default rule set, read from the validator's own interpreter."""
    probe = (
        "import json, logging; logging.disable(logging.CRITICAL)\n"
        "import importlib.metadata as m\n"
        "import omni.asset_validator as av\n"
        "from pxr import Usd\n"
        "engine = av.ValidationEngine()\n"
        "print(json.dumps({'usd_validation_nvidia': m.version('usd-validation-nvidia'),\n"
        "  'validator_openusd': '.'.join(map(str, Usd.GetVersion())),\n"
        "  'validator_rules_initialized': len(engine.initialized_rules),\n"
        "  'validator_rule_names': ' '.join(sorted(r.__name__ for r in engine.initialized_rules))}))\n"
    )
    done = subprocess.run([str(validator.parent / "python"), "-I", "-c", probe],
                          capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise RuntimeError(f"validator runtime probe failed: {done.stderr.strip()[-400:]}")
    return json.loads(done.stdout.strip().splitlines()[-1])


def convert(converter: Path, step: Path, out_dir: Path, options: list[str]) -> tuple[dict, Path | None]:
    """Run usd-convert-cad into a temporary directory, publish by atomic rename."""
    output = out_dir / f"{identifier(step.stem)}.usdc"
    log = out_dir / f"{output.stem}.convert.log"
    record = {"status": "failed", "returncode": None, "wall_seconds": None,
              "output": output.name, "output_sha256": None, "output_bytes": None}
    before = sha256(step)
    staging = Path(tempfile.mkdtemp(dir=out_dir, prefix=f".{output.stem}.", suffix=".tmp"))
    try:
        # The converter derives prim names from the output basename, so only
        # the directory is temporary.
        command = [str(converter), "-i", str(step), "-o", str(staging / output.name), *options]
        start = time.monotonic()
        done = subprocess.run(command, capture_output=True, text=True, check=False)
        record["wall_seconds"] = round(time.monotonic() - start, 2)
        record["returncode"] = done.returncode
        log.write_text(done.stdout + done.stderr)
        if done.returncode != 0:
            record["error"] = (done.stderr.strip() or done.stdout.strip())[-MESSAGE_CHARS:]
            return record, None
        if not (staging / output.name).is_file():
            record["error"] = "converter returned 0 without writing the stage"
            return record, None
        if sha256(step) != before:
            record["error"] = "source STEP changed during conversion"
            return record, None
        os.replace(staging / output.name, output)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    record.update(status="passed", output_sha256=sha256(output), output_bytes=output.stat().st_size)
    return record, output


def stage_statistics(path: Path) -> dict:
    """What the stage holds, read back with the validator's OpenUSD runtime."""
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError(f"stage cannot be opened: {path.name}")
    default = stage.GetDefaultPrim()
    layer = stage.GetRootLayer()
    by_type: dict[str, int] = {}
    meshes = faces = triangles = non_triangles = points = 0
    for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
        by_type[prim.GetTypeName() or "(untyped)"] = by_type.get(prim.GetTypeName() or "(untyped)", 0) + 1
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(prim)
        counts = mesh.GetFaceVertexCountsAttr().Get() or []
        meshes += 1
        faces += len(counts)
        triangles += sum(max(int(c) - 2, 0) for c in counts)
        non_triangles += sum(1 for c in counts if int(c) != 3)
        points += len(mesh.GetPointsAttr().Get() or [])
    bound = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]) \
        .ComputeWorldBound(stage.GetPseudoRoot()).ComputeAlignedRange()
    return {
        "default_prim": str(default.GetPath()) if default and default.IsValid() else None,
        "root_prims": [str(p.GetPath()) for p in stage.GetPseudoRoot().GetChildren()],
        # Authored values, with whether they were authored: a fallback is not a statement.
        "meters_per_unit": UsdGeom.GetStageMetersPerUnit(stage),
        "meters_per_unit_authored": bool(stage.HasAuthoredMetadata("metersPerUnit")),
        "up_axis": str(UsdGeom.GetStageUpAxis(stage)),
        "up_axis_authored": bool(stage.HasAuthoredMetadata("upAxis")),
        "kilograms_per_unit": (stage.GetMetadata("kilogramsPerUnit")
                               if stage.HasAuthoredMetadata("kilogramsPerUnit") else None),
        "layer_creator": (layer.customLayerData or {}).get("creator"),
        "prims": sum(by_type.values()),
        "prims_including_abstract": sum(1 for _ in stage.TraverseAll()),
        "prims_by_type": dict(sorted(by_type.items())),
        "meshes": meshes,
        "mesh_faces": faces,
        "triangles": triangles,
        "non_triangle_faces": non_triangles,
        "mesh_points": points,
        "world_bound_from_authored_extents_stage_units": (
            None if bound.IsEmpty() else [[round(v, 4) for v in bound.GetMin()],
                                          [round(v, 4) for v in bound.GetMax()]]),
    }


def validate(validator: Path, stage: Path, out_dir: Path) -> dict:
    """Run nvidia_usd_validate with its default rules; keep the raw report private."""
    raw = out_dir / f"{stage.stem}.nvidia-validation.json"
    raw.unlink(missing_ok=True)
    before = sha256(stage)
    start = time.monotonic()
    # Run beside the stage and pass its basename, so that no private absolute
    # path reaches a rule message.
    done = subprocess.run([str(validator), "--json-output", str(raw.resolve()), stage.name],
                          cwd=stage.resolve().parent, capture_output=True, text=True, check=False)
    record = {"status": "not_run", "returncode": done.returncode,
              "wall_seconds": round(time.monotonic() - start, 2)}
    (out_dir / f"{stage.stem}.nvidia-validation.log").write_text(done.stdout + done.stderr)
    if done.returncode not in (0, 1) or not raw.is_file():
        record["error"] = (done.stderr.strip() or done.stdout.strip())[-MESSAGE_CHARS:]
        return record
    if sha256(stage) != before:
        record["error"] = "the validator modified the stage it was asked to read"
        return record
    report = json.loads(raw.read_text())
    totals = dict.fromkeys(SEVERITIES, 0)
    rules = []
    for entry in report.get("rules", []):
        counts: dict[str, int] = {}
        for issue in entry.get("issues", []):
            counts[issue["severity"]] = counts.get(issue["severity"], 0) + 1
            totals[issue["severity"]] = totals.get(issue["severity"], 0) + 1
        if not counts:
            continue
        first = entry["issues"][0]
        rules.append({
            "rule": entry["rule"]["name"],
            "rule_status": entry.get("status"),
            "issues_by_severity": counts,
            "first_message": " ".join(first["message"].split())[:MESSAGE_CHARS],
            "first_at": (first.get("at") or {}).get("path"),
        })
    record.update(status=report.get("status"), issues_by_severity=totals,
                  rules_with_issues=sorted(rules, key=lambda r: r["rule"]),
                  raw_report_sha256=sha256(raw))
    return record


def verdict(validations: list[dict]) -> str:
    """Status of one summary: tool_failure, validator_findings or passed."""
    if any(v.get("status") not in ("PASS", "FAIL") for v in validations):
        return "tool_failure"
    if any(v["status"] != "PASS" or any(v.get("issues_by_severity", {}).get(s, 0) for s in BLOCKING)
           for v in validations):
        return "validator_findings"
    return "passed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("steps", nargs="*", type=Path, metavar="STEP")
    parser.add_argument("--converter", type=Path, help="path to the usd-convert-cad console script")
    parser.add_argument("--validator", type=Path,
                        default=Path(sys.executable).parent / "nvidia_usd_validate",
                        help="path to nvidia_usd_validate (default: beside this interpreter)")
    parser.add_argument("--out-dir", type=Path, required=True, help="private directory for stages and raw reports")
    parser.add_argument("--summary", type=Path, help="scalar summary of the conversions")
    parser.add_argument("--up-axis", choices=("file", "y", "z"), default="file",
                        help="converter up-axis; 'file' keeps what the STEP implies")
    parser.add_argument("--tess-lod", type=int, choices=range(5), help="converter tessellation level")
    parser.add_argument("--accurate-tessellation", action="store_true")
    parser.add_argument("--existing-stage", type=Path, help="a stage to validate without converting")
    parser.add_argument("--existing-stage-summary", type=Path)
    args = parser.parse_args(argv)

    if not args.steps and not args.existing_stage:
        parser.error("nothing to do: give at least one STEP or --existing-stage")
    if args.steps and not (args.converter and args.summary):
        parser.error("converting needs --converter and --summary")
    if args.existing_stage and not args.existing_stage_summary:
        parser.error("--existing-stage needs --existing-stage-summary")
    inputs = [*args.steps, *([args.existing_stage] if args.existing_stage else [])]
    for path in inputs:
        if not path.is_file():
            parser.error(f"not a file: {path}")
    for step in args.steps:
        if step.suffix.lower() not in (".step", ".stp"):
            parser.error(f"not a STEP file: {step.name}")
    if len({identifier(s.stem) for s in args.steps}) != len(args.steps):
        parser.error("two STEP files map to the same output name")
    for tool in (args.validator, *([args.converter] if args.steps else [])):
        if not tool.is_file():
            parser.error(f"tool not found: {tool}")

    started = time.monotonic()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    tools = {"python": platform.python_version(), **validator_tools(args.validator)}
    options = ["--up-axis", args.up_axis, "--instancing-style", "reference",
               "--composition-style", "none", "--filter-style", "deactivate", "--creator", CREATOR]
    if args.tess_lod is not None:
        options += ["--tess-lod", str(args.tess_lod)]
    if args.accurate_tessellation:
        options.append("--accurate-tessellation")

    statuses = []
    existing = None
    if args.existing_stage:
        stage = args.existing_stage
        existing = {"name": stage.name, "sha256": sha256(stage), "bytes": stage.stat().st_size}
        try:
            existing["stage"] = stage_statistics(stage)
            existing["validation"] = validate(args.validator, stage, args.out_dir)
        except Exception as exc:  # recorded, then reported through the exit status
            existing["error"] = f"{type(exc).__name__}: {exc}"[:MESSAGE_CHARS]
        existing_status = verdict([existing.get("validation", {})])
        statuses.append(existing_status)
        write_json(args.existing_stage_summary, {
            "schema": SCHEMA, "claims": CLAIMS, "kind": "validation of an existing stage",
            "status": existing_status, "tools": tools, "stage_input": existing,
            "wall_seconds_total": round(time.monotonic() - started, 2)})

    records = []
    if args.steps:
        tools["usd_convert_cad"] = package_version(args.converter, "usd-convert-cad")
    for step in args.steps:
        record = {"name": step.name, "sha256": sha256(step), "bytes": step.stat().st_size}
        try:
            record["conversion"], output = convert(args.converter, step, args.out_dir, options)
            if output is not None:
                record["stage"] = stage_statistics(output)
                record["validation"] = validate(args.validator, output, args.out_dir)
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"[:MESSAGE_CHARS]
        records.append(record)

    if args.steps:
        # The status of this summary covers its own inputs only; an existing
        # stage validated in the same run keeps its status in its own summary.
        status = verdict([r.get("validation", {}) for r in records])
        statuses.append(status)
        summary = {"schema": SCHEMA, "claims": CLAIMS, "kind": "STEP to OpenUSD conversion and validation",
                   "status": status, "tools": tools, "converter_options": options, "inputs": records}
        if existing is not None:
            summary["existing_stage"] = {"name": existing["name"], "sha256": existing["sha256"],
                                         "status": existing_status,
                                         "summary": args.existing_stage_summary.name}
        summary["wall_seconds_total"] = round(time.monotonic() - started, 2)
        write_json(args.summary, summary)

    for record in records:
        conversion, validation = record.get("conversion", {}), record.get("validation", {})
        print(f"{record['name']}: conversion {conversion.get('status')}, "
              f"validator {validation.get('status', 'not_run')} {validation.get('issues_by_severity', '')}")
    if existing is not None:
        validation = existing.get("validation", {})
        print(f"{existing['name']}: validator {validation.get('status', 'not_run')} "
              f"{validation.get('issues_by_severity', '')}")
    print(f"status: {', '.join(statuses)}")
    return 1 if "tool_failure" in statuses else 3 if "validator_findings" in statuses else 0


if __name__ == "__main__":
    raise SystemExit(main())
