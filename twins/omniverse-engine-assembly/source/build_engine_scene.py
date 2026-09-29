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


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("status") != "research_layout_not_fitment":
        raise ValueError("manifest status must be research_layout_not_fitment")
    if data.get("units") != "mm" or data.get("up_axis") != "Z":
        raise ValueError("the scene contract requires millimetres and Z-up")
    if not data.get("coordinate_frame", {}).get("layout_status"):
        raise ValueError("coordinate_frame.layout_status must document the layout basis")
    return data


def check_references(manifest: dict[str, Any], manifest_path: Path, out_path: Path) -> list[str]:
    """Return a list of 'layer-relative -> repo-relative' pairs for real assets,
    failing closed when a referenced asset file is missing."""
    repo_root = manifest_path.resolve().parents[2]
    pairs: list[str] = []
    for zone in manifest["zones"]:
        for item in zone["items"]:
            if item["asset_kind"] != "real_asset_reference":
                continue
            repo_relative = Path(item["usd"])
            if not (repo_root / repo_relative).is_file():
                raise FileNotFoundError(
                    f"manifest references missing asset {item['id']}: {repo_root / repo_relative}"
                )
            rel = (repo_root / repo_relative).resolve().relative_to(out_path.parent.resolve())
            pairs.append((item, "../" * 0 + rel.as_posix()))
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
    size = item["proxy"]["size_mm"]
    hx, hy, hz = (s / 2.0 for s in size)
    color = item["proxy"]["color"]
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


def build(manifest: dict[str, Any], manifest_path: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame = manifest["coordinate_frame"]
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
    print(f"wrote {path} ({len(manifest['zones'])} zones, {prims} item prims)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
