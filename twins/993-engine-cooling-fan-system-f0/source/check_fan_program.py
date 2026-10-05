#!/usr/bin/env python3
"""Check programme references, immutable receipts and boundaries between models."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FAN = Path(__file__).resolve().parents[1]


def check():
    from check_research_registry import check as check_research
    check_research()
    from check_material_process_import import check as check_materials
    check_materials()
    from check_engineering_iteration import check as check_engineering
    check_engineering()
    program = json.loads((FAN / "program/program.json").read_text())
    research = json.loads((ROOT / program["research_registry"]).read_text())
    for field in ("source_records", "distinct_url_groups"):
        if program["research"][field] != research[field]:
            raise ValueError("Programme research counts differ from the complete index")
    if program["research"]["engineering_validation"]:
        raise ValueError("Programme research is not engineering validation")
    if program["scan_geometry_used_in_new_calculations"] or program["scan"]["raw_or_geometry_derivatives_published"]:
        raise ValueError("Private scan must remain outside published geometry and calculations")
    if program["scan"]["units"] is not None or program["scan"]["scale_verified"] or program["scan"]["equivalence_935_993_verified"]:
        raise ValueError("No supporting metrology/identity evidence in this programme revision")
    for name in program["catalogue_records"] + program["evidence_records"] + [program["asset"], program["execution_report"]]:
        if not (ROOT / name).is_file():
            raise ValueError(f"Missing programme reference: {name}")
    catalogue = [json.loads((ROOT / name).read_text()) for name in program["catalogue_records"]]
    if any(c["validation"]["status"] != "concept" or c["classification"]["safety_class"] != "prohibited_pending_engineering" for c in catalogue):
        raise ValueError("Archived catalogue status changed without reviewing this programme")
    rotor, = [c for c in catalogue if "impeller" in c["classification"]["category"]]
    if rotor["vehicle"]["porsche_part_numbers"] != ["96410601531"] or program["current_target"]["reference_part_number"] != "96410601522":
        raise ValueError("Carrera/Turbo identities must remain distinct")
    for variant in program["variants"]:
        for field in ("source", "parameters"):
            if field in variant and not (ROOT / variant[field]).is_file():
                raise ValueError(f"Missing variant {field}: {variant['id']}")
    if any(program["release_gates"].values()):
        raise ValueError("No release evidence supports an approved gate in this programme revision")
    evidence = FAN / "results/program-20261003"
    manifest = json.loads((evidence / "manifest.json").read_text())
    for name, sha in manifest["files_sha256"].items():
        if hashlib.sha256((FAN / name).read_bytes()).hexdigest() != sha:
            raise ValueError(f"Evidence hash mismatch: {name}")
    for label in ("control", "pitch42"):
        report = json.loads((evidence / f"cfd/{label}-summary.json").read_text())
        audit = json.loads((evidence / f"cfd/{label}-audit.json").read_text())
        if report["last_iteration"] != 2000 or not report["normal_solver_exit"]:
            raise ValueError("Unexpected final CFD receipt")
        if report["numerical_window_checks_passed"] or report["nonlinear_residual_checks_passed"] or report["validated_airflow_m3_s"] is not None:
            raise ValueError("Rejected CFD may not acquire a validation claim")
        if audit["integral_checks_passed"] or audit["nonlinear_residual_checks_passed"] or audit["physical_gain_validated"]:
            raise ValueError("CFD audit claims unsupported acceptance")
    modal = json.loads((evidence / "modal/summary.json").read_text())
    if hashlib.sha256(gzip.decompress((evidence / "modal/modal.inp.gz").read_bytes())).hexdigest() != modal["file_sha256"]["modal.inp"]:
        raise ValueError("Modal input provenance mismatch")
    for name in ("modal.dat", "log.ccx", "preparation.json"):
        path = evidence / "modal" / name
        data = path.read_bytes() if path.is_file() else gzip.decompress(path.with_suffix(path.suffix + ".gz").read_bytes())
        if hashlib.sha256(data).hexdigest() != modal["file_sha256"][name]:
            raise ValueError(f"Modal native receipt mismatch: {name}")
    previous = json.loads((FAN / "results/organic/structure/reference-structure-50k/summary.json").read_text())
    if modal["source_deck_sha256"] != previous["file_sha256"]["rotor.inp"] or modal["safe_rpm_range"] is not None or modal["scan_used"]:
        raise ValueError("Modal calculation must remain bound to the unmeasured parametric reference")
    usd = json.loads((evidence / "usd-validation.json").read_text())
    if hashlib.sha256((ROOT / program["asset"]).read_bytes()).hexdigest() != usd["asset_sha256"]:
        raise ValueError("USD asset hash mismatch")
    if usd["scan_included"] or usd["digital_twin_validated"] or usd["meters_per_unit"] != 1 or usd["up_axis"] != "Z":
        raise ValueError("USD metadata or scope changed")
    entry = "twins/993-engine-cooling-fan-system-f0/README.md"
    if f"]({entry})" not in (ROOT / "README.md").read_text():
        raise ValueError("Missing root README entry")
    print("Fan programme references, receipt hashes and validation boundaries passed")


if __name__ == "__main__":
    check()
