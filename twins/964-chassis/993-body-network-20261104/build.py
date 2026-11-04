#!/usr/bin/env python3
"""Check documentary 993 constraints without producing vehicle hardpoints."""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FLOOR = ROOT / "catalog/measurements/MEAS-MANUAL-993-FLOOR-CONTROL-20261104.json"
BODY = ROOT / "catalog/measurements/MEAS-MANUAL-993-BODY-DRAWING-20261104.json"
IDENTITIES = HERE.parent / "993-body-dimensions-20261104/contract.json"
OLD = ROOT / "catalog/measurements/MEAS-MANUAL-964-INTERFACE-SPANS-20261030.json"
SOURCE = "SRC-PORSCHE-993-BODY-DIMENSIONS-PREVIEW"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def dimensions(record):
    if record.get("record_kind") != "documented_specification" or record.get("source_id") != SOURCE:
        raise ValueError("Expected the reviewed documentary preview source")
    result = {}
    for row in record["declared_values"]:
        detail = row["details"]
        value, tolerance = detail["nominal_mm"], detail["span_tolerance_mm"]
        expected = [value] if tolerance is None else [value, tolerance]
        if not number(value) or value <= 0 or (
            tolerance is not None and (not number(tolerance) or not 0 <= tolerance < value)
        ):
            raise ValueError("Invalid scalar or printed tolerance")
        if row["numeric_values"] != expected or row["unit"] != "mm":
            raise ValueError("Scalar detail disagrees with its source transcription")
        if row["extraction_status"] != "manually_checked" or row["source_id"] != SOURCE:
            raise ValueError("Unreviewed source cannot enter this check")
        if detail["generation"] != "993" or len(detail["endpoint_ids"]) != 2 or any(
            not endpoint.startswith("993:") for endpoint in detail["endpoint_ids"]
        ):
            raise ValueError("Generation-qualified 993 endpoints are required")
        if detail["kind"] == "cross_diagonal":
            projected = row["value_id"].endswith("-HORIZONTAL")
            if detail["measurement_basis"] != ("horizontal_projection" if projected else "direct_distance") or detail["bracketed_in_source"] != projected:
                raise ValueError("Direct and projected observations must remain distinct")
        elif detail["kind"] == "longitudinal_distance":
            if detail["measurement_basis"] != "drawing_longitudinal_projection":
                raise ValueError("A drawing station requires longitudinal arrow evidence")
        elif detail["kind"] == "transverse_pair_span":
            if detail["endpoint_ids"][0] != detail["endpoint_ids"][1]:
                raise ValueError("A transverse pair must retain one generation-qualified identity")
        else:
            raise ValueError("Unsupported documentary constraint kind")
        if detail["functional_geometry_admitted"] or detail["donor_applicability_verified"]:
            raise ValueError("Documentary inputs do not establish donor geometry")
        if row["value_id"] in result:
            raise ValueError("Duplicate source observation")
        result[row["value_id"]] = row
    return result


def implied_height(direct, direct_tol, projected, projected_tol):
    """Unsigned difference only, conditional on identical endpoint/projection definitions."""
    if any(not number(v) for v in (direct, projected)) or not 0 <= projected <= direct:
        raise ValueError("Inconsistent direct/projected lengths")
    if any(t is not None and (not number(t) or t < 0) for t in (direct_tol, projected_tol)):
        raise ValueError("Invalid tolerance")
    if direct_tol is None or projected_tol is None:
        bounds = None
    else:
        if direct_tol > direct or projected_tol > projected:
            raise ValueError("Tolerance crosses a negative length")
        bounds = [math.sqrt(max(0, (direct-direct_tol)**2 - (projected+projected_tol)**2)),
                  math.sqrt((direct+direct_tol)**2 - (projected-projected_tol)**2)]
    return {"nominal_abs_delta_z_mm": math.sqrt(direct**2-projected**2),
            "worst_case_feasible_interval_mm": bounds, "height_sign": None,
            "absolute_z_mm": None, "accepted_coordinate_uncertainty_mm": None}


def calculate(floor, body, identities, old):
    f, b = dimensions(floor), dimensions(body)
    def fv(row, basis="DIRECT"):
        return f[f"MNL-993FC-{row}-{basis}"]["numeric_values"]
    def bv(key):
        return b[f"MNL-993BD-{key}"]["details"]["nominal_mm"]
    def bt(key):
        return b[f"MNL-993BD-{key}"]["details"]["span_tolerance_mm"]

    heights = {}
    for label in ("N", "P", "R", "S", "T", "U"):
        direct, dt = fv(label)
        horizontal, ht = fv(label, "HORIZONTAL")
        heights[label] = implied_height(direct, dt, horizontal, ht)
        heights[label]["input_value_ids"] = [f"MNL-993FC-{label}-DIRECT", f"MNL-993FC-{label}-HORIZONTAL"]

    # This independent equation compares the drawing's longitudinal separation
    # with the floor table's horizontal diagonal. Symmetry is an explicit assumption.
    dx, dx_tol = bv("P13-P14"), bt("P13-P14")
    w13, t13 = fv("I")
    w14, t14 = fv("K")
    dy, dy_tol = (w13+w14)/2, (t13+t14)/2
    predicted = math.hypot(dx, dy)
    interval = [math.hypot(dx-dx_tol, dy-dy_tol), math.hypot(dx+dx_tol, dy+dy_tol)]
    horizontal, horizontal_tol = fv("S", "HORIZONTAL")
    direct, _ = fv("S")
    wrong_dx = math.sqrt(direct**2-dy**2)
    closure = {
        "input_value_ids": ["MNL-993BD-P13-P14", "MNL-993FC-I-DIRECT",
                            "MNL-993FC-K-DIRECT", "MNL-993FC-S-HORIZONTAL"],
        "assumptions": ["Pairs share a symmetry midplane in the drawing",
                        "Each left/right pair has equal height",
                        "S joins opposite-side P13/P14 centres as drawn"],
        "equation": "horizontal_S = hypot(P13_P14_longitudinal, (P13_span + P14_span)/2)",
        "predicted_horizontal_mm": predicted, "published_horizontal_mm": horizontal,
        "nominal_residual_mm": predicted-horizontal,
        "predicted_worst_case_interval_mm": interval,
        "published_interval_mm": [horizontal-horizontal_tol, horizontal+horizontal_tol],
        "intervals_overlap": max(interval[0], horizontal-horizontal_tol) <= min(interval[1], horizontal+horizontal_tol),
        "misinterpretation_example": {
            "assumption": "Incorrectly treating direct S as a horizontal diagonal",
            "implied_longitudinal_mm": wrong_dx,
            "difference_from_published_longitudinal_mm": wrong_dx-dx,
            "admitted": False},
        "meaning": "Internal documentary consistency only; not independent metrology or fitment"}

    def station(nominal, terms):
        tolerances = [bt(key) for key in terms]
        half = None if any(t is None for t in tolerances) else sum(tolerances)
        return {"drawing_station_mm": nominal, "worst_case_half_interval_mm": half,
                "input_value_ids": ["MNL-993BD-"+key for key in terms],
                "vehicle_xyz_mm": None, "axis": None, "mating_face": None}
    p17 = bv("P1-P17")-bv("P1-ZERO")
    p13 = p17-bv("P13-P17")
    stations = {
        "993:P1": station(-bv("P1-ZERO"), ["P1-ZERO"]),
        "993:P3": station(-bv("P3-ZERO"), ["P3-ZERO"]),
        "993:P5": station(bv("ZERO-P5"), ["ZERO-P5"]),
        "993:P17": station(p17, ["P1-P17", "P1-ZERO"]),
        "993:P13": station(p13, ["P1-P17", "P1-ZERO", "P13-P17"]),
        "993:P14": station(p13+bv("P13-P14"), ["P1-P17", "P1-ZERO", "P13-P17", "P13-P14"])}

    point_map = {p["id"]: p for p in identities["points"]}
    old_map = {v["value_id"]: v for v in old["declared_values"]}
    inventory = []
    for row in list(f.values())+list(b.values()):
        if row["details"]["kind"] != "transverse_pair_span":
            continue
        identity = point_map[row["details"]["endpoint_ids"][0]]
        candidate_values = [old_map[key]["numeric_values"] for key in identity["candidate_964_value_ids"]]
        inventory.append({"id": identity["id"], "value_id": row["value_id"],
                          "span_mm": row["numeric_values"][0],
                          "printed_half_tolerance_mm": row["numeric_values"][1],
                          "semantic_964_candidate": identity["semantic_964_candidate"],
                          "candidate_964_value_ids": identity["candidate_964_value_ids"],
                          "same_nominal_and_tolerance": row["numeric_values"] in candidate_values,
                          "geometry_interchangeability_verified": False})
    return {
        "classification": "documentary_constraints_not_vehicle_geometry",
        "input_admissibility": "Reviewed scalar data admitted for documentary checks only",
        "counts": {"floor_observations": len(f), "additional_body_observations": len(b),
                   "combined_scalar_observations": len(f)+len(b), "defined_point_identities": 19,
                   "point_identities_with_pair_spans": len(inventory),
                   "matching_964_candidate_pairs": sum(x["same_nominal_and_tolerance"] for x in inventory),
                   "new_validated_xyz_points": 0},
        "rear_subframe_projection_check": closure,
        "conditional_height_differences": heights,
        "drawing_station_convention": "Positive rearward from the printed zero line; no surveyed origin or vehicle-frame transform. P4 is not assigned station zero.",
        "drawing_stations": stations,
        "station_interval_policy": "Worst-case sums of printed limits, not confidence intervals. Derived stations share inputs; their marginal intervals must not be treated as independent measurements.",
        "pair_inventory": sorted(inventory, key=lambda p: int(p["id"].split("P")[1])),
        "unresolved": {"993:P7_span_mm": None, "993:P23_identity": None,
                       "D215_tolerance_mm": None, "donor_model_year": None, "donor_gearbox": None,
                       "reason_P7": "Digits remain ambiguous in the enlarged preview",
                       "tunnel_interior_surface": None},
        "release_flags": {"functional_geometry": False, "torsion_or_strength_validated": False,
                          "manufacturing_validated": False, "omniverse_validated_twin": False}}


def build():
    inputs = [FLOOR, BODY, IDENTITIES, OLD]
    result = calculate(*(json.loads(p.read_text()) for p in inputs))
    result["inputs"] = [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in inputs]
    result["builder_sha256"] = digest(Path(__file__))
    # Suppress platform-level last-bit variation without implying metrology at
    # this precision. The source's millimetre tolerance bands remain authoritative.
    def rounded(value):
        if isinstance(value, float):
            return round(value, 9)
        if isinstance(value, list):
            return [rounded(item) for item in value]
        if isinstance(value, dict):
            return {key: rounded(item) for key, item in value.items()}
        return value
    return rounded(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    path = HERE / "analysis.json"
    if args.check:
        if json.loads(path.read_text()) != result:
            raise SystemExit("Documentary analysis is stale")
        print("993 documentary analysis matches its reviewed inputs; no vehicle coordinates admitted")
    else:
        path.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
        print("Wrote documentary consistency analysis; functional geometry remains unverified")


if __name__ == "__main__":
    main()
