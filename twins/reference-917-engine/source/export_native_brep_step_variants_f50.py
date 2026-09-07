#!/usr/bin/env python3
"""Export a clean private native B-Rep through controlled STEP profiles.

This tool never changes 3D curves or surfaces.  It varies only STEP schema,
surface-curve serialization and uncertainty metadata so interoperability can be
audited independently from the native OCCT CAD/CAE master.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopoDS import TopoDS_Shape


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_native(path: Path):
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape, str(path), BRep_Builder()):
        raise RuntimeError("native_BREP_read_failed")
    return shape


def write_profile(shape, path: Path, profile: dict) -> dict:
    Interface_Static.SetCVal_s("write.step.schema", profile["schema"])
    Interface_Static.SetIVal_s("write.surfacecurve.mode", profile["surfacecurve_mode"])
    Interface_Static.SetIVal_s("write.precision.mode", profile["precision_mode"])
    Interface_Static.SetRVal_s("write.precision.val", profile["precision_mm"])
    writer = STEPControl_Writer()
    status = writer.Transfer(shape, STEPControl_AsIs)
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEP_transfer_failed:{profile['id']}:{status}")
    status = writer.Write(str(path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEP_write_failed:{profile['id']}:{status}")
    return {
        **profile,
        "filename": path.name,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-brep", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.expected_sha256 and sha256(args.input_brep) != args.expected_sha256:
        raise RuntimeError("native_BREP_SHA256_mismatch")
    args.output.mkdir(parents=True, exist_ok=True)
    shape = read_native(args.input_brep)
    profiles = [
        {
            "id": "ap214_surfacecurves_least",
            "schema": "AP214IS",
            "surfacecurve_mode": 1,
            "precision_mode": 0,
            "precision_mm": 1.0e-3,
        },
        {
            "id": "ap214_surfacecurves_user_0p02",
            "schema": "AP214IS",
            "surfacecurve_mode": 1,
            "precision_mode": 1,
            "precision_mm": 2.0e-2,
        },
        {
            "id": "ap242_surfacecurves_user_0p02",
            "schema": "AP242DIS",
            "surfacecurve_mode": 1,
            "precision_mode": 1,
            "precision_mm": 2.0e-2,
        },
    ]
    exports = [
        write_profile(shape, args.output / f"917-head-2v-f50-{profile['id']}.step", profile)
        for profile in profiles
    ]
    report = {
        "schema": "porsche-917-f50-private-step-interoperability-profiles/v1",
        "source_native_brep_sha256": sha256(args.input_brep),
        "geometry_edit_used": False,
        "global_ellipse_used": False,
        "global_oval_used": False,
        "global_box_used": False,
        "profiles": exports,
        "all_profiles_require_independent_roundtrip_audit": True,
        "release": {"manufacturing_authorized": False, "engine_start_authorized": False},
    }
    report_path = args.output / "917-head-2v-f50-step-profiles-private.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"profiles_written": len(exports), "report": str(report_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
