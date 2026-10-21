"""Restore a real connected free sheet when native denture fragments its material.

The policy constructs a new continuous interval, with added and removed native
material recorded explicitly. It preserves D and never bridges distinct gaps.
"""
import hashlib
import importlib.util
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon,box

_coverage_path=Path(__file__).resolve().parent/'exact_polygon_coverage.py'
if not _coverage_path.is_file():_coverage_path=Path(__file__).resolve().parent.parent/'process-scanpath-audit-20261016/exact_polygon_coverage.py'
COVERAGE_SHA256='0b1c7598a7358b9e9a384dd5b90dc66aa9e1ea53828033b6722477ec11409bed'
if hashlib.sha256(_coverage_path.read_bytes()).hexdigest()!=COVERAGE_SHA256:raise ValueError('Exact polygon inclusion helper changed')
_spec=importlib.util.spec_from_file_location('carrier_continuous_polygon_coverage',_coverage_path)
_coverage=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_coverage)
_holes_path=_coverage_path.with_name('exact_intended_holes.py')
HOLES_SHA256='bfcc3177f68b83c9c3139cb26e79d0633342caf04143565c2c80845cee403a7f'
if hashlib.sha256(_holes_path.read_bytes()).hexdigest()!=HOLES_SHA256:raise ValueError('Exact intended-hole helper changed')
_spec=importlib.util.spec_from_file_location('carrier_continuous_intended_holes',_holes_path)
_holes=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_holes)


def no_positive_connection(a,b):
    """A nonzero shared boundary interval or positive overlap is forbidden."""
    if any(p.geom_type!='Polygon' or p.is_empty or not p.is_valid for p in [a,b]):
        raise ValueError('Distinct interval proof requires valid nonempty Polygon pairs')
    def edges(polygon):
        return [[list(a),list(b)] for ring in [polygon.exterior,*polygon.interiors]
                for a,b in zip(list(ring.coords)[:-1],list(ring.coords)[1:]) if a!=b]
    found=[]
    for source,target in [(a,b),(b,a)]:
        intervals=_coverage._EXACT.clip_contacts(target,edges(source))
        if intervals:found.append(intervals[0])
    return _coverage._encoded(dict(status='passed' if not found else 'refused',passed=not found,
        source_geometry_sha256=hashlib.sha256(a.wkb).hexdigest(),target_geometry_sha256=hashlib.sha256(b.wkb).hexdigest(),
        arithmetic='Exact Fraction clips of both closed polygon boundaries; points alone do not connect material',
        positive_interval_witnesses=found))


def repair(material,domain,interfaces,penetration):
    from grid_intervals import parts,vertical_contact_band,contacts,_both_contacts
    if interfaces is None:raise ValueError('Continuous interfaces require attested source interfaces')
    if penetration<=0 or not np.isfinite(penetration):raise ValueError('Explicit positive interface penetration is required')
    pieces=[];rows=[]
    for index,free in enumerate(parts(domain)):
        allowed=vertical_contact_band(free,penetration)
        allowed=allowed.intersection(box(allowed.bounds[0],0.,allowed.bounds[2],max(0.,allowed.bounds[3])))
        native=material.intersection(allowed)
        contact=contacts(native,free,interfaces,required_only=True) if not native.is_empty else []
        required=[r for r in contact if r['kind']=='required_free_interval']
        fragmented=len(parts(native))!=1
        missed=any(not r['passed'] for r in required)
        selected=fragmented or missed
        result=native
        source_traces={}
        exact_core=exact_band=hole_normalization=None
        if selected:
            additions=[]
            for name,dz in [('upper',penetration),('lower',-penetration)]:
                paths=_both_contacts.round_contacts_in_both(free,free,interfaces[name])
                source_traces[name]=paths
                for a,b in paths:
                    a=np.asarray(a);b=np.asarray(b)
                    strip=Polygon([a,b,b+[0,dz],a+[0,dz]])
                    if strip.area>0:additions.append(strip)
            # The entire original D is retained. The extra strips are vertical
            # sweeps of attested interfaces, restricted to the existing band.
            # Union the swept bands before the original D. Clipping D itself
            # introduces needless computed intersections on its source edges.
            # Inclusion and confinement are verified below, without an epsilon.
            sweeps=shapely.union_all(additions).intersection(allowed)
            result=free.union(sweeps)
            # A computed hole may contradict the intended primitive union.
            # Remove only complete holes with exact coverage certificates;
            # retained rings and all stored coordinates remain unchanged.
            result,hole_normalization=_holes.normalize_holes(result,[free,*additions],allowed)
            if result.is_empty or not result.is_valid or len(parts(result))!=1:
                raise ValueError('A continuous interval did not remain one valid material component')
            if free.difference(result).area!=0:
                raise ValueError('Continuous construction lost original free-domain material')
            exact_core=_coverage.prove_polygon_covered(free,result)
            exact_band=_coverage.prove_polygon_covered(result,allowed)
            if not exact_core['passed'] or not exact_band['passed']:
                error=ValueError('Exact continuous-interval inclusion or confinement was refused')
                error.receipt=dict(exact_free_domain_coverage=exact_core,exact_own_band_confinement=exact_band)
                raise error
        if result.is_empty:raise ValueError('A required free interval has no material')
        pieces.append(result)
        after=contact if not selected else contacts(result,free,interfaces,required_only=True)
        required_after=[r for r in after if r['kind']=='required_free_interval']
        if not all(r['passed'] for r in required_after):raise ValueError('Continuous sheet still lacks a required true contact')
        rows.append(dict(domain_index=index,continuous_interface_selected=selected,
            reason='native_denture_fragmented_or_missed_required_contact' if selected else 'native_material_retained',
            source_domain_geometry_wkb_hex=free.wkb_hex,source_domain_geometry_sha256=hashlib.sha256(free.wkb).hexdigest(),
            generated_material_geometry_wkb_hex=result.wkb_hex,generated_material_geometry_sha256=hashlib.sha256(result.wkb).hexdigest(),
            own_allowed_domain_geometry_wkb_hex=allowed.wkb_hex,own_allowed_domain_geometry_sha256=hashlib.sha256(allowed.wkb).hexdigest(),
            exact_free_domain_coverage=exact_core,exact_own_band_confinement=exact_band,
            exact_intended_hole_normalization=hole_normalization,
            native_material_components=len(parts(native)),generated_material_components=len(parts(result)),
            original_free_area_mm2=free.area,native_material_area_mm2=native.area,generated_material_area_mm2=result.area,
            removed_native_material_area_mm2=native.difference(result).area,
            added_material_area_mm2=result.difference(native).area,
            upper_contact_before_mm=sum(r['upper_contact_trace_mm'] for r in required),
            lower_contact_before_mm=sum(r['lower_contact_trace_mm'] for r in required),
            upper_contact_after_mm=sum(r['upper_contact_trace_mm'] for r in required_after),
            lower_contact_after_mm=sum(r['lower_contact_trace_mm'] for r in required_after),
            interface_sweeps_2d_mm=source_traces,negative_Z_area_mm2=result.intersection(box(result.bounds[0],min(-1.,result.bounds[1]-1),result.bounds[2],0)).area,
            outside_own_free_vertical_contact_band_area_mm2=result.difference(allowed).area))
    # A penetration band is never permission to join two separate free intervals.
    tree=shapely.STRtree(pieces);pair_proofs=[]
    for i,piece in enumerate(pieces):
        for j in tree.query(piece):
            if j<=i:continue
            proof=no_positive_connection(piece,pieces[j]);pair_proofs.append(dict(intervals=[i,int(j)],receipt=proof))
            if not proof['passed']:
                raise ValueError('Continuous material would join distinct free intervals')
    result=shapely.union_all(pieces)
    return result,dict(strategy='continuous_true_interfaces_only_for_native_fragmented_intervals',
        vertical_contact_penetration_mm=penetration,plate_Z_mm=0.,intervals=rows,
        selected_intervals=sum(r['continuous_interface_selected'] for r in rows),
        distinct_interval_connection_proofs=pair_proofs,exact_polygon_coverage_source_sha256=COVERAGE_SHA256,
        exact_intended_holes_source_sha256=HOLES_SHA256,
        increased_contact_requires_detachment=True,distinct_free_intervals_joined=0,
        source_domain_geometry_sha256=hashlib.sha256(domain.wkb).hexdigest(),
        generated_material_geometry_sha256=hashlib.sha256(result.wkb).hexdigest())
