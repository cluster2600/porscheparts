"""Recompute public evidence consistency offline; never run a model or native code."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORBIDDEN_PAYLOAD_KEYS = {
    "question", "prompt", "gold", "messages", "input_ids", "attention_mask",
    "labels", "response", "raw_messages", "passage", "raw_output", "source_text",
}


def load(root: Path, name: str):
    return json.loads((root / name).read_text(encoding="utf-8"))


def require(condition: bool, reason: str):
    if not condition:
        raise ValueError(reason)


def check_payload_keys(value):
    if isinstance(value, dict):
        require(not (set(value) & FORBIDDEN_PAYLOAD_KEYS), "model/source payload field")
        for child in value.values():
            check_payload_keys(child)
    elif isinstance(value, list):
        for child in value:
            check_payload_keys(child)


def e_scores(root: Path):
    reviews = [load(root, f"e/blind/reviewer-{n}.json") for n in (1, 2)]
    mapping = load(root, "e/blind/arm-map.json")
    indices = []
    for review in reviews:
        require(len(review["rows"]) == 60, "blind grade count")
        index = {(r["id"], r["arm"]): r for r in review["rows"]}
        require(len(index) == 60, "duplicate blind grade")
        indices.append(index)
    require(set(indices[0]) == set(indices[1]), "blind roster disagreement")
    result, passed = {}, {}
    for role, arm in mapping["role_to_blind_arm"].items():
        keys = [k for k in indices[0] if k[1] == arm]
        require(len(keys) == 20, "arm denominator")
        for key in keys:
            a, b = indices[0][key], indices[1][key]
            require(a["response_sha256"] == b["response_sha256"], "response binding")
            require(a["run_sha256"] == b["run_sha256"], "run binding")
            require(a["run_sha256"] == mapping["runs"][role]["run_sha256"], "arm run")
        individual = [sum(idx[k]["acceptable"] is True for k in keys) for idx in indices]
        passed[role] = {k[0]: all(idx[k]["acceptable"] is True for idx in indices) for k in keys}
        result[role] = {"individual": individual, "initial": sum(passed[role].values())}
    require(mapping["runs"]["base"]["applied_adapter_sha256"] is None, "base applies adapter")
    require(set(passed["base"]) == set(passed["adapter"]), "paired task mismatch")
    wins = sum(passed["adapter"][k] and not passed["base"][k] for k in passed["base"])
    losses = sum(passed["base"][k] and not passed["adapter"][k] for k in passed["base"])
    supplement = load(root, "e/post-grading-admission-supplement.json")
    require(supplement["original_two_blinded_grade_files_unchanged"], "rewritten blind notes")
    require(not supplement["reserved_opened"] and not supplement["candidate_adopted"], "reserve/adoption")
    affected = supplement["additional_critical_failure_id"]
    for role, values in result.items():
        require(passed[role].get(affected) is True, "correction was not additional")
        values["post_claim"] = values["initial"] - 1
        require(values["post_claim"] == supplement["supplemental_conservative_acceptable_by_arm"][role], "supplement count")
        require(supplement["supplemental_critical_failures_by_arm"][role] == 1, "critical count")
    return {"arms": result, "paired_wins": wins, "paired_losses": losses}


def check(root: Path = HERE):
    manifest = load(root, "MANIFEST.json")
    names = [entry["path"] for entry in manifest["payloads"]]
    require(len(names) == len(set(names)), "duplicate manifest path")
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.name != "MANIFEST.json" and "__pycache__" not in p.parts}
    require(actual == set(names), "unregistered publication file")
    for entry in manifest["payloads"]:
        rel = Path(entry["path"])
        require(not rel.is_absolute() and ".." not in rel.parts, "unsafe manifest path")
        path = root / rel
        require(not path.is_symlink(), "publication symlink")
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == entry["sha256"], "payload hash: " + str(rel))
        require(len(data) == entry["bytes"], "payload length")
        text = data.decode("utf-8")
        require(not re.search(r"/(?:Users|home|private/tmp)/|C:\\Users\\", text), "local account path")
        require(not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|(?m:^-----BEGIN [A-Z ]*PRIVATE KEY-----$)", text), "credential pattern")
        if rel.suffix == ".json":
            check_payload_keys(json.loads(text))
    origins = load(root, "ORIGINS.json")
    for entry in origins["exact_originals"]:
        data = (root / entry["public_path"]).read_bytes()
        require(hashlib.sha256(data).hexdigest() == entry["origin_sha256"], "frozen original changed")
    e = e_scores(root)
    require(e["paired_wins"] == e["paired_losses"] == 0, "E paired outcome")
    require(all(v == {"individual": [15, 16], "initial": 15, "post_claim": 14} for v in e["arms"].values()), "E reported scores")
    selection = load(root, "e/selection-receipt.json")
    require(selection["candidate_acceptable"] == 15 and not selection["reserved_opened"], "original rejection overwritten")
    utility = load(root, "utility/evidence.json")["utility"]
    require(utility["complete"] == utility["usable_as_is"] == 0 and utility["cases"] == 8, "utility denominator")
    require(len(utility["rows"]) == 8, "utility row count")
    require([r["output_tokens_and_ceiling"][0] for r in utility["rows"]] == [384, 384, 384, 384, 256, 384, 384, 192], "utility budget")
    require(all(not r["eos_reached"] and not r["as_is_pass"] for r in utility["rows"]), "utility completion")
    coder = load(root, "coder/evidence.json")["coder_baseline"]
    require(coder["actual_eos_pass"] and not coder["static_admission_pass"] and not coder["truncation"], "Coder gate distinction")
    require(coder["output_tokens_including_eos"] == 368 and coder["generations"] == 1, "Coder count")
    control = load(root, "control/evidence.json")
    for case in control["geometry_cases"]:
        raw, derived = case["raw"], case["derived"]
        require(raw["geometry_gate"] == "failed" and raw["zero_area_faces"] == 80 and raw["nonfinite_normal_records"] == 76, "raw defects")
        require(raw["triangles"] - derived["triangles"] == 80, "cleanup count")
        require(derived["euler"] == 0 and derived["components"] == 1 and derived["edge_incidence_and_direction_failures"] == 0, "derived scope")
        expected = math.pi / 4 * (case["outer_diameter_mm"] ** 2 - 20 ** 2) * 3
        require(math.isclose(expected, derived["analytic_volume_mm3"], rel_tol=1e-12), "analytic volume")
        require(math.isclose(derived["signed_volume_mm3"] / expected - 1, derived["relative_mesh_volume_error"], abs_tol=1e-12), "volume error")
        require(case["cleanup"]["signed_volume_delta_mm3"] == 0 and case["cleanup"]["remaining_coordinate_attribute_bytes_preserved"], "cleanup interpretation")
    resource = load(root, "control/RESOURCE_EXCEPTION.json")["facts"]
    peak = resource["native_peak_interval"]
    ratio = peak["cpu_seconds_delta"] / peak["wall_seconds_delta"]
    require(math.isclose(ratio, peak["sampled_core_equivalents"], rel_tol=1e-12) and ratio > 2, "CPU ratio")
    require(not resource["strict_requested_cpu_ceiling_satisfied"], "strict CPU failure hidden")
    correction = load(root, "control/RAW_METADATA_CORRECTION.json")
    require(correction["corrected_raw_genus"] is None and not correction["mesh_geometry_changed"], "distinct raw correction")
    return {"status": "passed_public_consistency_only", "payloads": len(names), "E": e, "utility_complete": 0, "coder_static_pass": False, "control_strict_cpu_pass": False, "model_or_native_execution": False}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
