#!/usr/bin/env python3
"""Validate F1 engine simulation contracts without loading local scan assets."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins" / "engine-simulation-contracts"
COMPLETE_917 = ROOT / "twins" / "reference-917-engine" / "complete-engine-f1.json"


def load(name):
    with (CONTRACT / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def main():
    materials = load("materials-f1.json")
    interfaces = load("interfaces-f1.json")
    components = load("components-f1.json")
    load_cases = load("load-cases-f1.json")
    segmentation = load("segmentation-f1.json")
    engine_components = load("engine-components-f1.json")
    complete_917 = json.loads(COMPLETE_917.read_text(encoding="utf-8"))

    assert all(doc["schema_version"] == "1.0.0" for doc in (
        materials, interfaces, components, load_cases, segmentation, engine_components
    ))

    interface_ids = [item["interface_id"] for item in interfaces["interfaces"]]
    assert len(interface_ids) == len(set(interface_ids))
    for item in interfaces["interfaces"]:
        assert item["source_report"].startswith(("work/", "twins/"))
        if item["units"] == "OBJ_unit":
            assert item["unit_status"] == "unconfirmed"

    material_ids = set(materials["materials"])
    source_ids = {
        json.loads(path.read_text(encoding="utf-8"))["source_id"]
        for path in (ROOT / "catalog" / "sources").glob("*.json")
    }
    for material_id, material in materials["materials"].items():
        assert set(material["source_ids"]) <= source_ids, material_id
        if material["assignment_status"] == "unassigned":
            assert material.get("property_sets") == {}

    component_ids = [item["component_id"] for item in components["components"]]
    assert len(component_ids) == len(set(component_ids))
    for item in components["components"]:
        assert item["material_id"] in material_ids
        if "interface_id" in item:
            assert item["interface_id"] in interface_ids
        assert item["release_status"] in {"research_only", "fit_check_only"}
    assert components["local_asset_policy"] == {
        "raw_scans_in_git": False,
        "derived_meshes_in_git": False,
        "usd_in_git": False,
        "reports_and_scripts_in_git": True,
    }

    for case in load_cases["load_cases"]:
        assert set(case["targets"]) <= set(component_ids)
        missing = [key for key, value in case["required_inputs"].items() if value is None]
        if missing:
            assert case["status"].startswith("blocked_"), case["load_case_id"]
    policy = load_cases["physicsnemo_policy"]
    assert policy["execution_enabled"] is False
    assert "surrogate_only_after_validated_baseline" == policy["role"]

    config_917 = segmentation["engine_917"]
    assert config_917["expected_openings_per_bank"] == 6
    assert config_917["opening_neighborhood_radius_obj_units"] <= 58.9
    assert engine_components["status"] == "F1_parametric_envelope_proxies_not_manufacturing_geometry"
    for family_id, family in engine_components["families"].items():
        assert set(family["source_ids"]) <= source_ids, family_id
    assert engine_components["families"]["piston_993_turbo"]["evidence"]["diameter"] == "nominal_engine_bore_not_piston_measurement"
    assert engine_components["families"]["camshaft_993_layout"]["evidence"]["all_dimensions"] == "layout_hypothesis"
    assert complete_917["schema_version"] == "1.0.0"
    assert set(complete_917["source_ids"]) <= source_ids
    family_ids = [item["id"] for item in complete_917["component_families"]]
    assert len(family_ids) == len(set(family_ids)) == 31
    assert sum(item["count"] for item in complete_917["component_families"]) == 275
    assert complete_917["status"] == "F1_complete_functional_family_assembly_not_manufacturing_geometry"
    assert complete_917["prohibited_use"]
    print("Engine simulation contracts OK")


if __name__ == "__main__":
    main()
