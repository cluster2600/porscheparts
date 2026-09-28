#!/usr/bin/env python3
"""Generate conservative OpenUSD proxies for dimensioned catalogue entries.

The generated assets are documentary twins, not manufacturing geometry. A
component is eligible when its catalogue record marks the physical record as
complete and provides size, mass and material. A declared reference entry is
eligible when it provides a three-axis envelope; missing material remains an
explicit unresolved engineering input.

No physics schema, collision geometry or SimReady claim is authored here. The
source records do not provide the tolerances and full surfaces needed for those
claims.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "catalog" / "components"
PARTS = ROOT / "catalog" / "parts"
REFERENCE = ROOT / "catalog" / "reference"
OUTPUT = ROOT / "twins" / "catalogue-parts"
PORSCHEFANATICS_CONTEXT = OUTPUT / "evidence" / "porschefanatics-993-oem-context.json"

PLACEHOLDER_MATERIALS = {
    "",
    "a determiner",
    "non determine",
    "non déterminé",
    "unknown",
    "inconnue",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def meaningful_material(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = " ".join(value.strip().lower().replace("_", " ").split())
    if normalized in PLACEHOLDER_MATERIALS:
        return False
    return not any(marker in normalized for marker in ("a determiner", "à déterminer", "non determine"))


def parameter_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["parameter_id"]: item
        for item in record["physical"]["size_parameters"]
        if isinstance(item, dict) and isinstance(item.get("parameter_id"), str)
    }


def component_candidates() -> list[tuple[Path, dict[str, Any]]]:
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(COMPONENTS.glob("*.json")):
        record = load_json(path)
        physical = record.get("physical", {})
        material = physical.get("material", {})
        eligibility = record.get("eligibility", {})
        if not eligibility.get("complete_physical_record"):
            continue
        if not meaningful_material(material.get("family")) or not material.get("process"):
            continue
        if not physical.get("size_parameters") or not physical.get("mass"):
            continue
        parameters = parameter_map(record)
        if {"RIM_DIAMETER", "RIM_WIDTH", "CENTER_BORE"} <= parameters.keys():
            candidates.append((path, record))
    return candidates


def reference_candidates() -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, int]]:
    candidates: list[tuple[Path, dict[str, Any]]] = []
    dimensioned = 0
    unresolved_material = 0
    for path in sorted(REFERENCE.glob("*.json")):
        payload = load_json(path)
        for entry in payload.get("entries", []):
            if not isinstance(entry, dict) or entry.get("generation") != "993":
                continue
            dimensions = entry.get("dimensions_mm")
            if not (
                isinstance(dimensions, list)
                and len(dimensions) == 3
                and all(isinstance(value, (int, float)) and value > 0 for value in dimensions)
            ):
                continue
            dimensioned += 1
            if not meaningful_material(entry.get("material")):
                unresolved_material += 1
            candidates.append((path, entry))
    return candidates, {
        "dimensioned_reference_entries": dimensioned,
        "unresolved_material_entries": unresolved_material,
        "excluded_for_placeholder_material": 0,
    }


def part_by_oem_reference() -> dict[str, tuple[Path, dict[str, Any]]]:
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(PARTS.glob("*.json")):
        record = load_json(path)
        for reference in record.get("vehicle", {}).get("porsche_part_numbers", []):
            result[reference] = (path, record)
    return result


def porschefanatics_context() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = load_json(PORSCHEFANATICS_CONTEXT)
    records = {
        item["oem_reference"]: item
        for item in payload.get("records", [])
        if isinstance(item, dict) and isinstance(item.get("oem_reference"), str)
    }
    return payload, records


def slug(identifier: str) -> str:
    return identifier.lower().replace(".", "-").replace("_", "-")


def format_number(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if text not in {"", "-0"} else "0"


def tuple_text(values: tuple[float, float, float]) -> str:
    return "(" + ", ".join(format_number(value) for value in values) + ")"


def usd_header() -> str:
    return """#usda 1.0
(
    defaultPrim = "Twin"
    metersPerUnit = 0.001
    upAxis = "Z"
)

"""


def material_block(color: tuple[float, float, float], metallic: float, roughness: float) -> str:
    return f'''    def Scope "Looks"
    {{
        def Material "DocumentaryMaterial"
        {{
            token outputs:surface.connect = </Twin/Looks/DocumentaryMaterial/PreviewSurface.outputs:surface>

            def Shader "PreviewSurface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = {tuple_text(color)}
                float inputs:metallic = {format_number(metallic)}
                float inputs:roughness = {format_number(roughness)}
                token outputs:surface
            }}
        }}
    }}

'''


def mesh_block(
    points: list[tuple[float, float, float]],
    faces: list[list[int]],
    extent: tuple[tuple[float, float, float], tuple[float, float, float]],
) -> str:
    points_text = ",\n            ".join(tuple_text(point) for point in points)
    counts_text = ", ".join(str(len(face)) for face in faces)
    indices_text = ", ".join(str(index) for face in faces for index in face)
    return f'''    def Mesh "Geometry" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {{
        uniform bool doubleSided = true
        float3[] extent = [{tuple_text(extent[0])}, {tuple_text(extent[1])}]
        int[] faceVertexCounts = [{counts_text}]
        int[] faceVertexIndices = [{indices_text}]
        rel material:binding = </Twin/Looks/DocumentaryMaterial>
        point3f[] points = [
            {points_text}
        ]
        uniform token purpose = "proxy"
        uniform token subdivisionScheme = "none"
    }}
'''


def wheel_mesh(diameter_mm: float, width_mm: float, bore_mm: float, segments: int = 32):
    outer = diameter_mm / 2.0
    inner = bore_mm / 2.0
    half_width = width_mm / 2.0
    points: list[tuple[float, float, float]] = []
    for x, radius in ((-half_width, outer), (half_width, outer), (-half_width, inner), (half_width, inner)):
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            points.append((x, radius * math.cos(angle), radius * math.sin(angle)))

    outer_near, outer_far, inner_near, inner_far = (0, segments, 2 * segments, 3 * segments)
    faces: list[list[int]] = []
    for index in range(segments):
        following = (index + 1) % segments
        faces.extend(
            [
                [outer_near + index, outer_near + following, outer_far + following, outer_far + index],
                [inner_near + index, inner_far + index, inner_far + following, inner_near + following],
                [outer_near + index, inner_near + index, inner_near + following, outer_near + following],
                [outer_far + index, outer_far + following, inner_far + following, inner_far + index],
            ]
        )
    return points, faces, ((-half_width, -outer, -outer), (half_width, outer, outer))


def box_mesh(dimensions: list[float]):
    length, width, height = (float(value) for value in dimensions)
    x, y = length / 2.0, width / 2.0
    points = [
        (-x, -y, 0.0), (x, -y, 0.0), (x, y, 0.0), (-x, y, 0.0),
        (-x, -y, height), (x, -y, height), (x, y, height), (-x, y, height),
    ]
    faces = [
        [0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
        [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7],
    ]
    return points, faces, ((-x, -y, 0.0), (x, y, height))


def scad_header(identifier: str) -> str:
    return (
        "// Generated documentary F1 envelope proxy.\n"
        "// Not manufacturing geometry, not dimensionally validated, not SimReady.\n"
        f'proxy_id = "{identifier}";\n'
        '$fn = 96;\n\n'
    )


def wheel_scad_asset(identifier: str, diameter_mm: float, width_mm: float, bore_mm: float) -> str:
    return (
        scad_header(identifier)
        + f"rim_diameter_mm = {format_number(diameter_mm)};\n"
        + f"rim_width_mm = {format_number(width_mm)};\n"
        + f"centre_bore_mm = {format_number(bore_mm)};\n\n"
        + "rotate([0, 90, 0])\n"
        + "difference() {\n"
        + "    cylinder(h = rim_width_mm, d = rim_diameter_mm, center = true);\n"
        + "    cylinder(h = rim_width_mm + 2, d = centre_bore_mm, center = true);\n"
        + "}\n"
    )


def box_scad_asset(identifier: str, dimensions: list[float]) -> str:
    length, width, height = (float(value) for value in dimensions)
    return (
        scad_header(identifier)
        + f"length_mm = {format_number(length)};\n"
        + f"width_mm = {format_number(width)};\n"
        + f"height_mm = {format_number(height)};\n\n"
        + "translate([-length_mm / 2, -width_mm / 2, 0])\n"
        + "    cube([length_mm, width_mm, height_mm], center = false);\n"
    )


def usd_asset(
    points: list[tuple[float, float, float]],
    faces: list[list[int]],
    extent: tuple[tuple[float, float, float], tuple[float, float, float]],
    material_family: str | None,
) -> str:
    if material_family is None:
        color, metallic, roughness = (0.42, 0.44, 0.47), 0.0, 0.72
    elif "aluminium" in material_family.lower():
        color, metallic, roughness = (0.48, 0.50, 0.53), 0.85, 0.28
    else:
        color, metallic, roughness = (0.31, 0.34, 0.37), 0.90, 0.32
    return (
        usd_header()
        + 'def Xform "Twin" (\n    kind = "component"\n)\n{\n'
        + '    custom string documentationStatus = "F1_documentary_proxy_not_simready"\n'
        + '    custom string physicsAssignment = "intentionally_absent"\n\n'
        + material_block(color, metallic, roughness)
        + mesh_block(points, faces, extent)
        + "}\n"
    )


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def build_outputs() -> dict[Path, str]:
    outputs: dict[Path, str] = {}
    twin_records: list[dict[str, Any]] = []
    context_payload, context_by_reference = porschefanatics_context()

    for path, component in component_candidates():
        parameters = parameter_map(component)
        diameter = round(float(parameters["RIM_DIAMETER"]["value"]) * 25.4, 6)
        width = round(float(parameters["RIM_WIDTH"]["value"]) * 25.4, 6)
        bore = round(float(parameters["CENTER_BORE"]["value"]), 6)
        points, faces, extent = wheel_mesh(diameter, width, bore)
        identifier = component["component_id"]
        usd_path = OUTPUT / "usd" / f"{slug(identifier)}.usda"
        scad_path = OUTPUT / "cad" / f"{slug(identifier)}.scad"
        outputs[usd_path] = usd_asset(points, faces, extent, component["physical"]["material"]["family"])
        outputs[scad_path] = wheel_scad_asset(identifier, diameter, width, bore)
        twin_records.append(
            {
                "twin_id": f"TWIN-{identifier.removeprefix('COMP-')}",
                "subject": {
                    "kind": "catalog_component",
                    "id": identifier,
                    "record": relative(path),
                    "name": component["name"],
                },
                "fidelity": "F1_envelope",
                "representation": "annular_wheel_interface_proxy",
                "geometry": {
                    "file": relative(usd_path),
                    "editable_proxy_file": relative(scad_path),
                    "units": "mm",
                    "parameters": {
                        "rim_diameter_mm": diameter,
                        "rim_width_mm": width,
                        "centre_bore_mm": bore,
                    },
                    "accuracy_mm": component["geometry"]["interface_accuracy_mm"],
                    "source_master": component["geometry"]["master_file"],
                },
                "physical": {
                    "mass": component["physical"]["mass"],
                    "material": component["physical"]["material"],
                    "material_status": "manufacturer_sourced",
                },
                "provenance": {
                    "source_ids": [source["source_id"] for source in component["sources"]],
                    "porschefanatics_context": None,
                },
                "validation": {
                    "status": "geometry_generated_unvalidated",
                    "catalogue_application_documented": True,
                    "geometry_fit_validated": False,
                    "physics_assignment": "intentionally_absent",
                    "simready_status": "not_evaluated",
                    "safety_disposition": "wheel_part_blocked_from_release_pending_professional_engineering",
                    "known_limits": component["geometry"]["limitations"],
                },
            }
        )

    parts = part_by_oem_reference()
    reference_records, reference_stats = reference_candidates()
    for path, entry in reference_records:
        identifier = entry["entry_id"]
        dimensions = [float(value) for value in entry["dimensions_mm"]]
        points, faces, extent = box_mesh(dimensions)
        usd_path = OUTPUT / "usd" / f"{slug(identifier)}.usda"
        scad_path = OUTPUT / "cad" / f"{slug(identifier)}.scad"
        declared_material = entry.get("material")
        material_resolved = meaningful_material(declared_material)
        outputs[usd_path] = usd_asset(
            points,
            faces,
            extent,
            declared_material if material_resolved else None,
        )
        outputs[scad_path] = box_scad_asset(identifier, dimensions)
        oem_reference = entry.get("oem_reference")
        part_match = parts.get(oem_reference)
        part_path, part = part_match if part_match else (None, None)
        pf_record = context_by_reference.get(oem_reference)
        twin_records.append(
            {
                "twin_id": f"TWIN-{identifier}",
                "subject": {
                    "kind": "declared_reference_entry",
                    "id": identifier,
                    "record": relative(path),
                    "part_record": relative(part_path) if part_path else None,
                    "part_id": part.get("part_id") if part else None,
                    "oem_reference": oem_reference,
                    "name": entry["name"],
                },
                "fidelity": "F1_envelope",
                "representation": "declared_bounding_envelope",
                "geometry": {
                    "file": relative(usd_path),
                    "editable_proxy_file": relative(scad_path),
                    "units": "mm",
                    "parameters": {"bounding_box_mm": dimensions},
                    "accuracy_mm": None,
                    "source_master": None,
                },
                "physical": {
                    "mass": {
                        "value_kg": entry.get("mass_kg"),
                        "basis": "third_party_declared",
                        "source_id": entry["source_id"],
                    },
                    "material": {
                        "family": declared_material if material_resolved else None,
                        "grade": None,
                        "process": None,
                        "declared_label": declared_material,
                        "source_id": entry["source_id"],
                    },
                    "material_status": (
                        "inferred_not_measured" if material_resolved else "unresolved"
                    ),
                },
                "provenance": {
                    "source_ids": [entry["source_id"]],
                    "porschefanatics_context": pf_record,
                },
                "validation": {
                    "status": "geometry_generated_unvalidated",
                    "catalogue_application_documented": bool(pf_record and pf_record.get("pet_verified")),
                    "geometry_fit_validated": False,
                    "physics_assignment": "intentionally_absent",
                    "simready_status": "not_evaluated",
                    "safety_disposition": (
                        "safety_critical_blocked_from_release_pending_professional_engineering"
                        if part and part.get("classification", {}).get("safety_class") == "safety_critical"
                        else "not_assessed"
                    ),
                    "known_limits": (
                        [
                            "L'enveloppe 600 x 50 x 50 mm est une declaration vendeur arrondie, pas une metrologie de la piece.",
                            "L'acier est infere par recoupement de masse, volume apparent et photographies ; la nuance reste inconnue.",
                            "Le parallelepipede ne represente ni la lame incurvee, ni les bossages, ni les interfaces de fixation.",
                            "Aucune fabrication, simulation structurelle ou validation de montage n'est autorisee par ce proxy.",
                        ]
                        if identifier == "993-ENGINE-CARRIER-TURBO"
                        else [
                            "L'enveloppe est une declaration fournisseur de packaging ou de produit, pas une metrologie de surface.",
                            "Le parallelepipede ne represente ni la forme, ni les interfaces, ni les epaisseurs de la piece.",
                            "La matiere et le procede restent non resolus lorsqu'ils ne sont pas explicitement sources.",
                            "Aucune fabrication, simulation fonctionnelle ou validation de montage n'est autorisee par ce proxy.",
                        ]
                    ),
                },
            }
        )

    twin_records.sort(key=lambda item: item["twin_id"])
    index = {
        "$comment": (
            "Premiere tranche de jumeaux documentaires pour les pieces et produits disposant "
            "d'un encombrement declare. Les USD sont des proxys F1, pas des geometries de fabrication."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "eligibility_policy": {
            "components": "complete_physical_record avec taille, masse, matiere et procede sources",
            "declared_references": (
                "enveloppe XYZ positive ; toute matiere absente reste unresolved et une matiere inferee reste signalee"
            ),
        },
        "porschefanatics": {
            "evidence_file": relative(PORSCHEFANATICS_CONTEXT),
            "source_repository_commit": context_payload["source_repository_commit"],
            "catalogue_observations": context_payload["catalogue_observations"],
            "role": "confirmation d'identite, de groupe PET, de position et d'application ; aucune cote CAO deduite",
        },
        "summary": {
            "generated_twins": len(twin_records),
            "component_twins": sum(item["subject"]["kind"] == "catalog_component" for item in twin_records),
            "declared_reference_twins": sum(
                item["subject"]["kind"] == "declared_reference_entry" for item in twin_records
            ),
            "editable_proxy_sources": len(twin_records),
            **reference_stats,
        },
        "twins": twin_records,
    }
    outputs[OUTPUT / "index.json"] = json.dumps(index, ensure_ascii=False, indent=2) + "\n"
    return outputs


def run(write: bool) -> int:
    expected = build_outputs()
    failures: list[str] = []
    for path, content in expected.items():
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"wrote {relative(path)}")
        elif not path.is_file():
            failures.append(f"missing generated file: {relative(path)}")
        elif path.read_text(encoding="utf-8") != content:
            failures.append(f"stale generated file: {relative(path)}")

    expected_by_suffix = {
        suffix: {path.resolve() for path in expected if path.suffix == suffix}
        for suffix in (".usda", ".scad")
    }
    for directory, suffix in ((OUTPUT / "usd", ".usda"), (OUTPUT / "cad", ".scad")):
        if directory.is_dir():
            for path in directory.glob(f"*{suffix}"):
                if path.resolve() not in expected_by_suffix[suffix]:
                    failures.append(f"unexpected generated file: {relative(path)}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    if not write:
        print(
            f"catalogue twins: {len(expected_by_suffix['.usda'])} USD assets, "
            f"{len(expected_by_suffix['.scad'])} editable proxies and index are current"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the generated USD assets and index")
    mode.add_argument("--check", action="store_true", help="verify checked-in outputs are current")
    args = parser.parse_args(argv)
    return run(write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
