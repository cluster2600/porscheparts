"""Reopen actual STEP independently of the builder and compare original acquisition."""
import argparse
import json
from pathlib import Path
import signal
import resource
import sys
import time

import numpy as np

from chart_common import fixture, job, module, save, selected, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True); parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--control", choices=("square", "point-contact")); mode.add_argument("--chunk", type=int)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Existing native verification output refused")
    value, root = job(args.job)
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    verifier = module(root/"source_verifier.py", "independent_original_source_verifier", "3a2ddf947a1083399890dc167ec631fec0bce4d5a7a564613a765fcd95158658")
    if args.control:
        vertices, faces, ids = fixture(args.control)
    else:
        vertices, faces, ids = selected(value, root, args.chunk)
    assert args.step.is_file() and not args.step.is_symlink(); before = sha(args.step)
    report = verifier.inspect_source(args.step, vertices, faces, ids)
    assert report["vertex_roundtrip_maximum_mm"] == 0., "Source corner bits changed in actual STEP"
    # Inspect every support plane against actual saved native face vertices.
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopAbs import TopAbs_FACE, TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    shape = verifier.load(args.step); mapped = verifier.indexed(shape, TopAbs_FACE)
    plane_error = 0.
    for i in range(1, mapped.Extent()+1):
        face = TopoDS.Face_s(mapped.FindKey(i)); plane = BRepAdaptor_Surface(face, True).Plane()
        corners = verifier.indexed(face, TopAbs_VERTEX); assert corners.Extent() == 3
        for j in range(1, 4):
            point = BRep_Tool.Pnt_s(TopoDS.Vertex_s(corners.FindKey(j)))
            plane_error = max(plane_error, float(plane.Distance(point)))
    assert plane_error <= 1e-8, "Actual native support plane exceeds predeclared arithmetic guard"
    assert sha(args.step) == before
    save(args.output, {"source_sha256": sha(Path(__file__)), "job_sha256": sha(args.job),
         "step_sha256": before, "chunk": args.chunk, "synthetic_control": args.control, "source_faces": len(ids),
         "independent_original_acquisition_not_builder_map": not bool(args.control), "native_source_comparison": report,
         "all_native_support_planes_inspected": mapped.Extent(), "native_support_plane_residual_maximum_nominal_mm": plane_error,
         "arithmetic_plane_guard_nominal_mm": 1e-8, "physical_tolerance_or_metrology_not_inferred": True,
         "source_chunk_seams_not_sewn": True, "physical_acceptance": False, "manufacturing_authorized": False,
         "seconds": time.monotonic()-started})
    signal.alarm(0)


if __name__ == "__main__":
    main()
