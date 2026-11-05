#!/usr/bin/env python3
"""Build or independently inspect exact acquired fourth-region source charts."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["build", "verify"])
    for name in ["selection", "arrays", "helper", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--step", type=Path)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing reference-region output refused")
    pins = [(a.selection / "selection.json", "77d8c5c58ebf19f0eae3c0eec34290dddcae4597c5a2ecad5830da6b661d7a5e"),
            (a.selection / "selected-source.npz", "fdaf0c99285a2ab5d9f5d1928e4e4f1d5283ac25cb60264bfcc5a6f7981a9f31"),
            (a.arrays, "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"),
            (a.helper, "fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e" if a.mode == "build"
             else "3a2ddf947a1083399890dc167ec631fec0bce4d5a7a564613a765fcd95158658")]
    for path, expected in pins:
        if sha(path) != expected:
            raise ValueError("Registered reference-region input mismatch: " + path.name)
    admission = json.loads(pins[0][0].read_text())
    if not admission["size_admitted"] or not admission["defect_index_admitted"]:
        raise ValueError("Registered source region failed admission")
    with np.load(pins[1][0], allow_pickle=False) as s:
        v, f, vi, fi = (s[k] for k in ["vertices", "triangles", "source_vertex_ids", "source_face_ids"])
    with np.load(a.arrays, allow_pickle=False) as s:
        original_v, original_f = s["vertices"], s["triangles"]
    if (not np.array_equal(v, original_v[vi]) or
            not np.array_equal(vi[f], original_f[fi])):
        raise ValueError("Selected source coordinates or connectivity changed")
    spec = importlib.util.spec_from_file_location("retained_region_helper", a.helper)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    if a.mode == "build":
        cv, cf, mapping, groups, result = helper.atlas(v, f)
        shape = helper.native_shape(cv, cf, groups)
        a.output.mkdir(parents=True)
        helper.save(a.output / "controls.json", helper.controls(a.output))
        np.savez_compressed(a.output / "source-provenance.npz", vertices=cv, triangles=cf,
                            original_source_vertex_ids=vi[mapping], original_source_face_ids=fi,
                            component_labels=groups)
        step = a.output / "observed-fourth-region.step"
        helper.export(shape, step)
        result["step_sha256"] = sha(step)
    else:
        if a.step is None:
            raise ValueError("Actual STEP input required")
        from OCP.BRep import BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_VERTEX
        from OCP.TopoDS import TopoDS
        before = sha(a.step)
        result = helper.inspect_source(a.step, original_v, original_f[fi], fi)
        shape = helper.load(a.step)
        if helper.indexed(shape, TopAbs_SOLID).Extent():
            raise ValueError("Unexpected solid in acquired open reference")
        fm = helper.indexed(shape, TopAbs_FACE)
        maximum = 0.
        for i in range(1, fm.Extent() + 1):
            face = TopoDS.Face_s(fm.FindKey(i))
            plane = BRepAdaptor_Surface(face, True).Plane()
            vm = helper.indexed(face, TopAbs_VERTEX)
            for j in range(1, vm.Extent() + 1):
                maximum = max(maximum, plane.Distance(BRep_Tool.Pnt_s(TopoDS.Vertex_s(vm.FindKey(j)))))
        if maximum > 1e-6 or sha(a.step) != before:
            raise ValueError("Actual STEP plane consistency or immutability failed")
        result.update(actual_step_sha256=before, native_solids=0,
                      native_plane_corner_maximum_mm=maximum)
        a.output.mkdir(parents=True)
    result.update(adapter_source_sha256=sha(__file__),
                  retained_helper_sha256=sha(a.helper), acquired_coordinates_changed=False,
                  cylinder_fit_adopted=False, charts_are_physical_components=False,
                  full_head_created=False, physical_acceptance=False, manufacturing_authorized=False)
    (a.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
