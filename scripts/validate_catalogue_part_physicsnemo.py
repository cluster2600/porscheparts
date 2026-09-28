#!/usr/bin/env python3
"""Validate the fail-closed PhysicsNeMo structural surrogate contract."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins" / "catalogue-parts" / "physicsnemo-structural-f0.json"
ENGINEERING = ROOT / "twins" / "catalogue-parts" / "engineering-f0.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path}: expected a JSON object")
    return value


def validate() -> dict:
    contract = load(CONTRACT)
    engineering = load(ENGINEERING)

    assert contract["target"]["twin_id"] == "TWIN-993-ENGINE-CARRIER-TURBO"
    assert contract["target"]["status"].startswith("blocked_")
    assert contract["problem_shape"]["data_shape"].startswith("variable_topology_unstructured_")

    discovery = contract["discovery"]
    assert discovery["canonical_repository"] == "https://github.com/NVIDIA/physicsnemo"
    assert HEX40.fullmatch(discovery["current_snapshot"]["commit"])
    assert discovery["runtime_snapshot"]["version"] == "2.2.0"
    assert HEX40.fullmatch(discovery["runtime_snapshot"]["commit"])
    for path in discovery["verified_paths_in_runtime_snapshot"]:
        assert not Path(path).is_absolute(), path
        assert ".." not in Path(path).parts, path

    models = {entry["model"]: entry for entry in contract["model_menu"]}
    assert set(models) == {"GeoTransolver", "MeshGraphNet", "Transolver", "FIGConvUNet"}
    assert models["GeoTransolver"]["status"].startswith("selected_")
    assert models["MeshGraphNet"]["runtime_extra"] == "gnns"

    pilot = contract["selected_pilot"]
    assert pilot["model"] in models
    assert pilot["model"] == "GeoTransolver"
    assert pilot["serialization"].startswith("VTU_")
    assert pilot["execution_enabled"] is False
    assert pilot["adapter_status"].startswith("not_implemented_")

    dataset = contract["dataset_contract"]
    assert dataset["unit_system"] == "SI"
    assert dataset["reference_solver"] == "CalculiX"
    assert "displacement_m" in dataset["nodal_targets"]
    assert "von_mises_stress_Pa" in dataset["nodal_targets"]
    split = dataset["split_policy"]
    assert split["train_samples"] == split["validation_samples"] == split["held_out_test_samples"] == 0
    assert split["random_node_split_prohibited"] is True
    assert split["held_out_geometry_or_load_family_required"] is True

    gates = contract["enablement_gates"]
    assert gates
    assert all(value is False for value in gates.values())
    assert engineering["physicsnemo_policy"]["execution_enabled"] is False
    assert engineering["summary"]["ready_for_physicsnemo"] == 0
    assert "PhysicsNeMo_as_reference_solver" in contract["prohibited_claims"]
    assert "road_use_without_professional_review_and_physical_validation" in contract["prohibited_claims"]
    return contract


def main() -> int:
    contract = validate()
    print(
        "OK   "
        f"{CONTRACT.relative_to(ROOT)} "
        f"({len(contract['model_menu'])} models, {len(contract['datapipe_menu'])} datapipes, execution blocked)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
