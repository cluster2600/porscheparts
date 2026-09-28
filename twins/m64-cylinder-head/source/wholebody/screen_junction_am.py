#!/usr/bin/env python3
"""Preliminary AM slicing of a bound native mesh, not thermomechanical LPBF.

Volume-element quality may be rejected: only its closed boundary is used for
screening. This does not promote the mesh to CAE or certify CAD deviation.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import sys
import time

from render_v5_v2 import sha, save
from trial_meshers_2026 import read_gmsh, boundary
from audit_pinched_junction import BODY_SHA

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'scripts'))


def integrate_layers(rows, height, layer):
    if (not all(math.isfinite(v) and v > 0 for v in (height,layer))
            or len(rows) != math.ceil(height/layer-1e-12)
            or any(not math.isfinite(r[k]) or r[k] < 0 for r in rows
                   for k in ('part_area_mm2','support_area_mm2'))):
        raise ValueError('complete_finite_nonnegative_layers_required')
    widths=[min(layer,max(0.,height-i*layer)) for i in range(len(rows))]
    return tuple(math.fsum(r[k]*w for r,w in zip(rows,widths))
                 for k in ('part_area_mm2','support_area_mm2'))


def run(args):
    import gmsh
    import numpy as np
    import trimesh
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import run_metal_am_geometry_screen as screen
    import scipy
    import shapely
    mesh_path = args.trial/'native-trial/mesh/coarse-native-head.msh'
    report_path = args.trial/'native-trial/mesh/mesh-report.json'
    parent_path = args.trial/'junction-trial.json'
    parent = json.loads(parent_path.read_text())
    report = json.loads(report_path.read_text())
    if (args.output.exists() or parent.get('status') != 'completed'
            or parent.get('inputs_and_sources_unchanged') is not True
            or parent['mesh_report_sha256'] != sha(report_path)
            or report['native_BRep_sha256'] != BODY_SHA or report['native_input_unchanged'] is not True
            or sha(mesh_path) != report['mesh']['sha256']):
        raise ValueError('fresh_output_and_bound_native_mesh_required')
    for key in ('positive_signed_tetra_volumes','one_connected_tetra_region','complete_tetra_boundary','all_CAD_faces_meshed'):
        if report['gates'].get(key) is not True:
            raise ValueError('closed_native_boundary_gate_failed_'+key)
    pins = {p:sha(p) for p in (mesh_path,report_path,parent_path,Path(__file__),screen.KERNEL_PATH,Path(screen.__file__))}
    started = time.monotonic()
    os.umask(0o077)
    args.output.mkdir(mode=0o700)
    result = dict(schema='m64-native-mesh-AM-screen/v1',status='incomplete',
        input_mesh_sha256=sha(mesh_path), native_BRep_sha256=BODY_SHA,
        input_mesh_CAE_accepted=False, exact_native_CAD_deviation_certified=False,
        physical_millimetres_certified=False, assumed_mm_per_scan_unit=1.,
        geometry_modified=False, heat_and_distortion_simulated=False, manufacturing_authorized=False,
        unit_scope='All kernel mm fields use the unverified 1 mm/scan-unit hypothesis.',
        source_sha256=pins[Path(__file__)],kernel_sha256=pins[screen.KERNEL_PATH],
        adapter_sha256=pins[Path(screen.__file__)],software=dict(gmsh=gmsh.__version__,
            numpy=np.__version__,trimesh=trimesh.__version__,scipy=scipy.__version__,shapely=shapely.__version__))
    target = args.output/'report.json'
    save(target,result)
    gmsh.initialize(['am','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0)
    try:
        points,cells,stored,_ = read_gmsh(mesh_path)
    finally:
        gmsh.finalize()
    faces=boundary(cells)
    if set(map(tuple,np.sort(faces,axis=1))) != set(map(tuple,np.sort(stored,axis=1))):
        raise ValueError('mesh_boundary_mismatch')
    used,inverse = np.unique(faces,return_inverse=True)
    mesh=trimesh.Trimesh(vertices=points[used],faces=inverse.reshape(-1,3),process=False)
    if (not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0
            or len(mesh.split(only_watertight=False)) != 1):
        raise ValueError('one_closed_outward_boundary_required')
    kernel=screen.load_kernel()
    kernel.LAYER_MM=args.layer
    kernel.OVERHANG_DEG=45.
    kernel.SUPPORT_RASTER_MM=.5
    machine=dict(manufacturer='Eplus3D',model='EP-M400',build_width_mm=400.,build_depth_mm=400.,
        build_height_mm=450.,height_includes_plate=True,
        source='https://www.eplus3d.com/products/ep-m400-metal-3d-printer/',
        source_checked='2026-09-28',plate_and_support_height_reserved=False,
        material_process_qualified=False)
    kernel.machine_fit=lambda extents: screen.machine_fit(machine,extents)
    sanitize=kernel.sanitize_polygonal
    def strict_polygon(geometry):
        if geometry is not None and not geometry.is_valid:
            raise ValueError('invalid_polygon_no_silent_make_valid')
        return sanitize(geometry)
    kernel.sanitize_polygonal=strict_polygon
    result.update(machine_candidate=machine,triangle_count=len(faces),orientation_screen=kernel.orientation_screen(mesh))
    fitting=[r for r in result['orientation_screen'] if r['bare_part_nominal_fit']]
    if not fitting: raise ValueError('no_bare_envelope_fit_even_under_scale_hypothesis')
    selected=min(fitting,key=lambda r:r['downward_projected_area_mm2'])['orientation']
    result['selected_orientation']=selected
    result['selection_rule']='minimum projected downward area among six bare-envelope candidates; not support optimization'
    save(args.output/'orientation-stage.json',result)
    rows,slicing=kernel.slice_build(mesh,selected)
    # Correct integration of a possibly shorter final layer, independent of
    # the inherited support summary's constant-thickness last-layer formula.
    height=slicing['build_height_mm']
    layer_volume,support_volume=integrate_layers(rows,height,args.layer)
    polygon_volume=float(mesh.volume)
    result.update(full_build_slicing=slicing,midpoint_integrated_volume_scan_units3=layer_volume,
        boundary_volume_scan_units3=polygon_volume,
        slice_volume_relative_difference=abs(layer_volume/polygon_volume-1),
        slice_volume_within_0p5_percent_of_input_polygon_mesh=abs(layer_volume/polygon_volume-1)<=.005,
        support_proxy_partial_last_layer_corrected_scan_units3=support_volume,
        thickness_screen=kernel.thickness_screen(mesh,512),
        powder_escape_screen=dict(executed=False,accepted=False,
            reason='The inherited surface-fill routine cannot establish enclosed-void absence; no pass transferred.'),
        support_removal_access_verified=False,machining_allowances_qualified=False,
        laser_paths_generated=False,calibrated_material_card_available=False)
    kernel.write_rows(args.output/'layer-metrics-private.csv',rows)
    fig,axes=plt.subplots(1,3,figsize=(15,5))
    for ax,key,title in zip(axes,('part_area_mm2','unsupported_area_mm2','support_area_mm2'),
                            ('Part cross-section','New unsupported area','Vertical support proxy')):
        ax.plot([r['z_mm'] for r in rows],[r[key] for r in rows],linewidth=.7)
        ax.set_title(title);ax.set_xlabel('Build height — provisional scan units')
        ax.set_ylabel('Area — scan units squared');ax.grid(alpha=.2)
    fig.suptitle(f'M64 | Geometric slicing only | {selected} | {len(rows)} layers')
    fig.text(.5,.02,'No thermal/distortion/depowdering pass. Scale, supports and material route remain unqualified.',ha='center')
    fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(args.output/'am-geometric-screen.png',dpi=160);plt.close(fig)
    result.update(status='completed_screening_only',elapsed_seconds=time.monotonic()-started,
                  inputs_unchanged=all(sha(p)==h for p,h in pins.items()),
                  image_sha256=sha(args.output/'am-geometric-screen.png'))
    # save() is create-only; preserve the intermediate receipt rather than overwriting it.
    save(args.output/'completed-report.json',result)
    print(json.dumps({k:result[k] for k in ('status','selected_orientation','slice_volume_relative_difference','elapsed_seconds')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--layer',type=float,choices=(.06,.12),default=.06)
    signal.alarm(900)
    run(parser.parse_args())
