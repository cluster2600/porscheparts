#!/usr/bin/env python3
"""Write parts/<id>/source/gyroid.json: the gyroid-core variant of a part.

    python prep_gyroid.py <PART_ID> [<PART_ID> ...] | --all [--force] [--base-voxel]

The variant starts from the part's published PicoGK body (derived/*-picogk.stl,
pinned by SHA-256) and keeps its outer form; GyroidCore.cs hollows it into a
skin and a sheet-gyroid core wherever three cells fit. Core settings follow the
material class of the part's candidate material and are bounded below by the
voxel size (a wall under 2.5 voxels does not survive voxelization); the run may
use voxels down to half the base model's, so thin sheets still resolve. Every value
is an assumption: no core has been printed, depowdered or tested.

--base-voxel keeps the base model's voxel (walls and cells grow with it): for
large parts whose finer mesh exceeds finish.py's memory (about 9 million
triangles under a 10 GB cap). An existing gyroid.json is kept unless --force; hand edits (keep_solid,
recut_void, per-part overrides) live there.
"""
import hashlib
import json
import sys
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1]
ROOT = CATALOG.parents[1]

# wall, skin, minimum cell and drain diameter in mm, per material class.
# LPBF metal: 0.4 mm gyroid sheets are typical of printed heat exchangers;
# polymer PBF needs thicker sheets; composite panels follow sandwich practice
# (laminate skins over a light core). Whether powder leaves cells this small is
# not verified: depowdering is an open question for every part.
CLASSES = {
    "lpbf_metal": {"wall": 0.4, "skin": 0.8, "cell": 2.5, "drain": 2.0},
    "polymer": {"wall": 0.8, "skin": 1.2, "cell": 4.0, "drain": 2.5},
    "composite": {"wall": 1.0, "skin": 1.5, "cell": 5.0, "drain": 3.0},
}


# Parts without their own picogk.json: the base body comes from an existing
# model in the repository. Material and density follow the catalogue record
# (0 when the record names none, so no mass is claimed).
IMPORTED = {
    "993-ENG-BRACKET-0001": {
        "stl": "twins/993-engine-mount-system-f0/derived/native/993-ENG-BRACKET-0001.stl",
        "generator": "engine_mounts (parts/picogk-catalog/engine/EngineMounts.cs, PicoGK)",
        "voxel_mm": 0.5, "density_g_cm3": 0, "material_candidate": "unknown; record lists FFF for a geometric study"},
    "993-ENG-MOUNTING-0001": {
        "stl": "twins/993-engine-mount-system-f0/derived/native/993-ENG-MOUNTING-0001.stl",
        "generator": "engine_mounts (parts/picogk-catalog/engine/EngineMounts.cs, PicoGK)",
        "voxel_mm": 0.5, "density_g_cm3": 0, "material_candidate": "unknown; record lists FFF for a geometric study"},
    "993-ENG-CYLINDER-HEAD-4V-F0-0001": {
        "stl": "parts/m64-cylinder-head-0001/export/picogk-run-1/m64-head-4v-envelope.stl",
        "generator": "m64 head 4V envelope (PicoGK, 2 mm voxels; run-report.json beside it)",
        "voxel_mm": 2.0, "density_g_cm3": 2.7, "material_candidate": "aluminium candidate for head body (LPBF among candidates)"},
    "993-ENG-COOLING-IMPELLER-ALSI10MG-F0-0001": {
        "stl": "parts/993-eng-cooling-impeller-alsi10mg-f0-0001/derived/cooling_impeller_alsi10mg_f0.stl",
        "generator": "cooling_impeller.py (archived Carrera F0 study, not the 993 Turbo fan; CAD, not PicoGK)",
        "voxel_mm": 0.3, "density_g_cm3": 2.67, "material_candidate": "AlSi10Mg LPBF (comparison)"},
}


def imported_spec(part_id):
    imp = IMPORTED[part_id]
    record = json.loads((ROOT / "catalog" / "parts" / f"{part_id.lower()}.json").read_text(encoding="utf-8"))
    spec = {"part_id": part_id, "name": record["name"] + " (PicoGK)", "generator": imp["generator"],
            "catalogue_record": f"catalog/parts/{part_id.lower()}.json",
            "safety_class": record["classification"]["safety_class"],
            "material_candidate": imp["material_candidate"], "density_g_cm3": imp["density_g_cm3"],
            "voxel_mm": imp["voxel_mm"], "open_interfaces": [],
            "status": "F0 concept geometry - not fitted, not tested, not safe, not released, not a print file"}
    return spec, [ROOT / imp["stl"]]


def material_class(spec):
    m = spec.get("material_candidate", "").lower()
    if "composite" in m or "fibre" in m:
        return "composite"
    if "polymer" in m or "pa12" in m or spec.get("density_g_cm3", 0) < 1.3:
        return "polymer"
    return "lpbf_metal"


def region_tiles(src):
    """bionic.json shapes under parts/picogk-catalog/out/ are tiled design regions
    (inside/outside of the body), not features: the published body carries every
    opening already, so they are not re-applied."""
    bio = src / "bionic.json"
    if not bio.exists():
        return {}
    opt = json.loads(bio.read_text(encoding="utf-8"))["optimization"]
    if not any("picogk-catalog/out/" in s.get("path", "") for k in ("solid", "void") for s in opt.get(k) or []):
        return {}
    return {"reapply_bionic_features": False,
            "reapply_bionic_features_note": "bionic.json lists tiled design regions, not features; the published "
                                            "PicoGK body already carries every opening, and the skin wraps all of them"}


def param(value, note):
    return {"value": round(value, 3), "unit": "mm", "basis": "assumption", "source": None, "note": note}


def prep(part_id, force=False, base_voxel_only=False):
    src = ROOT / "parts" / part_id.lower() / "source"
    out = src / "gyroid.json"
    if out.exists() and not force:
        print(f"keep {out.relative_to(ROOT)}")
        return
    if (src / "picogk.json").exists():
        spec = json.loads((src / "picogk.json").read_text(encoding="utf-8"))
        base = [p for p in sorted((src.parent / "derived").glob("*-picogk.stl"))]
    elif part_id.upper() in IMPORTED:
        spec, base = imported_spec(part_id.upper())
    else:
        raise SystemExit(f"{part_id}: no source/picogk.json and no IMPORTED base")
    if len(base) != 1:
        raise SystemExit(f"{part_id}: expected one derived/*-picogk.stl, found {len(base)}")
    base_voxel = float(spec["voxel_mm"])
    cls = material_class(spec)
    d = CLASSES[cls]
    voxel = base_voxel if base_voxel_only else round(max(base_voxel / 2, min(base_voxel, d["wall"] / 2.5)), 3)
    wall = max(d["wall"], 2.5 * voxel)
    skin = max(d["skin"], 3.0 * voxel)
    # At 2.5 mm cells and 0.4 mm walls the labyrinth necks span a few voxels and
    # the pocket fill closed most of the core (rod: 5.8 of 7 cm3 refilled); at
    # 9 walls per cell the drains reach the whole core and the sheet is ~1/3 solid.
    cell = max(d["cell"], 9.0 * wall)
    drain = max(d["drain"], 4.0 * voxel)
    rel = base[0].relative_to(ROOT).as_posix()
    gyroid = {
        "part_id": spec["part_id"],
        "name": spec["name"].replace("(PicoGK)", "").strip() + ", gyroid core (PicoGK)",
        "generator": "gyroid_core",
        "catalogue_record": spec.get("catalogue_record"),
        "porsche_part_numbers": spec.get("porsche_part_numbers", []),
        "safety_class": spec["safety_class"],
        "material_candidate": spec["material_candidate"],
        "density_g_cm3": spec["density_g_cm3"],
        "voxel_mm": voxel,
        "picogk_enhancement": (
            f"Gyroid core: the published PicoGK body ({spec['generator']}) keeps its outer form; a {skin:g} mm skin "
            f"encloses a sheet gyroid ({cell:g} mm cell, {wall:g} mm wall) wherever the body holds three cells, "
            "thinner zones and functional features stay solid, drain ports run to the nearest outer surface and "
            "any pocket they miss is filled solid. Core settings are assumptions for the "
            f"{cls.replace('_', ' ')} class; nothing here is printed, depowdered or tested."),
        "base": {"stl": rel, "sha256": hashlib.sha256(base[0].read_bytes()).hexdigest(),
                 "generator": spec["generator"]},
        "material_class": cls,
        "parameters": {
            "cell_mm": param(cell, "gyroid period; at least 9 walls so the channels stay open to the drains"),
            "wall_mm": param(wall, f"gyroid sheet thickness; class minimum {d['wall']} mm, at least 2.5 voxels"),
            "skin_mm": param(skin, f"outer skin; class minimum {d['skin']} mm, at least 3 voxels"),
            "min_cells": {"value": 3, "unit": "cells", "basis": "assumption", "source": None,
                          "note": "owner rule 2026-10-22: core only where three cells fit, else solid"},
            "drain_d_mm": param(drain, f"powder/resin drain diameter; class minimum {d['drain']} mm"),
            "max_drains": {"value": 6, "unit": "count", "basis": "assumption", "source": None,
                           "note": "lowest and highest core points, then farthest-point spread"},
        },
        "keep_solid": [],
        **region_tiles(src),
        "recut_void": [],
        "open_interfaces": spec.get("open_interfaces", []),
        "status": spec.get("status", ""),
    }
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(gyroid, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out.relative_to(ROOT)}  {cls}: cell {cell:g}, wall {wall:g}, skin {skin:g}, drain {drain:g} mm")


def main(argv):
    force = "--force" in argv
    ids = [a for a in argv if not a.startswith("--")]
    if "--all" in argv:
        ids = [json.loads(p.read_text(encoding="utf-8"))["part_id"]
               for p in sorted(ROOT.glob("parts/993-*/source/picogk.json"))]
    if not ids:
        raise SystemExit(__doc__)
    for pid in ids:
        prep(pid, force, "--base-voxel" in argv)


if __name__ == "__main__":
    main(sys.argv[1:])
