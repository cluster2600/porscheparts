#!/usr/bin/env python3
"""Cross-reference reviewed forum leads without authoring engineering constraints."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FOLDER = Path(__file__).resolve().parent
INPUTS = {
    "leads": "twins/964-chassis/ddk-interface-bridge-20261104/reviewed-leads.json",
    "interfaces": "twins/964-chassis/interface-exploitation-20261030/contract.json",
    "regions": "twins/964-chassis/monocoque/scan-coverage-20261029/regions.json",
    "components": "twins/964-chassis/monocoque/component-review-20261029/review.json",
    "boundaries": "twins/964-chassis/monocoque/observed-boundaries-20261029/run.json",
}
POINTS = {f"P{i}" for i in (1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21)}
DISPOSITIONS = {
    "reported_dimension", "other_variant", "unidentified_variant_and_datum",
    "incompatible_context", "secondary_configuration_mass", "reported_configuration_mass",
}
FACT_KEYS = {"category", "subject", "value", "from", "to", "unit", "basis", "generationIds", "models"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def read_inputs(root=ROOT):
    return {name: json.loads((root / path).read_text()) for name, path in INPUTS.items()}


def build(inputs):
    data, interfaces = inputs["leads"], inputs["interfaces"]
    regions = {r["name"] for r in inputs["regions"]["regions"]}
    points = interfaces["points"]
    if set(points) != POINTS or interfaces["donor"] != {
        "generation": "964", "variant": "Carrera_2", "identity_basis": "user_reported",
        "model_year": None, "gearbox": None,
    }:
        raise ValueError("Baseline identities or donor changed; a new review is required")
    if any(interfaces["release_flags"].values()):
        raise ValueError("This bridge cannot inherit a release decision")
    for point in points.values():
        if any(point[k] is not None for k in ("xyz_mm", "axis", "mating_face", "selected_donor_span_mm")):
            raise ValueError("Baseline has selected geometry; review it independently")
    if inputs["boundaries"]["physical_segmentation_validated"] or inputs["boundaries"]["structural_analysis_admitted"]:
        raise ValueError("Scan admission changed; a new review is required")
    leads = data["leads"]
    seen = set()
    for lead in leads:
        if lead["id"] in seen:
            raise ValueError("Duplicate lead")
        seen.add(lead["id"])
        if lead["source_post"] not in data["sources"]:
            raise ValueError("Missing original source receipt")
        if not set(lead["candidate_point_context"]) <= POINTS or not set(lead["scan_search_context"]) <= regions:
            raise ValueError("Unknown interface or scan region")
        if lead["disposition"] not in DISPOSITIONS:
            raise ValueError("Unknown disposition; no automatic promotion")
        if any(lead[k] is not False for k in (
            "context_is_feature_identification", "accepted_as_cad_constraint", "accepted_as_load_input"
        )):
            raise ValueError("Forum context cannot authorize geometry or loads")
        facts = lead["facts"]
        if not set(facts) <= FACT_KEYS:
            raise ValueError("Unexpected fact field; raw content and member identities are excluded")
        for key in ("value", "from", "to"):
            if key in facts and (type(facts[key]) not in (int, float) or not math.isfinite(facts[key])):
                raise ValueError("Invalid numeric fact")
    crosswalk = []
    for name in sorted(points, key=lambda s: int(s[1:])):
        point = points[name]
        candidates = [lead for lead in leads if name in lead["candidate_point_context"]]
        crosswalk.append({
            "point": name, "designation": point["designation"],
            "documentary_span_options": point["span_options"],
            "ddk_context_leads": [r["id"] for r in candidates],
            "distinct_context_posts": sorted({r["source_post"] for r in candidates}),
            "ddk_exact_feature_matches": [], "accepted_xyz_mm": None,
            "accepted_axis": None, "accepted_mating_face": None,
            "selected_donor_span_mm": None,
        })
    scan_links = []
    for region in inputs["components"]["region_review"]:
        name = region["usd_prim"].rsplit("/", 1)[-1]
        if region["component_boundary_validated"] or region["functional_surface_fit_admitted"]:
            raise ValueError("Component admission changed; a new review is required")
        # Unselected context is preserved upstream; it is not an eighth search region.
        if name == "Context":
            continue
        scan_links.append({
            "region": name, "source_face_ids_sha256": region["source_face_ids_sha256"],
            "interpretation": region["interpretation"],
            "ddk_context_leads": [r["id"] for r in leads if name in r["scan_search_context"]],
            "confirmed_part_number": None, "functional_surface_fit_admitted": False,
        })
    if {r["region"] for r in scan_links} != regions:
        raise ValueError("Component review does not cover every scan search region")
    return {
        "classification": "documentary_crosswalk_not_cad_or_solver_input",
        "review_date": data["review_date"], "donor": interfaces["donor"],
        "coverage": {
            "selected_leads": len(leads),
            "distinct_original_posts": len({r["source_post"] for r in leads}),
            "manual_point_identities": len(crosswalk),
            "documentary_span_observations": sum(len(r["documentary_span_options"]) for r in crosswalk),
            "scan_search_regions": len(scan_links),
            "new_qualified_xyz": 0, "new_qualified_tunnel_surfaces": 0,
        },
        "independence_policy": "Several values from one post are not independent measurements; distinct posts are not necessarily independent either.",
        "interface_crosswalk": crosswalk, "scan_context": scan_links,
        "mass_policy": {
            "user_design_target_kg": 1200, "measured_vehicle_mass_kg": None,
            "accepted_component_masses": [], "centre_of_gravity_mm": None,
            "accepted_support_reactions_n": None,
            "note": "Do not sum alternative complete engines or combine whole-vehicle and component masses. Forum comparison tables are not load cases.",
        },
        "release_flags": {key: False for key in interfaces["release_flags"]},
    }


def crosswalk_csv(report):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["point", "designation", "span_mm", "pair_tolerance_mm", "model_year_group",
                     "ddk_context_leads", "exact_ddk_feature_match", "x_mm", "y_mm", "z_mm", "axis", "mating_face"])
    for row in report["interface_crosswalk"]:
        for span in row["documentary_span_options"]:
            writer.writerow([row["point"], row["designation"], span["span_mm"], span["pair_tolerance_mm"],
                             span["model_year_group"], ";".join(row["ddk_context_leads"]), "false", "", "", "", "", ""])
    return out.getvalue()


def verify_dataset(data, path):
    if digest(path) != data["dataset"]["sha256"]:
        raise ValueError("Private dataset differs from the reviewed revision")
    records = json.loads(path.read_text())["measurements"]
    tagged = [r for r in records if set(r.get("generationIds", [])) & {"964", "993"}]
    counts = {basis: sum(r["basis"] == basis for r in tagged) for basis in ("measured", "quoted", "reported")}
    if (len(records), len(tagged), counts) != (data["dataset"]["total_records"], data["dataset"]["records_tagged_964_or_993"], data["dataset"]["tagged_basis_counts"]):
        raise ValueError("Dataset coverage differs")
    by_id = {r["id"]: r for r in records}
    for lead in data["leads"]:
        original = by_id[lead["id"]]
        if {k: original[k] for k in FACT_KEYS if k in original} != lead["facts"]:
            raise ValueError("Selected fact differs from the source dataset")
        if str(original["post"]["postId"]) != lead["source_post"] or original["post"]["url"] != data["sources"][lead["source_post"]]["url"]:
            raise ValueError("Selected source link differs")


def outputs(root=ROOT):
    inputs = read_inputs(root)
    report = build(inputs)
    report["input_sha256"] = {path: digest(root / path) for path in INPUTS.values()}
    report["builder_sha256"] = digest(Path(__file__))
    return {"bridge.json": encoded(report), "interface-crosswalk.csv": crosswalk_csv(report)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dataset", type=Path, help="Optional private PorscheFanatics dataset; never copied")
    args = parser.parse_args()
    if args.dataset:
        verify_dataset(read_inputs()["leads"], args.dataset)
    generated = outputs()
    for name, content in generated.items():
        path = FOLDER / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise ValueError(f"Stale bridge output: {name}")
        else:
            path.write_text(content)
    print("DDK bridge checked: documentary context only; no geometry or load admission")


if __name__ == "__main__":
    main()
