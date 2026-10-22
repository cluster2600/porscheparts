#!/usr/bin/env python3
"""Audit all TetGen cells against the unchanged 935 boundary, then save arrays."""
import argparse
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
from prepare_conforming_surface import sha

ROOT=Path(__file__).resolve().parents[3]


def helper(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def table(path,kind):
    with Path(path).open() as stream:
        head=list(map(int,stream.readline().split()))
        cap=5_000_000 if kind=='node' else 10_000_000 if kind=='ele' else 2_000_000
        if not 0<head[0]<=cap:raise ValueError('Bounded TetGen output required')
        expected=[head[0],3,0,0] if kind=='node' else [head[0],4,0] if kind=='ele' else [head[0],1]
        if head!=expected:raise ValueError('Unexpected TetGen header or attributes')
        data=np.loadtxt(stream,dtype=np.float64 if kind=='node' else np.int64,ndmin=2)
    width=4 if kind=='node' else 5
    if data.shape!=(head[0],width) or not np.array_equal(data[:,0],np.arange(head[0])):
        raise ValueError('Complete zero-based ordered records required')
    return data[:,1:4] if kind in ('node','face') else data[:,1:5]


def integer_points(vertices):
    ratios=[[float(x).as_integer_ratio() for x in p] for p in vertices]
    scale=max(den for row in ratios for _,den in row)
    return [tuple(num*(scale//den) for num,den in row) for row in ratios],scale


def determinant(a,b,c,d):
    u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)];w=[d[j]-a[j] for j in range(3)]
    return u[0]*(v[1]*w[2]-v[2]*w[1])-u[1]*(v[0]*w[2]-v[2]*w[0])+u[2]*(v[0]*w[1]-v[1]*w[0])


def exact_orientation(vertices,cells,progress=None):
    points,scale=integer_points(vertices);negative=zero=total=0;minimum=None
    for i,cell in enumerate(cells):
        value=determinant(*(points[int(j)] for j in cell))
        negative+=value<0;zero+=value==0;total+=value;minimum=value if minimum is None else min(minimum,value)
        if progress is not None and (i+1)%100000==0:
            progress.write_text(json.dumps(dict(phase='exact_orientation',cells=i+1,negative=negative,zero=zero))+'\n')
    volume=Fraction(total,6*scale**3)
    return dict(cells=len(cells),negative=negative,zero=zero,minimum_integer_determinant=str(minimum),
                common_coordinate_scale=str(scale),signed_volume_exact=str(volume),signed_volume_native_units_cubed=float(volume))


def audit(prepared,meshed,output):
    prepared,meshed,output=map(Path,(prepared,meshed,output));start=time.monotonic()
    if output.exists() or not output.parent.is_dir():raise ValueError('Fresh private output required')
    proof=json.loads((prepared/'receipt.json').read_text());execution=json.loads((meshed/'execution.json').read_text())
    if (proof['schema']!='935-conforming-surface-preparation-v1' or proof['scale_verified'] is not False
            or execution['exit']!=0 or execution['input_sha256']!=proof['output_sha256']['rotor.smesh']
            or execution['command'][1]!=proof['switches']):raise ValueError('Matching preserved-boundary execution required')
    for name,value in proof['output_sha256'].items():
        if sha(prepared/name)!=value:raise ValueError('Prepared input changed')
    with np.load(prepared/'boundary.npz',allow_pickle=False) as data:reference=data['vertices'].copy();faces=data['faces'].copy()
    vertices=table(meshed/'rotor.1.node','node');cells=table(meshed/'rotor.1.ele','ele');boundary=table(meshed/'rotor.1.face','face')
    bpath=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/tetgen_preserved_boundary.py'
    cpath=ROOT/'twins/m64-cylinder-head/source/wholebody/audit_indexed_tetrahedra.py'
    same=helper(bpath,'_935_boundary_identity').boundary_identity(reference,faces,vertices,boundary,np)
    if not same:raise ValueError('Complete boundary coordinates or triangles changed')
    output.mkdir(mode=0o700);(output/'progress.json').write_text('{"phase":"indexed_connectivity"}\n')
    before={name:sha(meshed/name) for name in ('rotor.1.node','rotor.1.ele','rotor.1.face','execution.json')}
    metrics=helper(cpath,'_935_indexed_connectivity').connectivity_metrics(vertices,cells,boundary)
    exact=exact_orientation(vertices,cells,output/'progress.json')
    relative=abs(exact['signed_volume_native_units_cubed']/proof['source_surface_volume_native_units_cubed']-1)
    passed=(same and metrics['boundary_matches'] and metrics['tetra_connected_components']==1
            and metrics['repeated_node_tetrahedra']==0 and not exact['negative'] and not exact['zero'] and relative<1e-8)
    np.savez_compressed(output/'volume.npz',vertices=vertices,tetrahedra=cells,boundary=boundary)
    if any(sha(meshed/name)!=value for name,value in before.items()):raise ValueError('Mesher output changed during audit')
    report=dict(schema='935-conforming-volume-audit-v1',status='topology_and_exact_orientation_passed' if passed else 'volume_refused',
                source_sha256=sha(__file__),helper_sha256={str(p.relative_to(ROOT)):sha(p) for p in (bpath,cpath)},
                geometry_sha256=proof['geometry_sha256'],prepared_receipt_sha256=sha(prepared/'receipt.json'),
                raw_mesher_output_sha256=before,vertices=len(vertices),tetrahedra=len(cells),boundary_triangles=len(boundary),
                exact_boundary_coordinate_triangle_bijection=same,indexed_connectivity=metrics,exact_orientation=exact,
                volume_relative_difference_from_source=relative,volume_npz_sha256=sha(output/'volume.npz'),
                elapsed_s=time.monotonic()-start,source_unit='uncalibrated_scan_unit',scale_verified=False,
                quality_screen_completed=False,mechanical_mesh_admitted=False,manufacturing_authorized=False)
    (output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    return passed


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','meshed','new_output'):p.add_argument(name,type=Path)
    a=p.parse_args();raise SystemExit(0 if audit(a.prepared,a.meshed,a.new_output) else 2)
