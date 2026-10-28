#!/usr/bin/env python3
"""FCL discrete triangle-surface tests at the retained, uncalibrated 935 pose.

No inferred solid interiors, motion envelope, elastic or thermal qualification.
The observed open drive remains an open surface; it is never closed silently.
"""
import argparse
import hashlib
import importlib.metadata
import itertools
import json
import math
from pathlib import Path
import platform
import struct
import time

import numpy as np

DTYPE=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def model(vertices,faces):
    import fcl
    m=fcl.BVHModel();m.beginModel(len(vertices),len(faces));m.addSubModel(vertices,faces);m.endModel()
    return fcl.CollisionObject(m,fcl.Transform())


def query(a,b):
    import fcl
    result=fcl.CollisionResult();count=fcl.collide(a,b,fcl.CollisionRequest(num_max_contacts=1,enable_contact=True),result)
    if bool(count)!=bool(result.is_collision):raise ValueError('Collision result disagrees with contact count')
    if result.is_collision:
        if len(result.contacts)!=1:raise ValueError('Single retained contact witness required')
        c=result.contacts[0]
        return dict(surface_crossing=True,minimum_surface_distance_native_units=None,
                    witness_triangle_indices=[int(c.b1),int(c.b2)])
    distance=fcl.DistanceResult();value=float(fcl.distance(a,b,fcl.DistanceRequest(enable_nearest_points=True),distance))
    if not math.isfinite(value) or value<0:raise ValueError('Finite nonnegative surface distance required')
    return dict(surface_crossing=False,minimum_surface_distance_native_units=value,witness_triangle_indices=None)


def fixtures():
    a=np.array([[0.,0,0],[1,0,0],[0,1,0]]);faces=np.array([[0,1,2]],dtype=np.int32)
    cases=[('parallel_separation',a+np.array([0,0,2]),False,2.),
           ('disjoint_coplanar_overlapping_boxes',a+np.array([1,1,0]),False,math.sqrt(.5)),
           ('crossing_surfaces',np.array([[.25,.25,-1],[.25,.25,1],[.25,.75,0]]),True,None)]
    rows=[]
    for name,b,collision,distance in cases:
        row=query(model(a,faces),model(b,faces));value=row['minimum_surface_distance_native_units']
        passed=row['surface_crossing']==collision and (distance is None or abs(value-distance)<1e-6)
        rows.append(dict(name=name,expected_crossing=collision,expected_distance=distance,passed=passed,**row))
    if not all(r['passed'] for r in rows):raise ValueError('Independent analytic fixtures failed')
    return rows


def load(path,expected_count):
    path=Path(path)
    with path.open('rb') as stream:header=stream.read(84)
    if (type(expected_count) is not int or not 1<=expected_count<=5_000_000 or len(header)!=84
            or struct.unpack('<I',header[80:])[0]!=expected_count or path.stat().st_size!=84+50*expected_count):
        raise ValueError('Bounded complete binary component STL required')
    data=np.memmap(path,mode='r',dtype=DTYPE,offset=84,shape=(expected_count,))['vertices']
    if not np.isfinite(data).all():raise ValueError('Nonfinite native triangles')
    # Preserve every original triangle and its index; no welding or decimation.
    return model(np.asarray(data.reshape(-1,3),dtype=np.float64),np.arange(3*expected_count,dtype=np.int32).reshape(-1,3))


def run(native,receipt_sha,output):
    native,output=Path(native),Path(output)
    if output.exists() or not output.parent.is_dir() or sha(native/'receipt.json')!=receipt_sha:
        raise ValueError('Pinned receipt and fresh output required')
    receipt=json.loads((native/'receipt.json').read_text())
    if (receipt['target']!='935' or receipt['engine_cylinders']!=6 or receipt['scale_verified'] is not False
            or receipt['manufacturing_authorized'] is not False):raise ValueError('Uncalibrated 935 study required')
    rows=receipt['components'];ids=[r['id'] for r in rows]
    if len(ids)!=4 or set(ids)!={'engine_context','drive_observed','rotor_candidate','provisional_shroud'}:
        raise ValueError('Four retained 935 components required')
    controls=fixtures();models={};start=time.monotonic()
    for r in rows:
        if Path(r['file']).name!=r['file'] or sha(native/r['file'])!=r['sha256']:raise ValueError('Component changed')
        models[r['id']]=load(native/r['file'],r['triangles'])
        print('BVH ready:',r['id'],flush=True)
    pairs=[]
    for a,b in itertools.combinations(ids,2):
        row=dict(components=[a,b],**query(models[a],models[b]));pairs.append(row);print(row,flush=True)
    if sha(native/'receipt.json')!=receipt_sha or any(sha(native/r['file'])!=r['sha256'] for r in rows):
        raise ValueError('Inputs changed during surface review')
    report=dict(schema='935-discrete-surface-review-v1',native_receipt_sha256=receipt_sha,
                source_sha256=sha(__file__),component_sha256={r['id']:r['sha256'] for r in rows},fixtures=controls,pairs=pairs,
                python_fcl_version=importlib.metadata.version('python-fcl'),numpy_version=np.__version__,
                python_version=platform.python_version(),architecture=platform.machine(),elapsed_s=time.monotonic()-start,
                source_coordinate_unit='uncalibrated_scan_unit',pose='retained_assembly_pose_only',
                all_six_surface_pairs_checked=True,triangle_counts_preserved=True,
                solid_containment_checked=False,continuous_rotation_checked=False,thermal_or_elastic_changes_checked=False,
                entire_assembly_interference_checked=False,scale_verified=False,interfaces_verified=False,
                physical_validation=False,manufacturing_authorized=False)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native',type=Path);p.add_argument('receipt_sha256');p.add_argument('new_report',type=Path)
    a=p.parse_args();run(a.native,a.receipt_sha256,a.new_report)
