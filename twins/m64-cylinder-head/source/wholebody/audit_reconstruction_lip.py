#!/usr/bin/env python3
"""Local removal-volume crosscheck and actual native section of a support trial."""
import argparse
import json
import math
from pathlib import Path
import signal

import numpy as np
from trial_trimmed_support import support_tool, read_native, indexed, BODY_SHA, native
from audit_pinched_junction import section_edges


def faceted_volume(shape, deflection):
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS
    if not math.isfinite(deflection) or not 0 < deflection <= .01:
        raise ValueError('bounded_positive_deflection_required')
    BRepTools.Clean_s(shape)
    mesher = BRepMesh_IncrementalMesh(shape, deflection, False, .02, False)
    if not mesher.IsDone(): raise ValueError('native_tessellation_failed')
    triangles = []
    for face in indexed(shape, TopAbs_FACE):
        face = TopoDS.Face_s(face); location = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face, location)
        if mesh is None or not mesh.NbTriangles(): raise ValueError('all_faces_must_be_tessellated')
        xyz = np.array([mesh.Node(i).Transformed(location.Transformation()).Coord() for i in range(1, mesh.NbNodes()+1)])
        cells = np.array([mesh.Triangle(i).Get() for i in range(1, mesh.NbTriangles()+1)])-1
        if face.Orientation() == TopAbs_REVERSED: cells = cells[:, [0, 2, 1]]
        triangles.extend(xyz[cells])
    xyz = np.array(triangles); xyz -= xyz.mean(axis=(0, 1))
    if len(xyz) > 1000000 or not np.isfinite(xyz).all(): raise ValueError('bounded_finite_tessellation_required')
    volume = math.fsum(map(float, np.einsum('ij,ij->i', xyz[:, 0], np.cross(xyz[:, 1], xyz[:, 2]))/6))
    if volume <= 0: raise ValueError('positive_oriented_faceted_volume_required')
    return dict(deflection=deflection, triangles=len(xyz), volume=volume)


def run(args):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepGProp import BRepGProp
    from OCP.BRepTools import BRepTools
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
    from OCP.TopoDS import TopoDS
    from OCP.TopTools import TopTools_ListOfShape
    record = args.candidate/'report.json'; candidate = args.candidate/'candidate-private.brep'
    receipt = json.loads(record.read_text())
    if (args.output.exists() or native.sha256(args.body) != BODY_SHA
            or any(p.is_symlink() for p in (args.body, record, candidate))
            or receipt.get('schema') != 'm64-trimmed-native-support/v1'
            or receipt.get('input_sha256') != BODY_SHA or receipt.get('source_faces') != [1412, 1648]
            or receipt.get('support_face') != 1647
            or any(receipt.get(k) is not True for k in ('native_valid', 'protected_unchanged', 'tolerances_not_increased'))
            or receipt.get('candidate_sha256') != native.sha256(candidate)
            or receipt.get('status') != 'candidate_pending_BOP_distance_and_mesh'
            or receipt.get('inputs_unchanged') is not True or receipt.get('floor_fillet_radius_scan_units')
            or receipt.get('same_domain_unification')):
        raise ValueError('bound_unfilleted_support_candidate_and_fresh_output_required')
    pins = {p: native.sha256(p) for p in (args.body, candidate, record, Path(__file__), Path(support_tool.__code__.co_filename))}
    args.output.mkdir(mode=0o700)
    body = read_native(args.body); faces = indexed(body, TopAbs_FACE)
    direction = BRepAdaptor_Surface(TopoDS.Face_s(faces[1164])).Plane().Axis().Direction().Coord()
    tool, _ = support_tool(faces[1646], [faces[1411], faces[1647]], direction)
    first, second = TopTools_ListOfShape(), TopTools_ListOfShape(); first.Append(body); second.Append(tool)
    op = BRepAlgoAPI_Common(); op.SetArguments(first); op.SetTools(second)
    op.SetNonDestructive(True); op.SetRunParallel(False); op.SetFuzzyValue(0.); op.Build()
    if not op.IsDone(): raise ValueError('local_removal_intersection_failed')
    removed = op.Shape()
    if not BRepCheck_Analyzer(removed, True, False, True).IsValid() or len(indexed(removed, TopAbs_SOLID)) != 1:
        raise ValueError('one_valid_removed_solid_required')
    path = args.output/'removed-lip-private.brep'
    if not BRepTools.Write_s(removed, str(path)): raise ValueError('removed_solid_write_failed')
    path.chmod(0o600); volumes = []
    for epsilon in (1e-9, 1e-12):
        props = GProp_GProps(); error = BRepGProp.VolumeProperties_s(removed, props, epsilon, True, False)
        if not math.isfinite(error) or not math.isfinite(props.Mass()) or props.Mass() <= 0:
            raise ValueError('finite_positive_removal_integral_required')
        volumes.append(dict(requested_epsilon=epsilon, returned_error_estimate=error, volume=props.Mass()))
    facets = [faceted_volume(removed, d) for d in (.001, .00025, .0000625)]
    props = GProp_GProps(); BRepGProp.SurfaceProperties_s(faces[1411], props)
    centre = np.array(props.CentreOfMass().Coord())
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), facecolor='#f7f9fb')
    for shape, colour, style, label in ((body, '#176b91', '-', 'Original'),
                                      (read_native(candidate), '#cf542d', '--', 'Reconstructed support')):
        lines = section_edges(shape, centre)
        for ax in axes:
            for i, line in enumerate(lines):
                xy = line[:, [0, 2]]-centre[[0, 2]]
                ax.plot(*xy.T, color=colour, linestyle=style, lw=1.5, label=label if i == 0 else None)
    for ax, span in zip(axes, (1., .065)):
        ax.set(xlim=(-span, span), ylim=(-span, span), aspect='equal', xlabel='Relative X — scan units', ylabel='Relative Z — scan units')
        ax.grid(alpha=.2); ax.legend(fontsize=8)
    axes[0].set_title('Actual native section at the removed lip')
    axes[1].set_title('Local reconstruction — equal axis scale')
    fig.suptitle('Local CAD candidate | NOT an accepted head or printing approval')
    fig.text(.5, .025, '935-derived research geometry. Physical scale and M64 interfaces unverified. No thermal or stress field.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, .94)); image = args.output/'support-section.png'
    fig.savefig(image, dpi=160); plt.close(fig)
    report = dict(schema='m64-local-reconstruction-volume/v1', source_hashes={p.name: h for p, h in pins.items()},
        removed_solid_sha256=native.sha256(path), removed_faces=len(indexed(removed, TopAbs_FACE)),
        native_local_volumes=volumes, faceted_volumes=facets,
        image_sha256=native.sha256(image), quadrature_methods_differ_but_geometry_kernel_shared=True,
        rigorous_volume_bound=False, native_Hausdorff_certified=False, manufacturing_authorized=False,
        inputs_unchanged=all(native.sha256(p) == h for p, h in pins.items()))
    native.save(args.output/'report.json', report); print(json.dumps(report))
    return 0 if report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('body', 'candidate', 'output'): parser.add_argument('--'+key, type=Path, required=True)
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
