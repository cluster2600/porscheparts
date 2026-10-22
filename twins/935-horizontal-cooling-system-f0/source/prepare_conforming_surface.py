#!/usr/bin/env python3
"""Prepare an unchanged 935 PicoGK boundary and analytic TetGen control."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

import numpy as np
from stl_moments import DTYPE


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def load_surface(bundle, bundle_sha, stl, stl_sha):
    bundle,stl=Path(bundle),Path(stl)
    if sha(bundle)!=bundle_sha or sha(stl)!=stl_sha:raise ValueError('Pinned mesh inputs required')
    with zipfile.ZipFile(bundle) as archive:
        if sum(i.file_size for i in archive.infolist())>512*1024**2:raise ValueError('Bundle exceeds 512 MiB')
    with np.load(bundle,allow_pickle=False) as data:v=data['vertices'].copy();f=data['faces'].copy()
    if (v.dtype!=np.float32 or f.dtype!=np.int32 or v.ndim!=2 or v.shape[1]!=3 or not 4<=len(v)<=2_000_000
            or f.ndim!=2 or f.shape[1]!=3 or not 4<=len(f)<=4_000_000 or not np.isfinite(v).all()
            or f.min()<0 or f.max()>=len(v)):
        raise ValueError('Bounded finite indexed surface required')
    with stl.open('rb') as stream:header=stream.read(84)
    if len(header)!=84 or struct.unpack('<I',header[80:])[0]!=len(f) or stl.stat().st_size!=84+50*len(f):
        raise ValueError('Complete binary STL required')
    native=np.memmap(stl,mode='r',dtype=DTYPE,offset=84,shape=(len(f),))['vertices']
    for i in range(0,len(f),100000):
        if not np.array_equal(v[f[i:i+100000]],native[i:i+100000]):
            raise ValueError('Bundle changes native triangle coordinates or order')
    return v,f


def write_smesh(path,v,f):
    with Path(path).open('x') as stream:
        stream.write(f'{len(v)} 3 0 0\n')
        for i in range(0,len(v),100000):
            rows=np.column_stack((np.arange(i,min(i+100000,len(v))),v[i:i+100000]))
            np.savetxt(stream,rows,fmt=['%d','%.17g','%.17g','%.17g'])
        stream.write(f'{len(f)} 0\n')
        for i in range(0,len(f),100000):
            block=f[i:i+100000];np.savetxt(stream,np.column_stack((np.full(len(block),3),block)),fmt='%d')
        stream.write('0\n0\n')


def prepare(case_path,output):
    case_path,output=Path(case_path),Path(output);c=json.loads(case_path.read_text())
    if (c['purpose']!='uncalibrated_conforming_mesh_study' or c['scale_verified'] is not False
            or c['source_unit']!='uncalibrated_scan_unit' or c['tetgen_switches']!='-pYMQzC'):
        raise ValueError('Explicit unchanged-boundary, uncalibrated study required')
    if output.exists() or not output.parent.is_dir():raise ValueError('Fresh private output required')
    for parent in output.resolve().parents:
        if (parent/'.git').exists() and output.resolve().relative_to(parent).parts[0]!='work':
            raise ValueError('Scan derivatives must stay in ignored work/')
    v,f=load_surface(c['bundle_path'],c['bundle_sha256'],c['stl_path'],c['geometry_sha256'])
    volume=0.
    for i in range(0,len(f),100000):
        t=v[f[i:i+100000]].astype(np.float64);volume+=float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)
    if not np.isfinite(volume) or volume<=0:raise ValueError('Positive oriented source volume required')
    output.mkdir(mode=0o700);(output/'case.json').write_bytes(case_path.read_bytes())
    write_smesh(output/'rotor.smesh',v,f)
    cv=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
    cf=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype=np.int32)
    write_smesh(output/'control.smesh',cv,cf)
    np.savez_compressed(output/'boundary.npz',vertices=v,faces=f)
    if sha(c['bundle_path'])!=c['bundle_sha256'] or sha(c['stl_path'])!=c['geometry_sha256']:
        raise ValueError('Input changed during preparation')
    receipt=dict(schema='935-conforming-surface-preparation-v1',case_sha256=sha(case_path),source_sha256=sha(__file__),
                 stl_helper_sha256=sha(Path(__file__).with_name('stl_moments.py')),numpy_version=np.__version__,
                 geometry_sha256=c['geometry_sha256'],bundle_sha256=c['bundle_sha256'],vertices=len(v),triangles=len(f),
                 source_surface_volume_native_units_cubed=volume,native_triangle_coordinates_and_order_exact=True,
                 switches=c['tetgen_switches'],control_volume=1/6,source_unit=c['source_unit'],
                 output_sha256={n:sha(output/n) for n in ('rotor.smesh','control.smesh','boundary.npz')},
                 scale_verified=False,volume_mesh_created=False,mechanical_mesh_admitted=False,manufacturing_authorized=False)
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',type=Path);p.add_argument('new_output',type=Path)
    a=p.parse_args();prepare(a.case,a.new_output)
