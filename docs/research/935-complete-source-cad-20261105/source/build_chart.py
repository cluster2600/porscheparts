"""Construct one exact acquired-facet chart using the unchanged qualified builder."""
import argparse
import gc
import json
from pathlib import Path
import signal
import resource
import sys
import time

import numpy as np

from chart_common import job, module, save, selected, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--controls", action="store_true"); mode.add_argument("--chunk", type=int)
    args = parser.parse_args(); value, root = job(args.job)
    args.output.mkdir(mode=0o700, exist_ok=False)
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    builder = module(root/"source_builder.py", "qualified_source_chart_builder", "fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e")
    if args.controls:
        report = builder.controls(args.output)
        # Same geometric square with deliberately duplicated native source edges.
        points = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 0, 0], [1, 1, 0], [0, 1, 0]], float)
        faces = np.array([[0, 1, 2], [3, 4, 5]])
        builder.export(builder.native_shape(points, faces, np.array([0, 1])), args.output/"unsewn-square-negative.step")
        save(args.output/"report.json", {"source_sha256": sha(Path(__file__)), "controls": report,
             "synthetic_only_no_acquired_geometry_decoded": True, "seconds": time.monotonic()-started})
    else:
        vertices, faces, ids = selected(value, root, args.chunk)
        source_vertices, inverse = np.unique(faces, return_inverse=True)
        local_faces = inverse.reshape(-1, 3)
        chart_vertices, chart_faces, corner_source, groups, counts = builder.atlas(vertices[source_vertices], local_faces)
        assert np.array_equal(source_vertices[corner_source[chart_faces]], faces)
        shape = builder.native_shape(chart_vertices, chart_faces, groups)
        output = args.output/"source-chart.step"; builder.export(shape, output)
        del shape; gc.collect()
        provenance = args.output/"private-source-chart-map.npz"
        np.savez_compressed(provenance, source_face_ids=ids, chart_original_vertex_ids=source_vertices[corner_source],
                            chart_faces=chart_faces, chart_source_components=groups)
        save(args.output/"build-report.json", {"source_sha256": sha(Path(__file__)), "job_sha256": sha(args.job),
             "chunk": args.chunk, "source_faces": len(ids), "topology": counts, "step_sha256": sha(output),
             "step_bytes": output.stat().st_size, "source_map_sha256": sha(provenance),
             "source_coordinates_or_triangles_modified": False, "source_chunk_seams_not_sewn": True,
             "anatomical_identity_inferred": False, "physical_acceptance": False,
             "manufacturing_authorized": False, "seconds": time.monotonic()-started})
    signal.alarm(0)


if __name__ == "__main__":
    main()
