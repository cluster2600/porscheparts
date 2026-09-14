"""Supplementary inspection of the Physics Agent USD, not a final conformed render."""
import json

from common import Phase, sha

if __name__ == "__main__":
    p = Phase("render")
    profile = p.require("profile-initial", passed=False)
    asset = p.asset_from("physics")
    # Preserve the NVIDIA report and common receipt; scope lives in a sidecar.
    with (p.output / "inspection.json").open("x") as stream:
        json.dump({
            "schema_version": "1.0.0", "job_id": p.root.name,
            "job_manifest_sha256": p.manifest_sha256,
            "purpose": "pre_conformance_static_inspection", "source_phase": "physics",
            "source_usd_path": str(asset), "source_usd_sha256": sha(asset),
            "profile_initial_report_sha256": sha(p.root / "results/profile-initial/reference.json"),
            "profile_initial_passed": profile.get("passed") is True,
            "image_path": str(p.output / "inspection.png"),
            "render_success_not_asserted": True,
            "is_final_conformed_render": False,
            "simulation_validated": False, "manufacturing_authorized": False,
            "warnings": [
                "Inspection only; profile and conformance findings remain unchanged.",
                "Material/Physics Agent assignments are not qualified engineering properties.",
                "No engine, thermal, strength or manufacturing validation is supplied by this image.",
            ],
        }, stream, indent=2)
        stream.write("\n")
    raise SystemExit(p.invoke("ovrtx-render-service", [
        asset, p.output / "inspection.png", "--width", "1600", "--height", "1200",
    ]))
