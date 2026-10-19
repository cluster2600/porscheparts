"""Extend immutable geometry admissions with exact continuous-interval proofs."""
import hashlib
import json
from pathlib import Path
import importlib.util
from types import SimpleNamespace

import shapely

from compact_json import dumps as compact_dumps
_spec=importlib.util.spec_from_file_location('carrier_historical_admissions_isolated',Path(__file__).with_name('admissions.py'))
_legacy=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_legacy)
_legacy.json=SimpleNamespace(loads=json.loads,dumps=compact_dumps)
historical_seal=_legacy.seal
json=SimpleNamespace(loads=json.loads,dumps=compact_dumps)
from continuous_interfaces import COVERAGE_SHA256,HOLES_SHA256,_coverage,no_positive_connection
from continuous_prism_interfaces import BAND_SHA256
import exact_band_union_v2 as _band_union


def _geometry(row,name):
    geometry=shapely.from_wkb(bytes.fromhex(row[name+'_wkb_hex']))
    if hashlib.sha256(geometry.wkb).hexdigest()!=row[name+'_sha256']:
        raise ValueError('Continuous interval geometry and identity differ')
    if geometry.geom_type!='Polygon' or geometry.is_empty or not geometry.is_valid:
        raise ValueError('Continuous interval requires a valid nonempty Polygon')
    return geometry


def continuous_admission(reconstruction,contacts,penetration):
    """Bind the proof to the material components actually sent to remapping."""
    if (not reconstruction or reconstruction.get('strategy')!='continuous_true_interfaces_only_for_native_fragmented_intervals' or
        reconstruction.get('vertical_contact_penetration_mm')!=penetration or reconstruction.get('plate_Z_mm')!=0. or
        reconstruction.get('exact_polygon_coverage_source_sha256')!=COVERAGE_SHA256 or
        reconstruction.get('exact_intended_holes_source_sha256')!=HOLES_SHA256 or
        reconstruction.get('exact_intended_band_union_source_sha256')!=BAND_SHA256 or
        reconstruction.get('distinct_free_intervals_joined')!=0):
        raise ValueError('Missing or unrecognized continuous-interval construction')
    intervals=reconstruction['intervals'];materials=[];rows=[]
    required=[r for r in contacts if r['kind']=='required_free_interval']
    generated=[r for r in contacts if r['kind']=='generated_material_component']
    if not intervals or len(required)!=len(intervals):raise ValueError('Continuous construction omits required intervals')
    for index,row in enumerate(intervals):
        if row['domain_index']!=index:raise ValueError('Continuous interval ordering differs')
        free=_geometry(row,'source_domain_geometry');material=_geometry(row,'generated_material_geometry')
        contact_free=_geometry(required[index],'free_domain_geometry')
        allowed=_geometry(row,'own_allowed_domain_geometry');materials.append(material)
        if (row.get('exact_intended_band_union_confinement') is None or
                row.get('band_authority')!='exact_intended_sweep_union'):
            raise ValueError('Every v2 interval requires its exact intended-band union proof')
        intended=_band_union.prove_band_covered(material,free,penetration)
        if not intended['passed'] or intended!=row['exact_intended_band_union_confinement']:
            raise ValueError('Exact intended-band union proof differs')
        if (required[index]['domain_index']!=index or shapely.normalize(contact_free).wkb!=shapely.normalize(free).wkb or
            row['generated_material_components']!=1 or row['negative_Z_area_mm2']!=0 or
            (row['outside_own_free_vertical_contact_band_area_mm2']!=0 and intended is None) or material.bounds[1]<0.):
            raise ValueError('Continuous material is not bound to its true interval or plate')
        selected=row['continuous_interface_selected']
        if selected:
            core=_coverage.prove_polygon_covered(free,material)
            band=_coverage.prove_polygon_covered(material,allowed)
            if (not core['passed'] or not (band['passed'] or intended is not None) or
                    core!=row['exact_free_domain_coverage'] or band!=row['exact_own_band_confinement']):
                raise ValueError('Continuous interval inclusion/confinement proof differs')
            normalization=row['exact_intended_hole_normalization']
            removed=[h for h in normalization['holes'] if h['removed']]
            if (normalization.get('status')!='completed' or normalization.get('proof_source_sha256')!=HOLES_SHA256 or
                normalization.get('candidate_geometry_sha256')!=row['generated_material_geometry_sha256'] or
                normalization.get('allowed_geometry_sha256')!=row['own_allowed_domain_geometry_sha256'] or
                not normalization.get('all_removed_holes_certified') or normalization.get('new_vertices_introduced')!=0 or
                normalization.get('polygon_overlay_operations')!=0 or not normalization.get('exterior_and_retained_coordinates_unchanged') or
                normalization['removed_hole_indices']!=[h['hole_index'] for h in removed] or
                not all(h['status']=='removed_certified' and h['allowed_coverage']['passed'] and
                    h['allowed_coverage']['source_geometry_sha256']==h['hole_geometry_sha256'] and
                    h['allowed_coverage']['target_geometry_sha256']==row['own_allowed_domain_geometry_sha256'] and
                    h['intended_union_coverage']['passed'] and h['intended_union_coverage']['exact_area_conserved'] for h in removed)):
                raise ValueError('Intended-hole normalization has no complete linked certificates')
        elif row['reason']!='native_material_retained':raise ValueError('An unproved interval was changed')
        rows.append(dict(domain_index=index,selected=selected,material_sha256=row['generated_material_geometry_sha256'],passed=True,
            band_authority='exact_intended_sweep_union' if intended is not None else 'exact_overlay_polygon',
            exact_intended_band_union=intended,
            legacy_overlay_outside_area_mm2=row['outside_own_free_vertical_contact_band_area_mm2']))
    actual=[]
    for item in generated:
        polygon=shapely.from_wkb(bytes.fromhex(item['component_geometry_wkb_hex']))
        if hashlib.sha256(polygon.wkb).hexdigest()!=item['component_geometry_sha256']:
            raise ValueError('Actual component identity differs')
        actual.append(polygon)
    canonical=lambda polygons:sorted(shapely.normalize(p).wkb_hex for p in polygons)
    if canonical(materials)!=canonical(actual):
        raise ValueError('Final material union differs from the certified interval components')
    tree=shapely.STRtree(materials);pairs=[]
    for i,material in enumerate(materials):
        for j in tree.query(material):
            if j<=i:continue
            proof=no_positive_connection(material,materials[j])
            if not proof['passed']:raise ValueError('Final continuous materials join distinct free intervals')
            pairs.append(dict(intervals=[i,int(j)],receipt=proof))
    return dict(passed=True,status='passed',intervals=rows,distinct_interval_proofs=pairs,
        exact_final_component_boundaries_identical=True,
        exact_polygon_coverage_source_sha256=COVERAGE_SHA256,exact_intended_holes_source_sha256=HOLES_SHA256,
        scope='Exact inclusion of selected continuous intervals and identity of all final planar components; actual layer exposure remains independently required.')


def seal(output,checkpoint,store):
    """Keep the six original admissions and add their stricter continuous gates."""
    output=Path(output)
    admission,_=historical_seal(output,checkpoint,store)
    rows=[];passed=bool(checkpoint['supports'])
    for support in checkpoint['supports']:
        skin=support.get('peripheral_skin') or {};grid=support.get('grid_coverage') or {}
        if skin.get('continuous_fragmented_interfaces') is not True:
            passed=False
            rows.append(dict(region=support['index'],unit='support_strategy',receipt=dict(passed=False,status='rejected',
                error='The continuous strategy must be explicit for every v2 region')))
            continue
        units=[]
        for axis,record in enumerate(grid['axes']):
            units.extend((f'grid-{axis}-{plane["order"]}',plane['continuous_interface_reconstruction'],plane['contacts']) for plane in record['planes'])
        units.extend((f'skin-{c["index"]}',c['infill']['continuous_interface_reconstruction'],c['infill']['interface_contacts']) for c in skin['components'])
        for identity,reconstruction,contacts in units:
            try:
                receipt=continuous_admission(reconstruction,contacts,checkpoint['parameters']['support_teeth_upper_penetration_mm'])
            except (ValueError,KeyError,TypeError) as error:
                receipt=dict(passed=False,status='rejected',error=str(error))
            passed &= receipt['passed'];rows.append(dict(region=support['index'],unit=identity,receipt=receipt))
    for key in ['skins','grids','contacts','collisions']:
        path=output/admission[key]['receipt'];receipt=json.loads(path.read_text())
        receipt.update(continuous_interval_exact_admissions=rows,continuous_interval_exact_admissions_passed=passed,
            passed=bool(receipt['passed'] and passed),admission_schema='support-geometry-v2-continuous-intervals')
        receipt['status']='passed' if receipt['passed'] else 'rejected'
        path.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
        admission[key]=dict(status=receipt['status'],receipt=path.name,receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    admitted=all(r['status']=='passed' for r in admission.values())
    checkpoint.update(admission=admission,manufacturing_preparation_admitted=admitted)
    (output/'support-stage.json').write_text(json.dumps(checkpoint,indent=2,allow_nan=False)+'\n')
    return admission,admitted
