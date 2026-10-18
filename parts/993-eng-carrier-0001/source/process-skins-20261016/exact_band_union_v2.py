"""Verify the same intended band by exact successive convex subtraction."""
import hashlib
import importlib.util
import math
from pathlib import Path

import shapely
from shapely.geometry import box

BASE_SHA256='760a34fcfeb2de640864b91837dc797e3579da2b255ac5b07575c74b2154d44e'
CONVEX_SHA256='03678df0cb1887bc3ebe88d9d71fb8fff4e550a7ef16199272d58ba91695259b'


def _load(name,digest):
    path=Path(__file__).with_name(name+'.py')
    if not path.is_file():path=Path(__file__).resolve().parent.parent/'process-scanpath-audit-20261016'/path.name
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Exact band proof dependency changed')
    spec=importlib.util.spec_from_file_location('carrier_prism_'+name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


_BASE=_load('exact_band_union',BASE_SHA256)
_CONVEX=_load('exact_convex_union',CONVEX_SHA256)


def prove_band_covered(material,domain,penetration):
    """Return a full PASS proof or the first exact uncovered triangle witness."""
    if not math.isfinite(penetration) or penetration<=0:raise ValueError('Positive finite penetration is required')
    triangles,material_partition=_BASE._triangulation(material)
    primitives,domain_partition=_BASE._primitives(domain,penetration)
    boxes=[box(math.nextafter(float(min(p[0] for p in points)),-math.inf),
               math.nextafter(float(min(p[1] for p in points)),-math.inf),
               math.nextafter(float(max(p[0] for p in points)),math.inf),
               math.nextafter(float(max(p[1] for p in points)),math.inf)) for points in primitives]
    tree=shapely.STRtree(boxes);rows=[]
    for index,triangle in enumerate(triangles):
        extent=box(min(float(p[0]) for p in triangle),min(float(p[1]) for p in triangle),
                   max(float(p[0]) for p in triangle),max(float(p[1]) for p in triangle))
        candidates=sorted(int(i) for i in tree.query(extent))
        containing=next((i for i in candidates if all(_BASE._EXACT.inside([primitives[i]+[primitives[i][0]]],p) for p in triangle)),None)
        if containing is not None:
            proof=dict(passed=True,method='all_vertices_in_one_closed_convex_primitive',primitive_id=containing)
        else:
            proof=_CONVEX.union_certificate(triangle,[primitives[i] for i in candidates])
            proof['candidate_primitive_ids']=candidates
        rows.append(dict(triangle=index,receipt=proof))
        if not proof['passed']:break
    passed=len(rows)==len(triangles) and all(row['receipt']['passed'] for row in rows)
    return _BASE._COVERAGE._encoded(dict(schema='exact-intended-vertical-band-union-2',
        status='passed' if passed else 'refused',passed=passed,
        source_geometry_sha256=hashlib.sha256(material.wkb).hexdigest(),
        free_domain_geometry_sha256=hashlib.sha256(domain.wkb).hexdigest(),penetration_mm=penetration,plate_Z_mm=0.,
        proof_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        base_band_source_sha256=BASE_SHA256,exact_convex_union_source_sha256=CONVEX_SHA256,
        intended_convex_primitives=len(primitives),primitives_sha256=hashlib.sha256(repr(primitives).encode()).hexdigest(),
        material_triangulation=material_partition,domain_triangulation=domain_partition,
        arithmetic='Fraction of stored IEEE endpoints; exact convex subtraction; plate half-plane clipped rationally',
        closure_argument='Positive oriented triangle chains equal the complete source boundary. Exact convex subtraction proves each positive triangle covered by a finite closed union, including its boundary.',
        polygon_overlay_operations=0,new_material_vertices=0,triangles=rows,
        checked_material_triangles=len(rows),stopped_at_first_uncovered_triangle=not passed))
