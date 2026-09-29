#!/usr/bin/env python3
"""Validate the whole-engine v1 scene and manifest without OpenUSD.

Covers what the pxr validator cannot check on a machine without OpenUSD:
manifest schema, BOM-line coverage against twins/m64-engine-system/bom/
m64-bom-v1.json, the evidence-state attributes required on every item prim,
the presence of every referenced asset, and structural balance of the
generated USDA. Also runs in --structure-only mode inside the SimReady image
after USD generation.

Evidence limits: passing these checks means the scene is complete, honest
metadata and loadable structure (layout-grade F0/F1). It never means any part
is dimensionally correct, fitted, tested, safe, released or manufacturing-ready.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_engine_scene as bes  # noqa: E402

REQUIRED_ITEM_ATTRS = [
    "m64:bomLines",
    "m64:fidelity",
    "m64:assetKind",
    "m64:envelopeStatus",
    "m64:positionStatus",
    "m64:zone",
    "m64:sourceCitation",
]

BANNED_CLAIMS = re.compile(
    r"\b(dimensionally correct|fitted|tested|safe|released|manufacturing-ready)\b",
    re.IGNORECASE,
)


def check_usda_structure(text: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.append({"name": "usda_header", "passed": text.startswith("#usda 1.0")})
    checks.append(
        {
            "name": "usda_mm_z_up",
            "passed": "metersPerUnit = 0.001" in text and 'upAxis = "Z"' in text,
        }
    )
    checks.append(
        {"name": "usda_default_prim", "passed": 'defaultPrim = "EngineAssembly"' in text}
    )
    opens = text.count("{")
    closes = text.count("}")
    checks.append(
        {"name": "usda_braces_balanced", "passed": opens == closes, "opens": opens, "closes": closes}
    )
    return checks


def check_evidence_attributes(text: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    item_blocks = re.findall(
        r'def Xform "([A-Za-z_][A-Za-z0-9_]*)" \(([^()]*)\)', text, re.DOTALL
    )
    bad_attrs: list[str] = []
    real_refs = 0
    for name, body in item_blocks:
        if name == "EngineAssembly":
            continue
        missing = [attr for attr in REQUIRED_ITEM_ATTRS if attr not in body]
        if missing:
            bad_attrs.append(f"{name}: missing {missing}")
        if "m64:assetKind = \"real_asset_reference\"" in body:
            real_refs += 1
            if "references = @" not in body:
                bad_attrs.append(f"{name}: real_asset_reference without references arc")
    checks.append(
        {"name": "every_item_has_evidence_attributes", "passed": not bad_attrs, "issues": bad_attrs}
    )
    checks.append(
        {
            "name": "real_references_present",
            "passed": real_refs > 0,
            "real_asset_prims": real_refs,
        }
    )
    return checks


def check_no_overclaims(text: str) -> list[dict[str, Any]]:
    hits = [line.strip() for line in text.splitlines() if BANNED_CLAIMS.search(line)]
    # The scene is only allowed to state the denial explicitly.
    offenders = [h for h in hits if "not" not in h.lower()]
    return [{"name": "no_bare_fitment_claims", "passed": not offenders, "lines": offenders}]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=bes.DEFAULT_MANIFEST)
    parser.add_argument("--scene", type=Path, default=None,
                        help="generated USDA; default: manifest 'usd' path under the repo root")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--structure-only", action="store_true",
                        help="skip the manifest/BOM cross-check (run after generation in the image)")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    repo_root = manifest_path.parents[2]
    scene_path = args.scene.resolve() if args.scene else repo_root / manifest["usd"]

    checks: list[dict[str, Any]] = []
    if not args.structure_only:
        report = bes.validate_manifest(manifest, manifest_path)
        checks.append({"name": "manifest_contract", "passed": report["passed"], "errors": report["errors"]})
    if not scene_path.is_file():
        checks.append({"name": "scene_file_present", "passed": False, "path": str(scene_path)})
    else:
        text = scene_path.read_text(encoding="utf-8")
        checks.extend(check_usda_structure(text))
        checks.extend(check_evidence_attributes(text))
        checks.extend(check_no_overclaims(text))

    status = "passed" if all(item["passed"] for item in checks) else "failed"
    out = {
        "status": status,
        "classification": "F0_layout_grade_not_fitment",
        "scene": str(scene_path),
        "checks": checks,
        "limitations": [
            "structure and metadata checks only; no OpenUSD load test in this validator",
            "layout-grade F0/F1: no part is dimensionally correct, fitted, tested, safe or released",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
