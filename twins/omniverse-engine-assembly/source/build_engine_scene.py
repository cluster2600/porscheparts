#!/usr/bin/env python3
"""Generate the engine-level Omniverse research scene (ASCII .usda) from the
engine assembly manifest.

Stdlib only. Deterministic: identical manifest and asset set produce byte-identical
USDA. No pxr is used; the output is validated by structure and by the repository
validators (see twins/omniverse-engine-assembly/README.md).

The manifest (assembly-engine-v1.json) is the single source of truth: every prim
in the scene is either a real reference to an existing USD asset or an honestly
labelled box proxy. Positions are engine-local layout hypotheses, never fitment.

Usage:
    python3 twins/omniverse-engine-assembly/source/build_engine_scene.py
    python3 twins/omniverse-engine-assembly/source/build_engine_scene.py \
        --manifest path/to/manifest.json --out path/to/scene.usda
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE.parent / "assembly-engine-v1.json"

CUBE_FACES = [0, 3, 2, 1, 4, 5, 6, 7, 0, 1, 5, 4, 1, 2, 6, 5, 2, 3, 7, 6, 3, 0, 4, 7]

PRIM_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def fmt(v: float) -> str:
    """Deterministic fixed-point formatting with trailing zeros removed."""
    s = f"{float(v):.3f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def vec3(values: list[float]) -> str:
    return "(" + ", ".join(fmt(v) for v in values) + ")"


def validate_manifest(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    """Contract checks for the whole-engine manifest (engine_v1 schema),
    shared by the builder and the stdlib scene validator."""
    errors: list[str] = []
    if manifest.get("status") != "research_layout_not_fitment":
        errors.append("manifest status must be research_layout_not_fitment")
    if manifest.get("units") != "mm" or manifest.get("up_axis") != "Z":
        errors.append("the engine scene contract requires millimetres and Z-up")
    if not manifest.get("coordinate_frame", {}).get("layout_status"):
        errors.append("coordinate_frame.layout_status must document the layout basis")
    coverage = manifest.get("bom_coverage", {})
    declared = coverage.get("bom_lines_unrepresented")
    if not declared:
        errors.append("bom_coverage.bom_lines_unrepresented must be declared")
    if not coverage.get("unrepresentation_reasons"):
        errors.append("bom_coverage.unrepresentation_reasons must justify each unrepresented line")
    if not manifest.get("limitations"):
        errors.append("limitations must be explicit")
    seen_prims: set[tuple[str, str]] = set()
    covered: set[str] = set()
    for zone in manifest.get("zones", []):
        if not zone.get("coverage"):
            errors.append(f"zone {zone.get('zone_id')} lacks a coverage statement")
        if not PRIM_NAME.match(zone["prim"]):
            errors.append(f"invalid zone prim name: {zone['prim']}")
        for item in zone["items"]:
            if not PRIM_NAME.match(item["prim"]):
                errors.append(f"invalid item prim name: {item['prim']}")
            key = (zone["prim"], item["prim"])
            if key in seen_prims:
                errors.append(f"duplicate prim {zone['prim']}/{item['prim']}")
            seen_prims.add(key)
            kind = item["asset_kind"]
            if kind == "real_asset_reference":
                usd = item.get("usd")
                if not usd:
                    errors.append(f"{item['id']}: real_asset_reference without usd path")
                elif not (manifest_path.resolve().parents[2] / usd).is_file():
                    errors.append(f"{item['id']}: referenced asset missing: {usd}")
            elif kind in ("box_proxy", "envelope_unknown"):
                if not item.get("size_mm"):
                    errors.append(f"{item['id']}: proxy/marker without size_mm")
            else:
                errors.append(f"{item['id']}: unknown asset_kind {kind}")
            if not item.get("bom_lines"):
                errors.append(f"{item['id']}: no bom_lines link")
            if not item.get("source_citation"):
                errors.append(f"{item['id']}: no source_citation")
            if not item.get("positionStatus", item.get("position_mm")):
                errors.append(f"{item['id']}: no position")
            covered.update(item["bom_lines"])
    repo_root = manifest_path.resolve().parents[2]
    bom_source = repo_root / manifest["bom_source"]
    if not bom_source.is_file():
        errors.append(f"BOM source missing: {bom_source}")
    else:
        bom = json.loads(bom_source.read_text(encoding="utf-8"))
        bom_ids = {part["bom_id_local"] for part in bom["parts"]}
        undeclared = sorted(covered - bom_ids)
        if undeclared:
            errors.append(f"prim bom_lines not in BOM: {undeclared}")
        unrepresented = sorted(bom_ids - covered)
        if set(unrepresented) != set(declared or []):
            errors.append(
                "bom_coverage mismatch: BOM lines missing a prim but not declared: "
                f"{sorted(set(unrepresented) - set(declared or []))}; declared but represented: "
                f"{sorted(set(declared or []) - set(unrepresented))}"
            )
        missing_reasons = sorted(set(declared or []) - set(coverage["unrepresentation_reasons"]))
        if missing_reasons:
            errors.append(f"unrepresented lines without reasons: {missing_reasons}")
    return {"passed": not errors, "errors": errors}


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("status") != "research_layout_not_fitment":
        raise ValueError("manifest status must be research_layout_not_fitment")
    if data.get("units") != "mm" or data.get("up_axis") != "Z":
        raise ValueError("the scene contract requires millimetres and Z-up")
    if not data.get("coordinate_frame", {}).get("layout_status"):
        raise ValueError("coordinate_frame.layout_status must document the layout basis")
    if not data.get("bom_coverage", {}).get("bom_lines_unrepresented"):
        raise ValueError(
            "bom_coverage.bom_lines_unrepresented must declare every BOM line with no scene prim"
        )
    return data


def layer_relative(repo_root: Path, out_dir: Path, usd_dir: Path, repo_relative: Path) -> str:
    """POSIX asset path for the references arc, computed lexically (never via
    .resolve()) so output is deterministic across cwd and symlink layouts.

    When the scene is built into its canonical directory (repo_root/manifest
    'usd' directory) the reference is relative to that directory, giving the
    version-stable scene. A build to any other --out directory (a validation
    copy in /tmp, for example) uses the path that resolves from the canonical
    location, so a render package can carry the layer beside the versioned
    scene unchanged."""
    target = repo_root / repo_relative
    canonical_dir = repo_root / usd_dir
    if out_dir == canonical_dir:
        return os.path.relpath(target, canonical_dir).replace(os.sep, "/")
    return os.path.relpath(target, out_dir).replace(os.sep, "/")


def check_references(manifest: dict[str, Any], manifest_path: Path, out_path: Path) -> list[tuple[dict[str, Any], str]]:
    """Return a list of (item, layer-relative asset path) pairs for real assets,
    failing closed when a referenced asset file is missing."""
    repo_root = manifest_path.parents[2]
    usd_dir = Path(manifest["usd"]).parent
    pairs: list[tuple[dict[str, Any], str]] = []
    for zone in manifest["zones"]:
        for item in zone["items"]:
            if item["asset_kind"] != "real_asset_reference":
                continue
            repo_relative = Path(item["usd"])
            if not (repo_root / repo_relative).is_file():
                raise FileNotFoundError(
                    f"manifest references missing asset {item['id']}: {repo_root / repo_relative}"
                )
            pairs.append((item, layer_relative(repo_root, out_path.parent, usd_dir, repo_relative)))
    return pairs


def attr_lines(item: dict[str, Any], zone: dict[str, Any], indent: str) -> list[str]:
    lines = [
        f'{indent}custom string[] m64:bomLines = ["' + '", "'.join(item["bom_lines"]) + '"]',
        f'{indent}custom string m64:fidelity = "{item["fidelity"]}"',
        f'{indent}custom string m64:assetKind = "{item["asset_kind"]}"',
        f'{indent}custom string m64:envelopeStatus = "{item["envelope_status"]}"',
        f'{indent}custom string m64:positionStatus = "layout-hypothesis-engine-local"',
        f'{indent}custom string m64:zone = "{zone["zone_id"]}"',
    ]
    citation = item.get("source_citation")
    if citation:
        lines.append(f'{indent}custom string m64:sourceCitation = "{citation}"')
    if "redesign_interest" in item:
        lines.append(f'{indent}custom string m64:redesignInterest = "{item["redesign_interest"]}"')
    note = item.get("note")
    if note:
        lines.append(f'{indent}custom string m64:note = "{note}"')
    return lines


def cube_mesh(item: dict[str, Any], zone: dict[str, Any], indent: str) -> list[str]:
    size = item["size_mm"]
    hx, hy, hz = (s / 2.0 for s in size)
    color = zone["color"]
    pts = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    ]
    lines = [
        f"{indent}def Mesh \"ProxyBox\"",
        f"{indent}{{",
        f"{indent}    uniform bool doubleSided = true",
        f"{indent}    float3[] extent = [({fmt(-hx)}, {fmt(-hy)}, {fmt(-hz)}), ({fmt(hx)}, {fmt(hy)}, {fmt(hz)})]",
        f"{indent}    int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]",
        f"{indent}    int[] faceVertexIndices = [{', '.join(str(i) for i in CUBE_FACES)}]",
        f"{indent}    color3f[] primvars:displayColor = [("
        + ", ".join(fmt(c / 255.0) for c in color)
        + ")] (interp = \"constant\")",
        f"{indent}    uniform token purpose = \"proxy\"",
        f"{indent}    uniform token subdivisionScheme = \"none\"",
        f"{indent}    point3f[] points = [",
    ]
    for p in pts:
        lines.append(f"{indent}        {vec3(list(p))},")
    lines[-1] = lines[-1].rstrip(",")
    lines.append(f"{indent}    ]")
    lines.append(f"{indent}}}")
    return lines


def check_coverage(manifest: dict[str, Any], manifest_path: Path) -> list[str]:
    """Coverage gate reused from the shared manifest contract check."""
    return validate_manifest(manifest, manifest_path)["errors"]


def build(manifest: dict[str, Any], manifest_path: Path, out_path: Path) -> Path:
    coverage_errors = check_coverage(manifest, manifest_path)
    if coverage_errors:
        raise ValueError("; ".join(coverage_errors))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame = manifest["coordinate_frame"]
    coverage = manifest["bom_coverage"]
    doc = (
        "M64/60 whole-engine research layout. Status: research layout, not fitment. "
        "Every prim is a real documented asset reference or a labelled box proxy. "
        "Positions are engine-local layout hypotheses, not measured or fitted positions. "
        "See " + manifest_path.name + " for BOM line references and citations."
    )
    out: list[str] = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "EngineAssembly"',
        "    metersPerUnit = 0.001",
        '    upAxis = "Z"',
        f'    doc = "{doc}"',
        ")",
        "",
        'def Xform "EngineAssembly" (',
        '    kind = "assembly"',
        f'    custom string m64:status = "{manifest["status"]}"',
        f'    custom string m64:bomSource = "{manifest["bom_source"]}"',
        f'    custom string m64:coordinateFrame = "{frame["description"]}"',
        f'    custom string m64:layoutStatus = "{frame["layout_status"]}"',
        '    custom string[] m64:bomLinesUnrepresented = [',
    ]
    for i, line in enumerate(coverage["bom_lines_unrepresented"]):
        comma = "," if i < len(coverage["bom_lines_unrepresented"]) - 1 else ""
        out.append(f'        "{line}"{comma}')
    out += [
        "    ]",
        f'    custom string m64:bomCoverageUnrepresentedReasons = {json.dumps(json.dumps(coverage["unrepresentation_reasons"]))}',
        "    custom string[] m64:limitations = [",
    ]
    for i, lim in enumerate(manifest["limitations"]):
        comma = "," if i < len(manifest["limitations"]) - 1 else ""
        out.append(f'        "{lim}"{comma}')
    out += ["    ]", ")", "{"]

    pairs = {id(item): rel for item, rel in check_references(manifest, manifest_path, out_path)}

    for zone in manifest["zones"]:
        zone_prim = zone["prim"]
        if not PRIM_NAME.match(zone_prim):
            raise ValueError(f"invalid zone prim name: {zone_prim}")
        out += [
            f'    def Scope "{zone_prim}" (',
            '        kind = "group"',
            f'        custom string m64:zoneId = "{zone["zone_id"]}"',
            f'        custom string m64:zoneCoverage = "{zone["coverage"]}"',
            f'        custom string m64:zoneLabel = "{zone["label"]}"',
            "    )",
            "    {",
        ]
        for item in zone["items"]:
            prim = item["prim"]
            if not PRIM_NAME.match(prim):
                raise ValueError(f"invalid item prim name: {prim}")
            meta = attr_lines(item, zone, "        ")
            if item["asset_kind"] == "real_asset_reference":
                meta.append(f'        references = @{pairs[id(item)]}@')
            out.append(f'    def Xform "{prim}" (')
            out += meta
            out.append("    )")
            out.append("    {")
            out.append(f'        double3 xformOp:translate = {vec3(item["position_mm"])}')
            out.append('        uniform token[] xformOpOrder = ["xformOp:translate"]')
            if item["asset_kind"] != "real_asset_reference":
                out += cube_mesh(item, zone, "        ")
            out.append("    }")
            out.append("")
        out.append("    }")
        out.append("")
    out.append("}")
    out.append("")
    out_path.write_text("\n".join(out), encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_MANIFEST.parent / "usd" / "993-engine-assembly-v1.usda",
    )
    args = parser.parse_args()
    manifest = load_manifest(args.manifest.resolve())
    path = build(manifest, args.manifest.resolve(), args.out.resolve())
    prims = sum(len(z["items"]) for z in manifest["zones"])
    bom_source = args.manifest.resolve().parents[2] / manifest["bom_source"]  # repo-root-relative
    bom_parts = json.loads(bom_source.read_text(encoding="utf-8"))["parts"]
    covered = set()
    for z in manifest["zones"]:
        for item in z["items"]:
            covered.update(item["bom_lines"])
    print(
        f"wrote {path} ({len(manifest['zones'])} zones, {prims} item prims; "
        f"BOM coverage: {len(covered & {p['bom_id_local'] for p in bom_parts})}/{len(bom_parts)} "
        f"lines represented, {len(manifest['bom_coverage']['bom_lines_unrepresented'])} "
        "declared unrepresented)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
