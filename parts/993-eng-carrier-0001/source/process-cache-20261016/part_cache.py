"""Cache complete native part-only layers and require exact identity for reuse."""
import argparse
import csv
import hashlib
import importlib
import importlib.metadata
import importlib.util
import inspect
import json
import math
from pathlib import Path
import platform
import shutil
import sys
import time

import numpy as np
import pyslm
from pyslm import hatching
import trimesh
import shapely
import pyclipr

SOURCE=Path(__file__).resolve().parent
SLICING=SOURCE.parent/'process-slicing-20261016'
CORE=SOURCE.parent/'process-coverage-20261016/build_pyslm.py'
sys.path.insert(0,str(SLICING))
from parallel_layers import ParallelLayers

PART_KEYS=('rotation_degrees_xyz','support_gap_mm','layer_height_mm','hatch_distance_mm',
           'hatch_angle_degrees','spot_compensation_mm','contour_offset_mm',
           'hatch_volume_offset_mm','inner_contours','outer_contours')
FIELDS={'z_mm','part_area_mm2','part_boundary_points_mm','part_boundary_offsets',
        'part_scan_contour_points_mm','part_scan_contour_offsets','part_hatch_segments_mm'}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def json_bytes(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def array_identity(value):
    a=np.ascontiguousarray(value)
    return {'dtype':a.dtype.str,'shape':list(a.shape),'sha256':hashlib.sha256(a.tobytes()).hexdigest()}


def parameters_only(parameters):return {key:parameters[key] for key in PART_KEYS}


def core_module():
    spec=importlib.util.spec_from_file_location('carrier_part_cache_core',CORE)
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);return core


def make_part(path,parameters):
    part=pyslm.Part('carrier-part-cache')
    part.setGeometry(core_module().exact_mesh(path),fixGeometry=False,mergeVertices=False)
    part.rotation=parameters['rotation_degrees_xyz']
    part.dropToPlatform(parameters['support_gap_mm'])
    return part


def part_identity(part):
    mesh=part.geometry
    return {'rotation_degrees_xyz':np.asarray(part.rotation).tolist(),
            'origin_mm':np.asarray(part.origin).tolist(),'scale_factor':np.asarray(part.scaleFactor).tolist(),
            'transform':np.asarray(part.getTransform()).tolist(),'bounds_mm':mesh.bounds.tolist(),
            'vertices':array_identity(mesh.vertices),'faces':array_identity(mesh.faces)}


def dependencies():
    """Only part slicing/hatching sources; independent support code may evolve."""
    result={'cache/part_cache.py':Path(__file__),'builder/build_pyslm.py':CORE,
            'slicing/parallel_layers.py':SLICING/'parallel_layers.py','slicing/layers.py':SLICING/'layers.py',
            'audit/audit_scanpaths.py':SLICING/'audit_scanpaths.py'}
    for name in ('trimesh','numpy','shapely','pyclipr'):
        root=Path(inspect.getfile(importlib.import_module(name))).parent
        for path in sorted(root.rglob('*')):
            if path.is_file() and (path.suffix in ('.py','.so','.dylib') or '.so.' in path.name):
                result['runtime/'+name+'/'+str(path.relative_to(root))]=path
    root=Path(inspect.getfile(pyslm)).parent
    for path in [root/'__init__.py',root/'core.py',*sorted((root/'hatching').glob('*.py')),
                 *sorted((root/'geometry').glob('*.py'))]:
        if path.is_file():result['runtime/pyslm/'+str(path.relative_to(root))]=path
    return result


def runtime_identity(paths=None):
    paths=dependencies() if paths is None else paths
    return {'python':platform.python_version(),'machine':platform.machine(),
            'packages':{name:importlib.metadata.version(name) for name in
                        ('PythonSLM','numpy','trimesh','shapely','pyclipr','scipy','networkx','rtree')},
            'GEOS_version':shapely.geos_version_string,
            'sources_and_native_binaries_sha256':{label:sha(path) for label,path in paths.items()}}


def write_layer(output,index,z,result):
    raw,contours,vectors,area=result;core=core_module()
    raw_points,raw_offsets=core.packed_paths(raw);points,offsets=core.packed_paths(contours)
    arrays={'z_mm':np.asarray(z),'part_area_mm2':np.asarray(area),
            'part_boundary_points_mm':raw_points,'part_boundary_offsets':raw_offsets,
            'part_scan_contour_points_mm':points,'part_scan_contour_offsets':offsets,
            'part_hatch_segments_mm':np.asarray(vectors)}
    if any(not np.isfinite(a).all() for a in arrays.values()):raise ValueError('Nonfinite part layer')
    path=output/'layers'/f'layer-{index:05d}.npz';np.savez_compressed(path,**arrays)
    return {'layer':index,'z_mm':z,'part_area_mm2':area,'part_boundary_count':len(raw),
            'part_hatch_segments':len(vectors),
            'part_hatch_length_mm':float(np.linalg.norm(np.diff(vectors,axis=1),axis=2).sum())}


class CachedLayers:
    """Instantiate once, then pass this callable as layer_generator(part,z)."""
    def __init__(self,directory,source_stl,parameters):
        self.directory=Path(directory);self.source_stl=Path(source_stl)
        report_path=self.directory/'report.json';self.report_sha256=sha(report_path)
        self.report=json.loads(report_path.read_text());self.parameter_source=parameters
        self.parameters=json.loads(json_bytes(parameters_only(parameters)))
        r=self.report
        if r['status']!='part_layers_completed' or not r['source_and_runtime_unchanged_at_completion']:
            raise ValueError('Only a completed immutable part-layer cache may be reused')
        if sha(self.source_stl)!=r['input_sha256'] or self.parameters!=r['part_parameters']:
            raise ValueError('Cache STL or part-parameter identity mismatch')
        if runtime_identity()!=r['runtime']:raise ValueError('Cache runtime/source identity mismatch')
        n=r['n_layers']
        if n!=math.ceil(r['part_pose_and_arrays']['bounds_mm'][1][2]/self.parameters['layer_height_mm']):
            raise ValueError('Cache declaration omits required part midplanes')
        names=[f'layers/layer-{i:05d}.npz' for i in range(n)]
        actual=sorted(str(p.relative_to(self.directory)) for p in (self.directory/'layers').iterdir())
        recorded=sorted(name for name in r['outputs_sha256'] if name.startswith('layers/'))
        if actual!=names or recorded!=names:raise ValueError('Partial, extra or noncontiguous cached layers')
        for name in r['outputs_sha256']:
            if sha(self.directory/name)!=r['outputs_sha256'][name]:raise ValueError('Cached layer hash mismatch: '+name)
        if sha(self.directory/'layers.csv')!=r['outputs_sha256']['layers.csv']:raise ValueError('Layer CSV hash mismatch')
        with (self.directory/'layers.csv').open() as stream:rows=list(csv.DictReader(stream))
        if [int(row['layer']) for row in rows]!=list(range(n)):raise ValueError('Incomplete cached layer CSV')
        self.areas=[float(row['part_area_mm2']) for row in rows]
        self.z=[(i+.5)*self.parameters['layer_height_mm'] for i in range(n)]
        if [float(row['z_mm']) for row in rows]!=self.z:raise ValueError('Cached midplane order mismatch')
        self.index=0

    def __call__(self,part,z):
        if parameters_only(self.parameter_source)!=self.parameters:raise ValueError('Part parameters changed during cache reuse')
        if sha(self.directory/'report.json')!=self.report_sha256 or sha(self.source_stl)!=self.report['input_sha256']:
            raise ValueError('Cache receipt or STL changed during reuse')
        if part_identity(part)!=self.report['part_pose_and_arrays']:raise ValueError('Cached part pose/array mismatch')
        expected=math.ceil(part.geometry.bounds[1,2]/self.parameters['layer_height_mm'])
        if expected!=self.report['n_layers']:raise ValueError('Cache does not cover every declared midplane')
        if self.index>=len(self.z) or z!=self.z[self.index]:raise ValueError('Cached layers must be consumed at exact ordered midplanes')
        name=f'layers/layer-{self.index:05d}.npz';path=self.directory/name
        if sha(path)!=self.report['outputs_sha256'][name]:raise ValueError('Cached layer changed before consumption')
        with np.load(path,allow_pickle=False) as data:
            if set(data.files)!=FIELDS:raise ValueError('Only part arrays, area and z may exist in cache')
            if float(data['z_mm'])!=z or float(data['part_area_mm2'])!=self.areas[self.index]:raise ValueError('Cached layer scalar identity mismatch')
            # Same packed-path validation used by the independent native audit.
            audit_path=SLICING/'audit_scanpaths.py';spec=importlib.util.spec_from_file_location('cache_path_reader',audit_path)
            audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
            raw=audit.paths(data['part_boundary_points_mm'],data['part_boundary_offsets'])
            contours=audit.paths(data['part_scan_contour_points_mm'],data['part_scan_contour_offsets'])
            vectors=data['part_hatch_segments_mm'].copy();area=float(data['part_area_mm2'])
            if vectors.ndim!=3 or vectors.shape[1:]!=(2,2) or not np.isfinite(vectors).all():raise ValueError('Invalid cached hatch vectors')
        self.index+=1;return raw,contours,vectors,area


def build(source,output,identity_receipt):
    source,output,identity_receipt=map(Path,(source,output,identity_receipt));core=core_module()
    expected=json.loads(identity_receipt.read_text())['candidate_STL_sha256']
    if sha(source)!=expected:raise ValueError('Source STL differs from admitted meshing identity')
    parameters=parameters_only(core.PARAMETERS);part=make_part(source,parameters);pose=part_identity(part)
    n=math.ceil(part.geometry.bounds[1,2]/parameters['layer_height_mm'])
    if n!=1034:raise ValueError('This campaign requires all 1034 declared carrier part layers')
    output.mkdir(parents=True,exist_ok=False);(output/'layers').mkdir();(output/'source').mkdir()
    paths=dependencies();runtime=runtime_identity(paths);identity_sha=sha(identity_receipt)
    for label,path in paths.items():
        target=output/'source'/label;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        if sha(target)!=runtime['sources_and_native_binaries_sha256'][label]:raise ValueError('Dependency changed while freezing')
    shutil.copyfile(identity_receipt,output/'source/meshing.json')
    frozen={'status':'frozen_before_layer_generation','input_sha256':expected,'identity_receipt_sha256':identity_sha,
            'part_parameters':parameters,'part_parameters_sha256':hashlib.sha256(json_bytes(parameters)).hexdigest(),
            'part_pose_and_arrays':pose,'runtime':runtime,'n_layers':n,'workers':4,'maximum_pending_futures':8,
            'support_generation_or_reuse':False}
    (output/'frozen.json').write_text(json.dumps(frozen,indent=2,allow_nan=False)+'\n')
    started=time.monotonic();rows=[];calculate=ParallelLayers(parameters,workers=4)
    try:
        with calculate:
            for i in range(n):
                z=(i+.5)*parameters['layer_height_mm'];rows.append(write_layer(output,i,z,calculate(part,z)))
                if i%25==0:print(json.dumps({'completed_layers':i+1,'declared_layers':n,'elapsed_seconds':time.monotonic()-started}),flush=True)
    finally:
        (output/'parallel-runtime.json').write_text(json.dumps(calculate.receipt(),indent=2)+'\n')
    with (output/'layers.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    if (runtime_identity(paths)!=runtime or sha(source)!=expected or sha(identity_receipt)!=identity_sha or part_identity(part)!=pose):
        raise ValueError('Frozen cache input, pose, source or native runtime changed during calculation')
    p=calculate.receipt()
    if not p['worker_group_closed'] or p['completed_layers']!=n or p['declared_layers']!=n:raise ValueError('Incomplete layer calculation or worker cleanup')
    report={**frozen,'status':'part_layers_completed','source_and_runtime_unchanged_at_completion':True,
            'source_sha256':sha(__file__),'parallel_slicing':p,'elapsed_seconds':time.monotonic()-started,
            'part_nonempty_layers':sum(row['part_area_mm2']>0 for row in rows),
            'part_hatch_segments':sum(row['part_hatch_segments'] for row in rows),
            'part_layer_volume_mm3':sum(row['part_area_mm2'] for row in rows)*parameters['layer_height_mm'],
            'support_scanpaths_generated':False,'complete_LPBF_preparation':False,
            'outputs_sha256':{str(path.relative_to(output)):sha(path) for path in sorted(output.rglob('*')) if path.is_file()}}
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('status','n_layers','part_nonempty_layers','part_hatch_segments','elapsed_seconds')}),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--identity-receipt',required=True,type=Path);args=parser.parse_args()
    build(args.source,args.output,args.identity_receipt)
