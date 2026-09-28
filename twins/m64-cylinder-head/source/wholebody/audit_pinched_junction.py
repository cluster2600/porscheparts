#!/usr/bin/env python3
"""Locate a rejected mesh island on unchanged native CAD; draw real sections.

Distances and line chords are local diagnostics, never a minimum-wall or
physical-millimetre certificate. Raw coordinates and geometry remain private.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import time

from render_v5_v2 import sha, save

BODY_SHA = 'b2b48fe40edd1a20c8e6c0d20d77e6045931189f18330b441b09bcbf4618fc0a'
REGION_SHA = 'f533d81212692dbad7ea5812488475742083d4cb5723f17b73d7babec90abd96'


def indexed(shape, kind):
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    table = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, table)
    return [table.FindKey(i) for i in range(1, table.Extent() + 1)]


def locate(shape, centre, radius):
    import numpy as np
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.TopAbs import TopAbs_FACE
    from OCP.gp import gp_Pnt
    if not np.isfinite(centre).all() or not 0 < radius <= 10:
        raise ValueError('finite_centre_and_bounded_radius_required')
    vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, centre))).Vertex()
    rows = []
    for index, face in enumerate(indexed(shape, TopAbs_FACE), 1):
        box = Bnd_Box()
        BRepBndLib.AddOptimal_s(face, box, False, False)
        bounds = np.array(box.Get()).reshape(2, 3)
        lower = np.linalg.norm(np.maximum(0, np.maximum(bounds[0]-centre, centre-bounds[1])))
        if lower > radius:
            continue
        distance = BRepExtrema_DistShapeShape(vertex, face)
        distance.Perform()
        if not distance.IsDone():
            raise ValueError('trimmed_face_distance_failed')
        if distance.Value() <= radius:
            rows.append(dict(face_index=index, distance=distance.Value(),
                             point=list(distance.PointOnShape2(1).Coord())))
    return sorted(rows, key=lambda row: (row['distance'], row['face_index']))


def section_edges(shape, centre):
    import numpy as np
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    operation = BRepAlgoAPI_Section(shape, gp_Pln(gp_Pnt(*map(float, centre)), gp_Dir(0, 1, 0)), False)
    operation.SetRunParallel(False)
    operation.Build()
    if not operation.IsDone():
        raise ValueError('native_section_failed')
    lines = []
    for edge in indexed(operation.Shape(), TopAbs_EDGE):
        curve = BRepAdaptor_Curve(TopoDS.Edge_s(edge))
        sample = GCPnts_QuasiUniformDeflection(curve, 0.0002)
        if not sample.IsDone() or not 2 <= sample.NbPoints() <= 100000:
            raise ValueError('section_sampling_failed')
        lines.append(np.array([sample.Value(i).Coord() for i in range(1, sample.NbPoints()+1)]))
    if not lines:
        raise ValueError('empty_section')
    return lines


def line_chords(shape, centre, direction, span=2.):
    import numpy as np
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN, TopAbs_OUT
    from OCP.gp import gp_Lin, gp_Pnt, gp_Dir
    direction = np.asarray(direction, dtype=float)
    if not np.isfinite(direction).all() or np.linalg.norm(direction) < 1e-12:
        raise ValueError('nonzero_finite_direction_required')
    direction /= np.linalg.norm(direction)
    ray = IntCurvesFace_ShapeIntersector()
    ray.Load(shape, 1e-9)
    ray.Perform(gp_Lin(gp_Pnt(*map(float, centre)), gp_Dir(*map(float, direction))), -span, span)
    if not ray.IsDone():
        raise ValueError('ray_intersection_failed')
    parameters = sorted(set(ray.WParameter(i) for i in range(1, ray.NbPnt()+1)))
    chords = []
    for a, b in zip(parameters, parameters[1:]):
        if b-a < 1e-8:
            continue
        point = centre + (a+b)/2 * direction
        state = BRepClass3d_SolidClassifier(shape, gp_Pnt(*map(float, point)), 1e-9).State()
        if state not in (TopAbs_IN, TopAbs_OUT):
            raise ValueError('ambiguous_ray_interval')
        if state == TopAbs_IN:
            chords.append(dict(start=a, end=b, length=b-a, contains_centre=a <= 0 <= b))
    return dict(direction=direction.tolist(), intersections=parameters, material_chords=chords,
                minimum_wall_thickness_certified=False)


def run(args):
    import numpy as np
    import OCP
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.TopoDS import TopoDS_Shape
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID
    pins = {args.body: BODY_SHA, args.region: REGION_SHA, Path(__file__): sha(__file__)}
    if args.output.exists() or any(p.is_symlink() or sha(p) != h for p, h in pins.items()):
        raise ValueError('exact_inputs_and_fresh_private_output_required')
    started = time.monotonic()
    with np.load(args.region, allow_pickle=False) as data:
        points, cells = data['points'], data['cells']
    if points.shape != (6, 3) or cells.shape != (3, 4) or not np.isfinite(points).all():
        raise ValueError('exact_small_region_arrays_required')
    centre = points.mean(0)
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape, str(args.body), BRep_Builder()):
        raise ValueError('native_body_read_failed')
    if len(indexed(shape, TopAbs_SOLID)) != 1 or not BRepCheck_Analyzer(shape, True, False, True).IsValid():
        raise ValueError('one_valid_native_body_required')
    os.umask(0o077)
    args.output.mkdir(mode=0o700)
    nearby = locate(shape, centre, 2.)
    if len(nearby) < 2:
        raise ValueError('two_nearby_faces_required')
    faces = indexed(shape, TopAbs_FACE)
    first, second = (faces[r['face_index']-1] for r in nearby[:2])
    common_edges = [edge for edge in indexed(first, TopAbs_EDGE)
                    if any(edge.IsSame(other) for other in indexed(second, TopAbs_EDGE))]
    chords = line_chords(shape, centre, np.array(nearby[1]['point'])-nearby[0]['point'])
    lines = section_edges(shape, centre)
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    for ax in axes:
        for line in lines:
            ax.plot(line[:, 0], line[:, 2], color='#27445b', linewidth=.8)
        ax.scatter(centre[0], centre[2], s=28, c='#d95734', zorder=4)
        ax.set_aspect('equal')
        ax.set_xlabel('X — provisional scan units')
        ax.set_ylabel('Z — provisional scan units')
        ax.grid(alpha=.15)
    axes[0].set_title('Native CAD section — body unchanged')
    for ax, half in zip(axes[1:], (3., .10)):
        ax.set_xlim(centre[0]-half, centre[0]+half)
        ax.set_ylim(centre[2]-half, centre[2]+half)
    axes[1].set_title('Local junction — 6-unit window')
    axes[2].set_title('Rejected tetrahedra — XZ projection')
    for cell in cells:
        for i in range(4):
            for j in range(i):
                edge = points[cell[[i,j]]]
                axes[2].plot(edge[:,0], edge[:,2], color='#d95734', alpha=.6, linewidth=.8)
    fig.suptitle('M64 four-valve development | Native section + mesh defect diagnosis', fontsize=16)
    fig.text(.5, .02, 'Not a print simulation. No geometry repair, physical scale or manufacturing approval claimed.', ha='center')
    fig.tight_layout(rect=(0,.05,1,.95))
    image = args.output/'native-junction-section.png'
    fig.savefig(image, dpi=170)
    plt.close(fig)
    report = dict(schema='m64-pinched-junction-diagnostic/v1', input_sha256=BODY_SHA,
        region_sha256=REGION_SHA, source_sha256=pins[Path(__file__)], OCP_version=OCP.__version__,
        centre_private=centre.tolist(), nearby_trimmed_faces_private=nearby,
        two_nearest_faces_common_edges=len(common_edges), local_ray=chords,
        section_plane='Y=region_vertex_centroid_Y', section_curve_display_deflection=.0002,
        section_edges=len(lines), image_sha256=sha(image), geometry_modified=False,
        physical_millimetres_certified=False, manufacturing_authorized=False,
        inputs_unchanged=all(sha(p)==h for p,h in pins.items()), elapsed_seconds=time.monotonic()-started)
    save(args.output/'report.json', report)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('body', 'region', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    signal.alarm(600)
    run(parser.parse_args())
