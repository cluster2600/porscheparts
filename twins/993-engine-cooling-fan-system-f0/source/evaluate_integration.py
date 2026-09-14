#!/usr/bin/env python3
"""Évalue l'intégration F0 du carter et de la turbine de refroidissement 993."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HOUSING_REPORT = (
    REPOSITORY_ROOT
    / "parts/993-eng-fan-housing-alsi10mg-f0-0001/evidence/engineering-screen.json"
)
IMPELLER_REPORT = (
    REPOSITORY_ROOT
    / "parts/993-eng-cooling-impeller-alsi10mg-f0-0001/evidence/engineering-screen.json"
)
HOUSING_STEP = (
    REPOSITORY_ROOT
    / "parts/993-eng-fan-housing-alsi10mg-f0-0001/derived/fan_housing_alsi10mg_f0.step"
)
IMPELLER_STEP = (
    REPOSITORY_ROOT
    / "parts/993-eng-cooling-impeller-alsi10mg-f0-0001/derived/cooling_impeller_alsi10mg_f0.step"
)
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "twins/993-engine-cooling-fan-system-f0/evidence/integration-screen.json"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPOSITORY_ROOT.resolve()).as_posix()


def _brep_clash(housing_step: Path, impeller_step: Path) -> dict[str, Any]:
    from build123d import import_step

    housing = import_step(str(housing_step))
    impeller = import_step(str(impeller_step))
    common = housing & impeller
    solids = [] if common is None else list(common.solids())
    overlap_volume_mm3 = sum(float(solid.volume) for solid in solids)
    return {
        "method": "exact OpenCascade BRep boolean intersection",
        "alignment": "synthetic coaxial X=Y=0 and shared front plane Z=0",
        "housing_valid_brep": bool(housing.is_valid),
        "impeller_valid_brep": bool(impeller.is_valid),
        "intersection_solid_count": len(solids),
        "intersection_volume_mm3": overlap_volume_mm3,
        "collision_detected": overlap_volume_mm3 > 0.0,
        "status": "failed_clearance" if overlap_volume_mm3 > 0.0 else "no_brep_overlap_at_synthetic_alignment",
    }


def build_report(
    housing_report_path: Path = HOUSING_REPORT,
    impeller_report_path: Path = IMPELLER_REPORT,
    housing_step: Path = HOUSING_STEP,
    impeller_step: Path = IMPELLER_STEP,
    *,
    measure_brep: bool = True,
) -> dict[str, Any]:
    housing = _load(housing_report_path)
    impeller = _load(impeller_report_path)
    integration = impeller["upstream_f0_integration"]
    housing_results = housing["results"]
    impeller_results = impeller["results"]

    throat_mm = float(integration["housing_synthetic_throat_mm"])
    impeller_od_mm = float(integration["impeller_synthetic_outer_diameter_mm"])
    required_radial_clearance_mm = float(integration["minimum_synthetic_radial_clearance_mm"])
    cold_diametral_clearance_mm = throat_mm - impeller_od_mm
    cold_radial_clearance_mm = cold_diametral_clearance_mm / 2.0
    required_throat_mm = impeller_od_mm + 2.0 * required_radial_clearance_mm
    throat_shortfall_mm = required_throat_mm - throat_mm

    housing_growth_mm = float(housing_results["free_throat_diametral_growth_mm"])
    impeller_growth_mm = float(impeller_results["free_outer_diametral_growth_mm"])
    hot_radial_clearance_mm = (
        throat_mm + housing_growth_mm - impeller_od_mm - impeller_growth_mm
    ) / 2.0

    housing_flow_m3_s = float(housing["synthetic_cases"]["airflow_m3_s"])
    impeller_flow_m3_s = float(impeller["synthetic_cases"]["airflow_m3_s"])
    flow_delta_m3_s = housing_flow_m3_s - impeller_flow_m3_s
    flow_delta_percent_of_impeller = 100.0 * flow_delta_m3_s / impeller_flow_m3_s

    housing_bpf_hz = float(housing_results["synthetic_blade_pass_frequency_hz"])
    impeller_bpf_hz = float(impeller_results["blade_pass_frequency_hz"])
    frequency_delta_hz = impeller_bpf_hz - housing_bpf_hz

    brep = (
        _brep_clash(housing_step, impeller_step)
        if measure_brep
        else {
            "method": "exact OpenCascade BRep boolean intersection",
            "alignment": "synthetic coaxial X=Y=0 and shared front plane Z=0",
            "collision_detected": None,
            "status": "not_executed",
        }
    )
    cold_clearance_pass = cold_radial_clearance_mm >= required_radial_clearance_mm
    hot_clearance_pass = hot_radial_clearance_mm >= required_radial_clearance_mm
    brep_clearance_pass = brep["collision_detected"] is False

    return {
        "schema_version": "1.0.0",
        "twin_id": "TWIN-993-ENGINE-COOLING-FAN-SYSTEM-F0",
        "status": "f0_synthetic_assembly_integration_failed",
        "inputs": {
            "housing": {
                "part_id": housing["part_id"],
                "engineering_report": _relative(housing_report_path),
                "engineering_report_sha256": _sha256(housing_report_path),
                "step": _relative(housing_step),
                "step_sha256": _sha256(housing_step),
            },
            "impeller": {
                "part_id": impeller["part_id"],
                "engineering_report": _relative(impeller_report_path),
                "engineering_report_sha256": _sha256(impeller_report_path),
                "step": _relative(impeller_step),
                "step_sha256": _sha256(impeller_step),
            },
        },
        "authority": {
            "level": "F0_synthetic_research_only",
            "alignment": "coaxial local axes and shared front plane are an explicit hypothesis",
            "not_claimed": "No measured Porsche housing, fan, shaft, alternator, pulley, shim, bearing, tip-clearance or axial-location interface is represented.",
        },
        "clearance_screen": {
            "housing_throat_diameter_mm": throat_mm,
            "impeller_outer_diameter_mm": impeller_od_mm,
            "required_minimum_radial_clearance_mm": required_radial_clearance_mm,
            "cold_diametral_clearance_mm": cold_diametral_clearance_mm,
            "cold_radial_clearance_mm": cold_radial_clearance_mm,
            "required_throat_diameter_mm": required_throat_mm,
            "throat_diameter_shortfall_mm": throat_shortfall_mm,
            "housing_free_diametral_growth_mm": housing_growth_mm,
            "impeller_free_diametral_growth_mm": impeller_growth_mm,
            "hot_radial_clearance_mm": hot_radial_clearance_mm,
            "cold_clearance_pass": cold_clearance_pass,
            "hot_clearance_pass": hot_clearance_pass,
            "equations": {
                "cold": "c_radial=(D_throat-D_impeller)/2",
                "required_throat": "D_required=D_impeller+2*c_required",
                "hot": "c_hot=(D_throat+delta_D_throat-D_impeller-delta_D_impeller)/2",
            },
        },
        "brep_clash_screen": brep,
        "flow_contract_screen": {
            "housing_target_m3_s": housing_flow_m3_s,
            "impeller_target_m3_s": impeller_flow_m3_s,
            "delta_m3_s": flow_delta_m3_s,
            "delta_percent_of_impeller_target": flow_delta_percent_of_impeller,
            "status": "failed_inconsistent_synthetic_targets",
        },
        "excitation_contract_screen": {
            "housing_assumed_blade_pass_frequency_hz": housing_bpf_hz,
            "impeller_assumed_blade_pass_frequency_hz": impeller_bpf_hz,
            "frequency_delta_hz": frequency_delta_hz,
            "status": "failed_inconsistent_speed_and_blade_count_assumptions",
        },
        "mass_screen": {
            "synthetic_assembly_mass_g": float(housing_results["cad_mass_g"])
            + float(impeller_results["cad_mass_g"]),
            "role": "scalar bookkeeping only; not an assembly mass validation",
        },
        "gates": {
            "cold_clearance": cold_clearance_pass,
            "hot_clearance": hot_clearance_pass,
            "brep_no_clash": brep_clearance_pass,
            "flow_contract_consistent": False,
            "excitation_contract_consistent": False,
            "simready_property_assignment": False,
            "physicsnemo_model_executed": False,
            "manufacturing_authorized": False,
            "engine_operation_authorized": False,
            "release_authorized": False,
            "integration_pass": False,
        },
        "failure_reasons": [
            "The synthetic 280 mm impeller exceeds the synthetic 252 mm housing throat.",
            "The exact BRep clash test detects overlap at the explicit coaxial front-plane alignment.",
            "The separate F0 flow targets differ and do not form a fan/system operating point.",
            "The separate speed and blade-count assumptions produce incompatible excitation frequencies.",
            "No measured axial transform, runout, thermal field, fan map, balance or containment boundary exists.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--housing-report", type=Path, default=HOUSING_REPORT)
    parser.add_argument("--impeller-report", type=Path, default=IMPELLER_REPORT)
    parser.add_argument("--housing-step", type=Path, default=HOUSING_STEP)
    parser.add_argument("--impeller-step", type=Path, default=IMPELLER_STEP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-brep", action="store_true")
    args = parser.parse_args()
    report = build_report(
        args.housing_report,
        args.impeller_report,
        args.housing_step,
        args.impeller_step,
        measure_brep=not args.skip_brep,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["gates"]["integration_pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
