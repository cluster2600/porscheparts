#!/usr/bin/env python3
"""Audit documentary observations versus implemented F2 source-feature bindings.

Published observations are not unique geometric dimensions. Citations, nominal
wheelbase and successful CAD/media checks cannot replace actual feature pairs,
identified contacts and an admitted common comparison frame.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path


REGISTRIES = {
    "MEAS-MANUAL-964-BODY-CONTROL": "964 repair-plate scalar/contact references",
    "MEAS-MANUAL-964-SUSPENSION-ALIGNMENT": "964 ground-to-named-contact ride-height directions",
    "MEAS-OWNER-964-FRAME-20261105": "Publisher-specific source-local CH/Mi/Ed datum and assembly state",
    "MEAS-MANUAL-993-FLOOR-CONTROL-20261104": "993 scalar spans; no 964 transfer or absolute XYZ",
    "MEAS-FIA-964-INTERIOR-20261105": "FIA seat/occupant measurement directions, not bare-floor Z",
    "MEAS-MANUAL-964-INTERFACE-SPANS-20261030": "964 documentary endpoint spans, no admitted XYZ",
}
MI_B_AMENDMENT = "twins/964-chassis/body-contact-alternatives-20261106/mi-b-width-correction.json"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare_distance(observation, model, binding):
    result = {"binding_status": "unimplemented_feature_or_frame", "model_value_mm": None,
              "delta_mm": None, "within_source_tolerance": None}
    if not binding or binding.get("part_identity") != observation["part_identity"] or \
       binding.get("identity_status") != "independently_qualified" or \
       binding.get("same_frame_admitted") is not True or model.get("units") != "mm" or observation.get("unit") != "mm":
        return result
    ids = binding.get("feature_ids", [])
    features = model.get("source_features_mm", {})
    if observation.get("comparison_kind") != "direct_distance" or len(ids) != 2 or \
       any(i not in features for i in ids):
        return result
    points = [features[i] for i in ids]
    if any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in points):
        return result
    value = math.dist(*points)
    delta = value - observation["source_scalar_mm"]
    tolerance = observation.get("source_tolerance_mm")
    return {"binding_status": "bound_direct_distance", "model_value_mm": value,
            "delta_mm": delta, "within_source_tolerance": abs(delta) <= tolerance
            if tolerance is not None else None}


def rows_from_registry(path, frame):
    record = json.loads(path.read_text())
    entries = {r["value_id"]: r for r in record["declared_values"]}
    datum_names = {r["details"]["point"]: r["value_text"] for r in entries.values()
                   if r.get("details", {}).get("kind") == "datum_point"}
    rows = []
    for entry in record["declared_values"]:
        details = dict(entry.get("details", {}))
        if details.get("between") and datum_names:
            details["catalogue_endpoint_definitions"] = [datum_names.get(p) for p in details["between"]]
        if record["measurement_id"] == "MEAS-MANUAL-964-SUSPENSION-ALIGNMENT" and details.get("field") in (
                "height_mm", "height_at_outer_mount_body_side_mm", "height_at_control_arm_mm"):
            definition = "0001" if details.get("axle") == "front_axle" else (
                "0024" if "outer_mount" in details.get("field", "") else "0023")
            details["named_contact_definition"] = entries["MNL-964SA-" + definition]["value_text"]
        values = entry.get("numeric_values", [])
        direct = details.get("measurement_basis") == "direct_distance"
        rows.append({"observation_origin": "catalogue_documentary_observation",
            "registry": record["measurement_id"], "observation_id": entry["value_id"],
            "source_id": entry.get("source_id", record.get("source_id")),
            "source_reference": json.dumps({"plate": entry.get("plate") or details.get("plate"),
                "pdf_page": entry.get("pdf_page"), "figure": details.get("figure")}),
            "source_member": details.get("member", ""),
            "source_file_sha256": details.get("source_file_sha256", details.get("source_pdf_sha256", "")),
            "source_extraction_status": entry.get("extraction_status", "not_specified"),
            "observation_kind": details.get("kind", details.get("field", "documentary_entry")),
            "part_identity": entry.get("description", "") +
                (" | " + details["named_contact_definition"] if "named_contact_definition" in details else ""),
            "source_frame": frame, "source_values": json.dumps(values),
            "source_value_text": entry.get("value_text", ""), "unit": entry.get("unit", ""),
            "source_scalar_mm": values[0] if direct and values else None,
            "source_tolerance_mm": details.get("span_tolerance_mm") if direct else None,
            "comparison_kind": "direct_distance" if direct else "requires_quantity_specific_contract",
            "endpoint_or_state_definition": json.dumps(details, ensure_ascii=False)})
    return rows


def coverage(rows, model, bindings):
    checked = []
    for row in rows:
        checked.append(dict(row, **compare_distance(row, model, bindings.get(row["observation_id"]))))
    bound = sum(r["binding_status"] == "bound_direct_distance" for r in checked)
    return checked, {"observation_rows": len(rows), "implemented_comparisons": bound,
        "unimplemented_or_unregistered": len(rows) - bound,
        "numerical_comparisons_within_tolerance": sum(r["within_source_tolerance"] is True for r in checked),
        "numerical_comparisons_outside_tolerance": sum(r["within_source_tolerance"] is False for r in checked),
        "reconstruction_admitted": False, "inventory_is_required_geometry_contract": False,
        "standalone_CAD_or_future_generator_gate": False,
        "admission_scope": "This inventory audit cannot grant reconstruction or physical approval; identities, angles, pressures and unsupported quantities are not all required geometric constraints.",
        "verdict": "failed_F2_binding_coverage_no_implemented_comparisons" if bound == 0
                   else "inventory_comparisons_exist_reconstruction_still_unqualified"}


def apply_mi_b_overlay(rows, root):
    path = root / MI_B_AMENDMENT
    amendment = json.loads(path.read_text())
    assert amendment["source_only_use_admitted"] and amendment["point_id"] == "B"
    assert amendment["combined_equal_opposed_span"] == 2 * amendment["source_only_half_width"]
    for row in rows:
        row.update({"source_amendment_path": "", "source_amendment_sha256": "",
            "effective_source_values": row["source_values"], "effective_half_width_mm": None,
            "source_amendment_scope": ""})
        if row["observation_id"] in ("MNL-FD964-MI-B-BOLT", "MNL-FD964-MI-B-FRAME"):
            assert row["source_file_sha256"] == amendment["source_sha256"]
            row.update(source_amendment_path=MI_B_AMENDMENT, source_amendment_sha256=sha(path),
                source_amendment_scope="Qualified documentary bolt-head width; no donor/F2 binding or new bare-frame contact equivalence")
            if row["observation_id"].endswith("-BOLT"):
                effective = json.loads(row["endpoint_or_state_definition"])["components"]
                effective["half_width"] = amendment["source_only_half_width"]
                effective["combined_equal_opposed_span"] = amendment["combined_equal_opposed_span"]
                row.update(effective_source_values=json.dumps(effective), effective_half_width_mm=effective["half_width"])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--model", type=Path)
    parser.add_argument("--bindings", type=Path, help="Independent, qualified feature comparison contract, if available")
    parser.add_argument("--scan-floor-report", type=Path, help="Separate source-indexed exterior-floor diagnostic, if available")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    model_path = args.model or root / "twins/964-chassis/sculpted-cell-f2-20261106/canonical-model.json"
    model = json.loads(model_path.read_text())
    paths = {name: root / "catalog/measurements" / (name + ".json") for name in REGISTRIES}
    rows = [r for name, path in paths.items() for r in rows_from_registry(path, REGISTRIES[name])]
    counts = dict(Counter(r["registry"] for r in rows))
    legacy = root / "twins/964-chassis/derived/964-floor-assembly.json"
    legacy_record = json.loads(legacy.read_text())
    rows.append({"observation_origin": "legacy_scan_envelope_hypothesis_not_OEM_dimension",
        "registry": "legacy_floor_assembly", "observation_id": "LEGACY-SCAN-FLOOR-Z-271P7",
        "source_id": "MESH-964-UNDERSIDE-2P13", "source_reference": "source/envelope.py; source/floor_assembly.py",
        "source_member": "", "source_file_sha256": "", "source_extraction_status": "unqualified_histogram_mode",
        "observation_kind": "aggregate_scan_height_candidate", "part_identity": "Unidentified central underside Z-mode, called floor by legacy script",
        "source_frame": "Tyre-contact/symmetry vehicle frame; structural datums not registered",
        "source_values": json.dumps([legacy_record["floor_pan_height_above_ground"]]),
        "source_value_text": "271.7 mm stored hypothesis; 200-bin Z histogram in X(-1400,-200), abs(Y)<450",
        "unit": "mm", "source_scalar_mm": None, "source_tolerance_mm": None,
        "comparison_kind": "requires_identified_floor_patch_and_uncertainty", "endpoint_or_state_definition": "No complete floor plane or interior surface acquired by this estimator"})
    rows = apply_mi_b_overlay(rows, root)
    bindings = json.loads(args.bindings.read_text()) if args.bindings else {}
    checked, result = coverage(rows, model, bindings)
    args.output.mkdir(parents=True, exist_ok=False)
    table = args.output / "traceability.csv"
    with table.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(checked[0]))
        writer.writeheader()
        for row in checked:
            writer.writerow({k: "null" if v is None else v for k, v in row.items()})
    params = root / "twins/964-chassis/sculpted-cell-f2-20261106/parameters.json"
    interfaces = root / "twins/964-chassis/interface-exploitation-20261030/contract.json"
    result.update({"classification": "completed_source_extraction_vs_model_binding_audit",
        "audit_source_sha256": sha(__file__), "model_sha256": sha(model_path),
        "parameters_sha256": sha(params), "registry_sha256": {k: sha(v) for k, v in paths.items()},
        "catalogue_observation_counts": counts, "catalogue_observation_total": sum(counts.values()),
        "inventory_scope": "Six named registries only; not exhaustive coverage of all Porsche data",
        "source_amendment": {"path": MI_B_AMENDMENT, "sha256": sha(root / MI_B_AMENDMENT),
            "effective_B_bolt_half_width_mm": json.loads((root / MI_B_AMENDMENT).read_text())["source_only_half_width"],
            "effective_combined_span_mm": json.loads((root / MI_B_AMENDMENT).read_text())["combined_equal_opposed_span"], "new_observations_added": 0},
        "legacy_aggregate_hypotheses": 1, "observation_counts_are_not_unique_geometric_dimensions": True,
        "body_datum_identity_rows_included": sum(r["registry"] == "MEAS-MANUAL-964-BODY-CONTROL" and
            r["observation_kind"] == "datum_point" for r in rows),
        "interface_observations_and_identities": {"observations": counts["MEAS-MANUAL-964-INTERFACE-SPANS-20261030"],
            "documentary_identities": len(json.loads(interfaces.read_text())["points"]),
            "contract_sha256": sha(interfaces), "duplicate_family_observations_are_not_new_geometry": True},
        "legacy_hypothesis_input_sha256": {str(p.relative_to(root)): sha(p) for p in [legacy,
            root / "twins/964-chassis/source/envelope.py", root / "twins/964-chassis/source/floor_assembly.py"]},
        "table": table.name, "table_sha256": sha(table), "source_feature_count_in_model": len(model.get("source_features_mm", {})),
        "source_extraction_validity": "Existing documentary transcriptions retain their own statuses; this audit does not re-verify raw pages or convert them into acquired surfaces.",
        "source_to_F2_transform": None, "CAD_and_media_success_grant_reconstruction_admission": False,
        "ground_contact_heights": {"front": "MNL-964SA-0001/0002: outer crossmember body bolt 165±10 mm, US175",
                                  "rear": "MNL-964SA-0024/0030: rear outer mount body-side 270±5 mm, US280"},
        "floor_geometry_limit": "Named contacts and the legacy 271.7 mm histogram do not fix a bare inner floor or a 65 mm floor box. New exterior-candidate patch evidence is a separate source observation, still unbound to F2.",
        "additional_scan_floor_diagnostic": {"report_sha256": sha(args.scan_floor_report),
            "status": "source_indexed_exterior_candidates_not_F2_binding",
            "model_value_mm": None, "delta_mm": None} if args.scan_floor_report else None,
        "physical_validation": False, "manufacturing_authorized": False})
    (args.output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"verdict": result["verdict"], "observations": len(rows), "bound": result["implemented_comparisons"]}))
    # Signal absent/failed actual comparisons, never a complete CAD release gate.
    return 1 if result["implemented_comparisons"] == 0 or result["numerical_comparisons_outside_tolerance"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
