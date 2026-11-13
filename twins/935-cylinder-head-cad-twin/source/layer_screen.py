#!/usr/bin/env python3
"""Layer screen of the print body with bounded memory.

The repository's layer screen (scripts/run_metal_am_geometry_screen.py, with
the kernel twins/reference-917-engine/source/run_f50_lpbf_geometry_audit.py)
was killed on the 0.5 mm surface of the print body (1,684,604 triangles,
4,482 layers) at caps of 6, 12 and 20 GiB. Stage by stage, measured on
2026-11-12:

* the slicing is not the problem. It ends at 4 GiB when trimesh is asked for
  every section in one call, and at 2.7 GiB when asked 64 layers at a time;
* the wall-thickness probe is. trimesh grows a tangent sphere at 2,000 points
  at once, and each step looks up every triangle near every sphere: on this
  surface that passes 14 GiB within half a minute.

This driver runs the same tool and the same kernel, both unmodified, and
changes two calls only:

  --slice-chunk N       sections are computed N layers at a time and handed to
                        the kernel one by one;
  --thickness-batch N   the thickness probes go to trimesh N at a time.

Every plane is cut by the same function at the same height and every probe is
grown on its own, so the results must not change. That is checked on the
1.0 mm surface: the per-layer table, the report and the chart must have the
hashes of the run made without this driver. It also reports each stage of the
kernel with the peak memory so far.

Usage: layer_screen.py --slice-chunk N --thickness-batch N  <arguments of the screen tool>
Run in the cadsim image with shapely, rtree and networkx on PYTHONPATH.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "scripts/run_metal_am_geometry_screen.py"


class ChunkedSections:
    """What `section_multiplane` returns, computed a few layers at a time."""

    def __init__(self, section, plane_origin, plane_normal, heights, chunk: int):
        self.section, self.origin, self.normal = section, plane_origin, plane_normal
        self.heights, self.chunk = heights, int(chunk)

    def __len__(self) -> int:
        return len(self.heights)

    def __iter__(self):
        for start in range(0, len(self.heights), self.chunk):
            paths = self.section(plane_origin=self.origin, plane_normal=self.normal,
                                 heights=self.heights[start:start + self.chunk])
            for index in range(len(paths)):
                path, paths[index] = paths[index], None
                yield path
            print(f"sections {min(start + self.chunk, len(self.heights))}/{len(self.heights)}",
                  file=sys.stderr, flush=True)


def staged(name: str, function):
    """Report when a stage of the kernel starts and ends, with the peak memory so far."""

    import resource
    import time

    def run(*args, **kwargs):
        started = time.time()
        print(f"stage {name}: start", file=sys.stderr, flush=True)
        result = function(*args, **kwargs)
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0
        print(f"stage {name}: done in {time.time() - started:.0f} s, peak so far {peak:.2f} GiB", file=sys.stderr, flush=True)
        return result

    return run


def main() -> None:
    argv = sys.argv[1:]
    at = argv.index("--slice-chunk")
    chunk = int(argv[at + 1])
    assert chunk > 0
    del argv[at:at + 2]
    at = argv.index("--thickness-batch")
    batch = int(argv[at + 1])
    assert batch > 0
    del argv[at:at + 2]

    import numpy as np
    import trimesh.proximity

    thickness = trimesh.proximity.thickness

    def thickness_in_batches(mesh, points, **options):
        assert options.get("normals") is None
        return np.concatenate([thickness(mesh, points[start:start + batch], **options)
                               for start in range(0, len(points), batch)])

    trimesh.proximity.thickness = thickness_in_batches

    spec = importlib.util.spec_from_file_location("run_metal_am_geometry_screen", TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    load_kernel = tool.load_kernel

    def load_chunked_kernel():
        kernel = load_kernel()
        orient = kernel.orient

        def orient_chunked(mesh, name):
            candidate = orient(mesh, name)
            section = candidate.section_multiplane
            candidate.section_multiplane = (
                lambda plane_origin, plane_normal, heights:
                ChunkedSections(section, plane_origin, plane_normal, heights, chunk))
            return candidate

        kernel.orient = orient_chunked
        for name in ("orientation_screen", "slice_build", "thickness_screen", "trapped_void_screen"):
            setattr(kernel, name, staged(name, getattr(kernel, name)))
        return kernel

    tool.load_kernel = load_chunked_kernel
    sys.argv = [str(TOOL), *argv]
    try:
        report = tool.run(tool.parse_args())
    except tool.ScreenError as exc:
        raise SystemExit(f"screen refused: {exc}")
    print(tool.json.dumps({"part_id": report["part_id"], "gates": report["gates"]}, sort_keys=True))


if __name__ == "__main__":
    main()
