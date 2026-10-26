"""Freeze and replay the carrier's existing, independently blocked contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

from ft_common import (
    HERE,
    ROOT,
    load,
    new_directory,
    receipt,
    sha256,
    verify_inputs,
    write,
)

from ft_common import CARRIER_RECORD as PART, CARRIER_CONVERGENCE as CONVERGENCE

INTERFACES = "twins/993-engine-mount-system-f0/interface-contract.json"
STUDY = "parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/auxiliary-fea-study"
INPUTS = [
    PART,
    INTERFACES,
    f"{STUDY}/mechanics-study.json",
    f"{STUDY}/surface.mesh64.gz",
    CONVERGENCE,
]


def freeze(root, output):
    output = new_directory(output)
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    inputs = [{"path": path, "sha256": sha256(Path(root) / path)} for path in INPUTS]
    manifest = {
        "schema_version": 1,
        "part_id": "993-ENG-CARRIER-0001",
        "revision": revision,
        "inputs": inputs,
        "units": "mm, N, MPa, s, tonne",
        "catalogue_geometry_changed": False,
        "R2_adopted": False,
        "new_tool_controls_are_synthetic": True,
    }
    write(output / "manifest.json", manifest)
    return manifest


def replay(manifest_path, root, output):
    manifest = load(manifest_path)
    verify_inputs(manifest, root)
    if manifest["part_id"] != "993-ENG-CARRIER-0001" or {
        x["path"] for x in manifest["inputs"]
    } != set(INPUTS):
        raise ValueError("wrong carrier input contract")
    # Bind the gate to reviewed inputs, not to caller-supplied status booleans.
    registered = load(HERE / "baseline.json")
    if manifest["inputs"] != registered["inputs"]:
        raise ValueError("carrier baseline differs from registered hashes")
    contract = load(Path(root) / INTERFACES)
    blockers = []
    if contract["status"] != "measured_interfaces_verified":
        blockers.append("missing_measured_variant_interfaces")
    if contract["load_path"]["forces_and_boundary_conditions"] is None:
        blockers.append("missing_measured_load_case")
    # The registered R2 comparison explicitly leaves convergence open.
    blockers.append("carrier_mesh_convergence_not_demonstrated")
    study = load(Path(root) / STUDY / "mechanics-study.json")
    result = receipt(
        "carrier-replay",
        "blocked_engineering",
        manifest["inputs"],
        checks={
            "input_hashes_verified": True,
            "catalogue_unchanged": True,
            "optimization_enabled": False,
            "blockers": blockers,
            "carrier_stages": {
                "cloudcompare": "blocked_no_registered_scan_and_registration_contract",
                "salome": "blocked_no_reviewed_surface_face_groups_in_registered_inputs",
                "openturns": "blocked_no_converged_solver_response_or_qualified_probability_model",
                "openmdao": "blocked_native_fem_replay_and_optimization_not_accepted",
            },
            "documented_support_stiffness_scenarios_N_mm": study[
                "support_sensitivity_per_eye_N_mm"
            ],
        },
        limitations=["R2 is an unadopted study; no new native solve is claimed."],
    )
    output = new_directory(output)
    write(output / "receipt.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["freeze", "replay"])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = (
        freeze(args.root, args.output)
        if args.command == "freeze"
        else replay(args.manifest, args.root, args.output)
    )
    print(result.get("status", "inputs_frozen"))


if __name__ == "__main__":
    main()
