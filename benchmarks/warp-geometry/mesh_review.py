#!/usr/bin/env python3
"""Review a pinned real mesh on CPU or CUDA against independent distances."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import time
import zipfile

import numpy as np
from pilot import assess_distances, bounded_integer, load_kernel


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def load_bundle(path, expected):
    path = Path(path)
    if sha(path) != expected:
        raise ValueError('Pinned private bundle hash mismatch')
    with zipfile.ZipFile(path) as archive:
        if sum(row.file_size for row in archive.infolist()) > 512*1024**2:
            raise ValueError('Uncompressed bundle exceeds 512 MiB')
    with np.load(path, allow_pickle=False) as data:
        if set(data.files) != {'vertices','faces','probes','reference_distances'}:
            raise ValueError('Explicit mesh, probes and independent distances required')
        v, f, p, reference = (data[k].copy() for k in ('vertices','faces','probes','reference_distances'))
    if (v.dtype != np.float32 or p.dtype != np.float32 or f.dtype != np.int32 or
            v.ndim != 2 or v.shape[1] != 3 or not 3 <= len(v) <= 8_000_000 or
            f.ndim != 2 or f.shape[1] != 3 or not 1 <= len(f) <= 8_000_000 or
            p.ndim != 2 or p.shape[1] != 3 or not 1 <= len(p) <= 1_000_000 or
            reference.shape != (len(p),) or reference.dtype != np.float64 or
            not all(np.isfinite(a).all() for a in (v,p,reference)) or np.any(reference < 0) or
            f.min() < 0 or f.max() >= len(v)):
        raise ValueError('Bounded finite arrays and valid triangle indices required')
    if np.any(np.linalg.norm(v, axis=1) > 500) or np.any(np.linalg.norm(p, axis=1) > 500):
        raise ValueError('Inputs exceed this kernel query-distance domain')
    return v, f, p, reference


def query(wp, kernel, device, vertices, faces, points):
    mesh = wp.Mesh(points=wp.array(vertices,dtype=wp.vec3,device=device),
                   indices=wp.array(faces.reshape(-1),dtype=wp.int32,device=device))
    probes = wp.array(points,dtype=wp.vec3,device=device)
    distances = wp.empty(len(points),dtype=wp.float32,device=device)
    hits = wp.empty(len(points),dtype=wp.int32,device=device)
    wp.launch(kernel,dim=len(points),inputs=[mesh.id,probes],outputs=[distances,hits],device=device)
    wp.synchronize_device(device)
    return distances.numpy(), hits.numpy()


def run(case_path, device_name, repeats, output):
    case_path, output = Path(case_path), Path(output)
    if device_name not in ('cpu','cuda:0') or type(repeats) is not int or not 1 <= repeats <= 5:
        raise ValueError('Explicit CPU/CUDA device and bounded repeat count required')
    case = json.loads(case_path.read_text())
    if (case['scale_verified'] is not False or case['native_unit'] != 'uncalibrated_scan_unit' or
            case['reference_scope'] != 'complete_target_mesh' or
            not case['reference_method'].startswith('independent_trimesh_point_to_triangle')):
        raise ValueError('Explicit uncalibrated geometry and independent reference required')
    if output.exists() or output.with_suffix('.samples.npz').exists() or not output.parent.is_dir():
        raise ValueError('New report in an existing private directory required')
    v, f, p, reference = load_bundle(case['bundle_path'],case['bundle_sha256'])
    start = time.perf_counter()
    import warp as wp
    if wp.__version__ != '1.18.0' or np.__version__ != '2.2.6':
        raise ValueError('This experiment requires pinned Warp1.18.0 and NumPy2.2.6')
    wp.init(); device = wp.get_device(device_name)
    if device_name == 'cuda:0' and not device.is_cuda:
        raise RuntimeError('Requested CUDA device is unavailable; no CPU fallback')
    kernel = load_kernel(); init_wall = time.perf_counter()-start; times = []; checks = []
    for i in range(repeats+1):
        started = time.perf_counter()
        distances, hits = query(wp,kernel,device,v,f,p)
        times.append(time.perf_counter()-started)
        checks.append(assess_distances(distances,reference,hits))
    passed = all(c['passed'] for c in checks)
    report = {'schema':'warp-private-mesh-review-v1','passed':passed,
        'source_sha256':{name:sha(Path(__file__).with_name(name)) for name in ('mesh_review.py','pilot.py','kernels.py')},
        'case_sha256':sha(case_path),'bundle_sha256':case['bundle_sha256'],'geometry_sha256':case['geometry_sha256'],
        'reference_method':case['reference_method'],'reference_sha256':case['reference_sha256'],
        'reference_scope':case['reference_scope'],
        'native_unit':case['native_unit'],'vertices':len(v),'triangles':len(f),'probes':len(p),
        'device':{'requested':device_name,'actual':str(device),'name':device.name,'cuda':bool(device.is_cuda)},
        'versions':{'python':platform.python_version(),'numpy':np.__version__,'warp':wp.__version__},
        'max_abs_error_native_units':max(c['max_abs_error_mm'] for c in checks),
        'rms_abs_error_native_units':max(c['rms_abs_error_mm'] for c in checks),
        'tolerance_native_units':checks[0]['tolerance_mm'],'query_misses':max(c['query_miss_count'] for c in checks),
        'invalid_distances':max(c['invalid_distance_count'] for c in checks),'repeats':repeats,
        'timing':{'cold_init_and_pass_s':init_wall+times[0],
                  'pass_wall_s':times,'total_init_and_passes_s':time.perf_counter()-start,
                  'kernel_cache_directory':str(wp.config.kernel_cache_dir),
                  'scope':'fresh BVH and buffers, host/device transfer, query, synchronize and readback',
                  'speedup_claimed':False},
        'geometry_only':True,'scale_verified':False,'self_intersection_verified':False,
        'physical_validation':False,'manufacturing_authorized':False,'gpu_validated':bool(passed and device.is_cuda)}
    if sha(case['bundle_path']) != case['bundle_sha256']:
        raise ValueError('Input changed during queries')
    output.write_text(json.dumps(report,indent=2)+'\n')
    np.savez_compressed(output.with_suffix('.samples.npz'),distances=distances,hits=hits,reference_distances=reference)
    print(json.dumps(report,indent=2))
    return passed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case',type=Path); parser.add_argument('--device',choices=('cpu','cuda:0'),required=True)
    parser.add_argument('--repeats',type=bounded_integer(1,5),default=3); parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); raise SystemExit(0 if run(args.case,args.device,args.repeats,args.output) else 1)
