#!/usr/bin/env python3
"""Four-case, standard-library extraction preparation; no model or backend."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys


class Rejected(ValueError):
    pass


SOURCE_BASE = "twins/993-engine-cooling-fan-system-f0/program/research/"
ADMITTED_INPUTS = {
    "EXTRACT-001": ("geometry_parameter_contract", "structured_parameter_definition",
        SOURCE_BASE + "corpus/geometry/parameter-contract.json", 128, 128,
        "/parameter_dictionary/9", "d7896e9445c00d594ca0c3f2a34f68bdd15f94d79bf5389f01c20000c48473a7",
        "6ec45c246c75a0635bcc71a0831ce884ed6ec0a830feb9f29ab030d06b727604"),
    "EXTRACT-002": ("geometry_research_gap", "structured_unavailable_claim",
        SOURCE_BASE + "corpus/geometry/evidence.json", 54, 54,
        "/claims/17", "228f7afc0d4726a13d540840ae4bf119366988357037406221990c9e1eb0ccbe",
        "779d01702212827765d0db14bfd150c9e5836e0609ab5c3e5073d0e401cc2cce"),
    "EXTRACT-003": ("material_legacy_assumption", "authored_assumption_card",
        SOURCE_BASE + "materials-20261003/ADMISSION.md", 35, 38, None,
        "82d1a849997ac4f1bd2d09d41cf5e175696e5f333c82e4d01a048eaa1879877a",
        "0d1d1d935313fdd012630fb75f28c0ad8f4c1bb7ce3061f118750d3a2f8f425e"),
    "EXTRACT-004": ("material_admission_contract", "authored_admission_boundary",
        SOURCE_BASE + "materials-20261003/ADMISSION.md", 10, 14, None,
        "82d1a849997ac4f1bd2d09d41cf5e175696e5f333c82e4d01a048eaa1879877a",
        "b700e79618c3d75c2b168bb3d3d34d5b94a1b34f203db441617c196040524e81"),
}
PUBLIC_PATHS = {entry[2] for entry in ADMITTED_INPUTS.values()} | {"LICENSE"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise Rejected("duplicate_json_key")
        result[key] = value
    return result


def strict_json(text):
    def invalid(value):
        raise Rejected("nonfinite_json_number:" + value)
    result = json.loads(text, object_pairs_hook=_pairs, parse_constant=invalid)
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise Rejected("nonfinite_json_number")
        if isinstance(value, dict):
            for item in value.values():
                finite(item)
        if isinstance(value, list):
            for item in value:
                finite(item)
    finite(result)
    return result


def support(text, phrase):
    start = text.find(phrase)
    if start < 0 or text.find(phrase, start + 1) >= 0:
        raise Rejected("support_span_missing_or_ambiguous")
    return {"char_start": start, "char_end": start + len(phrase),
            "utf8_sha256": sha(phrase.encode("utf-8"))}


def check_input(row):
    if set(row) != {"id", "family", "parser_kind", "source", "excerpt"}:
        raise Rejected("input_schema")
    source, text = row["source"], row["excerpt"]
    observed = (row["family"], row["parser_kind"], source["path"],
                source["line_start"], source["line_end"], source["json_pointer"],
                source["file_sha256"], source["excerpt_sha256"])
    if row["id"] not in ADMITTED_INPUTS or observed != ADMITTED_INPUTS[row["id"]]:
        raise Rejected("input_outside_exact_four_span_whitelist")
    if not isinstance(text, str) or not text or len(text.encode("utf-8")) > 2048:
        raise Rejected("excerpt_budget")
    if (source["excerpt_sha256"] != sha(text.encode("utf-8")) or
            source["chars"] != len(text) or source["utf8_bytes"] != len(text.encode("utf-8"))):
        raise Rejected("excerpt_binding")
    if (source["ownership"] != "project_authored" or
            source["authority"] != "project_context" or
            source["third_party_payload"] is not False):
        raise Rejected("source_not_project_authored")
    if source["license"] != "porscheparts Proprietary License v1.0":
        raise Rejected("source_rights_changed")
    if (source["license_evidence"]["path"] != "LICENSE" or
            source["license_evidence"]["sha256"] !=
            "518ff42b02bb3263adbc938cd0863c565e389589876fe8b93db2ef624d316b53"):
        raise Rejected("license_binding_changed")
    path = Path(source["path"])
    if path.is_absolute() or ".." in path.parts or "forums" in path.parts:
        raise Rejected("source_path_not_admitted")
    return text


def record(parameter, kind, value, source_value, source_unit, unit, status,
           variant, conditions, level, qualifiers, limitations, accepted_for,
           span, normalization=None):
    return {"parameter_id": parameter, "record_kind": kind, "value": value,
            "source_value": source_value, "source_unit": source_unit, "unit": unit,
            "status": status, "variant": variant, "conditions": conditions,
            "evidence_level": level, "qualifiers": qualifiers,
            "limitations": limitations, "accepted_for": accepted_for,
            "normalization": normalization, "causal_claim": False,
            "review_required": True, "support_span": span}


def extract(row):
    """Inputs alone are sufficient; gold files are never opened by this code."""
    text = check_input(row)
    kind, records = row["parser_kind"], []
    if kind == "structured_parameter_definition":
        data = strict_json(text.strip().rstrip(","))
        if data["id"] != "rotor.outer_diameter" or data["unit"] != "mm":
            raise Rejected("definition_identity_or_unit")
        records.append(record(data["id"], "parameter_definition", None, None,
            None, data["unit"], "definition_only", None,
            {"datum": "A", "station": None, "specimen_condition": None},
            "project_definition", ["maximum_swept_tip_diameter"],
            ["Dictionary entry supplies no measured value, specimen or uncertainty."],
            ["parameter_definition"], support(text, data["definition"])))
    elif kind == "structured_unavailable_claim":
        data = strict_json(text.strip().rstrip(","))
        if (data["id"] != "GEO-C018" or data["source_ids"] != [] or
                data["value"] is not None or data["status"] != "unavailable"):
            raise Rejected("unknown_claim_changed")
        records.append(record(data["parameter"], "research_gap", None, None,
            None, None, "unavailable", data["application"], {},
            "project_context_negative_finding", ["bounded_to_inspected_evidence"],
            [data["note"]], [], support(text, '"value":null')))
    elif kind == "authored_assumption_card":
        if ("legacy **assumed** isotropic" not in text or
                "not relabeled as" not in text or
                "not a measured alloy property" not in text):
            raise Rejected("assumption_qualifiers_missing")
        match = re.search(r"E = (\d+) GPa, Poisson ratio (\d+\.\d+), density (\d+) kg/m³", text)
        if match is None:
            raise Rejected("assumption_pattern_or_units")
        e, poisson, density = int(match[1]), float(match[2]), int(match[3])
        common = {"analysis": "rotation_and_eigenstrain_sensitivity",
                  "constitutive_idealization": "isotropic", "temperature_degC": None,
                  "qualified_alloy": None, "supplier_route": None}
        entries = [("material.young_modulus", e * 1000, e, "GPa", "MPa", match[1] + " GPa",
                    {"operation": "multiply", "factor": 1000, "from_unit": "GPa", "to_unit": "MPa"}),
                   ("material.poisson_ratio", poisson, poisson, None, "1", match[2],
                    {"operation": "dimensionless_parameter_identity", "source_unit_not_written": True}),
                   ("material.density", density, density, "kg/m³", "kg/m3", match[3] + " kg/m³",
                    {"operation": "unit_spelling_only", "from_unit": "kg/m³", "to_unit": "kg/m3"})]
        for parameter, value, original, original_unit, unit, phrase, normalization in entries:
            records.append(record(parameter, "research_assumption", value, original,
                original_unit, unit, "assumed", "legacy_project_isotropic_card",
                dict(common), "project_research_assumption", ["legacy", "assumed", "isotropic"],
                ["Not qualified AlSi10Mg, AlF357 or another vendor route.",
                 "Not a measured alloy property or part-specific allowable."],
                ["research_sensitivity_only"], support(text, phrase), normalization))
    elif kind == "authored_admission_boundary":
        if ("comparisons and sensitivities" not in text or
                "not a qualified material" not in text or
                "Never join on the scenario name alone." not in text):
            raise Rejected("admission_qualifiers_missing")
        records.append(record("machine.selected", "research_gap", None, None, None,
            None, "unavailable", "impeller_material_process_comparison", {},
            "project_admission_boundary", ["selected_machine_unknown"],
            ["No qualified material card or manufacturing route is admitted."], [],
            support(text, "selected machine remains null")))
        keys = ["material", "scenario", "source", "orientation", "temperature", "property"]
        records.append(record("material.record_join", "integration_rule", None,
            None, None, None, "definition_only", None, {"required_join_keys": keys},
            "project_admission_boundary", ["shared_scenario_name_is_not_unique"],
            ["Do not merge AlSi10Mg and AlF357 through EOS_M290_30_AB alone."],
            ["record_join_constraint"], support(text,
            "join on material, scenario, source, orientation, temperature and property.")))
    else:
        raise Rejected("parser_kind_not_admitted")
    return {"case_id": row["id"], "records": records,
            "status": "preparation_dev_requires_human_review", "measured_records": 0}


def validate(row, candidate):
    if not isinstance(candidate, dict):
        raise Rejected("candidate_schema")
    expected = extract(row)
    try:
        observed_json = json.dumps(candidate, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False)
        expected_json = json.dumps(expected, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as error:
        raise Rejected("candidate_invalid_json_types") from error
    if observed_json != expected_json:
        raise Rejected("candidate_not_exact_source_supported_contract")
    return True


def read_public_file(root, relative):
    if relative not in PUBLIC_PATHS:
        raise Rejected("source_path_not_in_public_allowlist")
    root = root.resolve(strict=True)
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise Rejected("source_symlink_forbidden")
    if path.resolve(strict=True) != root / relative:
        raise Rejected("source_path_resolution_changed")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 65536:
            raise Rejected("source_not_bounded_regular_file")
        data = source.read(65537)
        after = os.fstat(source.fileno())
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if (len(data) != before.st_size or
                any(getattr(before, field) != getattr(after, field) for field in fields)):
            raise Rejected("source_changed_during_read")
    return data


def verify_source(row, root):
    check_input(row)
    if root.resolve(strict=True) != Path(__file__).resolve().parents[2]:
        raise Rejected("repository_root_not_current_public_checkout")
    source = row["source"]
    data = read_public_file(root, source["path"])
    if sha(data) != source["file_sha256"]:
        raise Rejected("source_file_hash")
    if sha(read_public_file(root, "LICENSE")) != source["license_evidence"]["sha256"]:
        raise Rejected("license_file_hash")
    lines = data.decode("utf-8").splitlines(keepends=True)
    excerpt = "".join(lines[source["line_start"] - 1:source["line_end"]])
    if excerpt != row["excerpt"]:
        raise Rejected("source_line_span")
    pointer = source["json_pointer"]
    if pointer is not None:
        current = strict_json(data.decode("utf-8"))
        for part in pointer.lstrip("/").split("/"):
            key = part.replace("~1", "/").replace("~0", "~")
            current = current[int(key)] if isinstance(current, list) else current[key]
        if current != strict_json(excerpt.strip().rstrip(",")):
            raise Rejected("source_json_pointer")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [strict_json(line) for line in args.inputs.read_text().splitlines() if line]
    if len(rows) != 4 or len({row["id"] for row in rows}) != 4:
        raise Rejected("four_unique_cases_required")
    results = []
    for row in rows:
        verify_source(row, args.repository_root)
        results.append(extract(row))
    with args.output.open("x", encoding="utf-8") as output:
        for result in results:
            output.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": "preparation_only", "cases": len(results),
                      "records": sum(len(r["records"]) for r in results), "model_calls": 0}))


if __name__ == "__main__":
    try:
        main()
    except (Rejected, KeyError, ValueError, OSError) as error:
        print(json.dumps({"status": "failed_closed", "reason": str(error)}), file=sys.stderr)
        sys.exit(1)
