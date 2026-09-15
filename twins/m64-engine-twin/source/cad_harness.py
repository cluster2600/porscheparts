#!/usr/bin/env python3
"""Executer un module CAO propose par un agent, dans un conteneur sans reseau.

Usage : cad_harness.py MODULE.py PARAMS.json OUT_DIR
Le module doit definir build(p) et renvoyer un cq.Workplane ou un cq.Shape.
Imprime un unique objet JSON sur stdout ; ne valide rien au-dela de la geometrie.
"""
import importlib.util
import json
import sys
from pathlib import Path


def main(module_path, params_path, out_dir):
    import cadquery as cq
    from OCP.BRepCheck import BRepCheck_Analyzer

    p = json.loads(Path(params_path).read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("agent_part", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod.build(p)
    if isinstance(result, cq.Workplane):
        shapes = [s for s in result.vals() if isinstance(s, cq.Shape)]
        shape = cq.Compound.makeCompound(shapes) if len(shapes) != 1 else shapes[0]
    elif isinstance(result, cq.Shape):
        shape = result
    else:
        return {"ok": False, "error": f"build_returned_{type(result).__name__}"}
    solids = shape.Solids()
    bb = shape.BoundingBox()
    report = {
        "brep_valid": bool(BRepCheck_Analyzer(shape.wrapped).IsValid()),
        "solid_count": len(solids),
        "face_count": len(shape.Faces()),
        "volume_mm3": float(sum(s.Volume() for s in solids)),
        "bbox_mm": [bb.xlen, bb.ylen, bb.zlen],
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    step = out / "part.step"
    cq.exporters.export(cq.Workplane().add(shape), str(step))
    report["step_bytes"] = step.stat().st_size
    report["ok"] = True
    return report


if __name__ == "__main__":
    try:
        print(json.dumps(main(*sys.argv[1:4])))
    except Exception as exc:  # le message revient a l'agent comme retour d'erreur
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:2000]}))
