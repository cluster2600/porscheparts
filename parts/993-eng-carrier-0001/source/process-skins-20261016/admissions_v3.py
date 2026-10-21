"""Seal the six historical gates with recomputed combinatorial interval proofs.

Only the two rounded-overlay outside-area predicates change authority. Their
measured values remain in the original receipts. No geometry is generated here;
the planar constructor is replayed to verify the exported component identities.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import MultiPolygon
import trimesh

from compact_json import dumps as compact_dumps

SOURCE = Path(__file__).resolve().parent
SCHEMA = 'support-geometry-v3-combinatorial-intervals'
STRATEGY = 'continuous_domain_with_nonoverlapping_attested_edge_strips'
CONSTRUCTION_SHA256 = '94393c465fb15c1c3129ad8e482ea19cd597d3e716714e069b4eaee38b80e2fa'
BAND_SHA256 = 'c6452e918ed5fd04bfd1595102eb8c691c697c18477d7b924e29ff7465c62286'
COVERAGE_SHA256 = '0b1c7598a7358b9e9a384dd5b90dc66aa9e1ea53828033b6722477ec11409bed'
LEGACY_SHA256 = '2015cbcf6483a728c47995811420e33fe1f59025e9cd1227fa9d71923c5e5868'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(name, digest):
    path = SOURCE / (name + '.py')
    if not path.is_file():
        path = SOURCE.parent / 'process-scanpath-audit-20261016' / path.name
    if sha(path) != digest:
        raise ValueError('An admission proof dependency changed: ' + name)
    spec = importlib.util.spec_from_file_location('carrier_admission_v3_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_construction = _load('combinatorial_interfaces', CONSTRUCTION_SHA256)
_band = _load('exact_band_union_v3', BAND_SHA256)
_coverage = _load('exact_polygon_coverage', COVERAGE_SHA256)
_historical = _load('admissions', LEGACY_SHA256)
KEYS = _historical.KEYS
complete_contacts = _historical.complete_contacts


def _same(actual, expected, message):
    # JSON equality is type sensitive, unlike Python's True == 1.
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if encode(actual) != encode(expected):
        raise ValueError(message)


def _geometry(row, name):
    geometry = shapely.from_wkb(bytes.fromhex(row[name + '_wkb_hex']))
    if hashlib.sha256(geometry.wkb).hexdigest() != row[name + '_sha256']:
        raise ValueError('Interval/component geometry identity differs')
    if (geometry.geom_type != 'Polygon' or geometry.is_empty or not geometry.is_valid or
            geometry.has_z or not np.isfinite(shapely.get_coordinates(geometry)).all()):
        raise ValueError('A valid finite nonempty planar Polygon is required')
    return geometry


def _collection(polygons):
    return polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)


def continuous_admission(reconstruction, contacts, penetration):
    """Rebuild D + attested strips, both inclusions and every final component.

The recorded GEOS band is a diagnostic only. The unchanged exact polygon and
intended-union checks decide the two inclusions, with no new tolerance.
    """
    if type(penetration) not in (float, int) or not math.isfinite(penetration) or penetration <= 0:
        raise ValueError('Explicit positive finite penetration is required')
    header = dict(strategy=STRATEGY, vertical_contact_penetration_mm=penetration, plate_Z_mm=0.,
        combinatorial_construction_source_sha256=CONSTRUCTION_SHA256,
        exact_polygon_coverage_source_sha256=COVERAGE_SHA256,
        exact_intended_band_union_source_sha256=BAND_SHA256,
        polygon_overlay_operations_for_material=0, increased_contact_requires_detachment=True,
        distinct_free_intervals_joined=0)
    if not isinstance(reconstruction, dict):
        raise ValueError('Missing combinatorial interval construction')
    for key, expected in header.items():
        _same(reconstruction.get(key), expected, 'Unrecognized combinatorial construction: ' + key)
    intervals = reconstruction['intervals']
    required = [r for r in contacts if r['kind'] == 'required_free_interval']
    generated = [r for r in contacts if r['kind'] == 'generated_material_component']
    if not intervals or len(intervals) != len(required) or len(generated) != len(intervals):
        raise ValueError('Continuous construction omits intervals or actual components')
    _same(reconstruction.get('selected_intervals'), len(intervals), 'Every v3 interval must be explicit')
    materials, domains, rows = [], [], []
    for index, row in enumerate(intervals):
        _same(row['domain_index'], index, 'Interval ordering differs')
        _same(required[index]['domain_index'], index, 'Required contact ordering differs')
        if row.get('continuous_interface_selected') is not True or row.get('band_authority') != 'exact_intended_sweep_union':
            raise ValueError('Every interval requires an explicit construction and exact band proof')
        _same(row['generated_material_components'], 1, 'An interval must export one component')
        free = _geometry(row, 'source_domain_geometry')
        material = _geometry(row, 'generated_material_geometry')
        contact_free = _geometry(required[index], 'free_domain_geometry')
        if shapely.normalize(contact_free).wkb != shapely.normalize(free).wkb:
            raise ValueError('The construction does not use the true required free interval')
        interfaces = {name: required[index][name + '_interface_traces_2d_mm'] for name in ['upper', 'lower']}
        _same(row['attested_source_interfaces'], interfaces, 'Attested interfaces differ from required source contacts')
        interface_sha = hashlib.sha256(json.dumps(interfaces, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        _same(row['attested_source_interfaces_sha256'], interface_sha, 'Attested interface identity differs')
        from grid_intervals import contacts as recompute_contacts
        actual_required = recompute_contacts(material, free, interfaces, required_only=True)
        if len(actual_required) != 1:
            raise ValueError('An interval must have one complete required-contact proof')
        for name, value in actual_required[0].items():
            if name not in {'domain_index', 'free_domain_geometry_wkb_hex', 'free_domain_geometry_sha256'} and not name.startswith('diagnostic_geos_'):
                _same(required[index][name], value, 'Required true-contact proof differs: ' + name)
        rebuilt, construction = _construction.construct(free, interfaces, penetration)
        if rebuilt.wkb != material.wkb:
            raise ValueError('The exported material differs from the recomputed combinatorial construction')
        _same(row['combinatorial_construction'], construction, 'Combinatorial construction proof differs')
        core = _coverage.prove_polygon_covered(free, material)
        intended = _band.prove_band_covered(material, free, penetration)
        if not core['passed'] or not intended['passed']:
            raise ValueError('Exact source inclusion or intended-band confinement was refused')
        _same(row['exact_free_domain_coverage'], core, 'Exact free-domain proof differs')
        _same(row['exact_intended_band_union_confinement'], intended, 'Exact intended-band proof differs')
        if material.bounds[1] < 0. or row['negative_Z_area_mm2'] != 0:
            raise ValueError('The exported material extends below the plate')
        allowed = _geometry(row, 'own_allowed_domain_geometry')
        outside = material.difference(allowed).area
        _same(row['outside_own_free_vertical_contact_band_area_mm2'], outside, 'Stored GEOS outside-area diagnostic differs')
        _same(row['legacy_overlay_confinement_passed'], outside == 0., 'Stored GEOS confinement diagnostic differs')
        materials.append(material); domains.append(free)
        proof_sha = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        rows.append(dict(domain_index=index, passed=True,
            material_sha256=row['generated_material_geometry_sha256'],
            recomputed_construction_sha256=proof_sha(construction),
            exact_free_domain_coverage_sha256=proof_sha(core), exact_intended_band_union_sha256=proof_sha(intended),
            required_contacts_recomputed=True, legacy_overlay_outside_area_mm2=outside,
            legacy_overlay_used_as_authority=False))
    for name, polygons in [('source_domain_geometry_sha256', domains), ('generated_material_geometry_sha256', materials)]:
        _same(reconstruction[name], hashlib.sha256(_collection(polygons).wkb).hexdigest(), 'Whole interval collection identity differs')
    actual = []
    for index, component in enumerate(generated):
        _same(component['component_index'], index, 'Actual component ordering differs')
        actual.append(_geometry(component, 'component_geometry'))
    canonical = lambda polygons: sorted(shapely.normalize(p).wkb_hex for p in polygons)
    if canonical(materials) != canonical(actual):
        raise ValueError('Actual exported components differ from the certified materials')
    from continuous_prism_interfaces import no_positive_connection
    pairs = []
    tree = shapely.STRtree(materials)
    for i, material in enumerate(materials):
        for j in tree.query(material):
            if j <= i:
                continue
            proof = no_positive_connection(material, materials[j])
            if not proof['passed']:
                raise ValueError('Final materials join distinct free intervals')
            pairs.append(dict(intervals=[i, int(j)], receipt=proof))
    _same(reconstruction['distinct_interval_connection_proofs'], pairs, 'Distinct interval proofs differ')
    return dict(passed=True, status='passed', strategy=STRATEGY, intervals=rows,
        distinct_interval_proofs=pairs, exact_final_component_boundaries_identical=True,
        construction_source_sha256=CONSTRUCTION_SHA256, exact_band_source_sha256=BAND_SHA256,
        geometry_authority='recomputed_combinatorial_construction_and_both_exact_inclusions')


def _material_bindings(support, vertices, faces):
    """Retain the historical geometry hash and bind group descriptors to contacts.

Face ranges partition the actual NPZ. Mapping/area tolerances and the actual
connection graph remain the independent historical gates; descriptors alone do
not claim an exact inverse of the IEEE skin remapping.
    """
    groups = support['peripheral_skin']['support_surface_face_groups']
    if (not groups or vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all() or
            faces.ndim != 2 or faces.shape[1] != 3 or faces.dtype.kind not in 'iu' or
            not len(faces) or faces.min() < 0 or faces.max() >= len(vertices)):
        raise ValueError('Invalid actual support geometry/groups')
    expected = {}
    for axis, record in enumerate(support['grid_coverage']['axes']):
        for plane, item in enumerate(record['planes']):
            expected.update({f'/grid_coverage/axes/{axis}/planes/{plane}/contacts/{i}': row
                for i, row in enumerate(item['contacts']) if row['kind'] == 'generated_material_component'})
    for component, item in enumerate(support['peripheral_skin']['components']):
        expected.update({f'/peripheral_skin/components/{component}/infill/interface_contacts/{i}': row
            for i, row in enumerate(item['infill']['interface_contacts']) if row['kind'] == 'generated_material_component'})
    cursor = 0; identities = set(); references = set()
    for group in groups:
        begin, end = group['face_range']
        if (type(begin) is not int or type(end) is not int or begin != cursor or
                not begin < end <= len(faces) or group['id'] in identities):
            raise ValueError('Material groups must partition actual faces exactly once')
        cursor = end; identities.add(group['id'])
        reference = group['contact_reference']
        if not isinstance(reference, str) or reference not in expected or reference in references:
            raise ValueError('Each actual generated component requires one canonical material group reference')
        references.add(reference); contact = expected[reference]
        _geometry(group, 'component_geometry')
        for name in ['component_geometry_sha256', 'component_geometry_wkb_hex']:
            _same(group[name], contact[name], 'Actual face group and certified component differ')
    if cursor != len(faces) or references != set(expected):
        raise ValueError('Material groups omit actual faces or generated components')


def _exact_support_units(support, penetration):
    skin = support.get('peripheral_skin') or {}
    if skin.get('continuous_fragmented_interfaces') is not True:
        raise ValueError('Every region requires the explicit continuous strategy')
    units = []
    for axis, record in enumerate(support['grid_coverage']['axes']):
        units.extend((f'grid-{axis}-{plane["order"]}', plane['continuous_interface_reconstruction'], plane['contacts']) for plane in record['planes'])
    units.extend((f'skin-{c["index"]}', c['infill']['continuous_interface_reconstruction'], c['infill']['interface_contacts']) for c in skin['components'])
    result = {}
    for identity, reconstruction, contacts in units:
        if identity in result:
            raise ValueError('Duplicate support surface unit')
        try:
            result[identity] = continuous_admission(reconstruction, contacts, penetration)
        except (ValueError, KeyError, TypeError, IndexError) as error:
            result[identity] = dict(passed=False, status='rejected', error=str(error))
    if not result:
        raise ValueError('No support surface unit was verified')
    return result


def seal(output,checkpoint,store):
    output=Path(output);store.verify();supports=checkpoint['supports'];coverage=json.loads((output/'region-coverage.json').read_text())
    regions_ok=bool(coverage.get('region_projection_admission_passed') and coverage['expected_regions']==coverage['generated_regions']==len(supports)==store.report['expected_regions'])
    skin_rows=[];grid_rows=[];contact_rows=[];graphs=[];exact_rows=[]
    source_sha=sha(__file__)
    if [s['index'] for s in supports]!=list(range(7)) or store.report['expected_regions']!=7:
        raise ValueError('The seven ordered support regions are required')
    all_skin=all_grid=bool(supports) and len(supports)==store.report['expected_regions']
    for support in supports:
        skin=support.get('peripheral_skin') or {};grid=support.get('grid_coverage') or {}
        units=_exact_support_units(support,checkpoint['parameters']['support_teeth_upper_penetration_mm'])
        exact_rows.extend(dict(region=support['index'],unit=name,receipt=proof) for name,proof in units.items())
        graph=skin.get('material_connection_graph') or {};groups=skin.get('support_surface_face_groups',[])
        with np.load(output/f"support-{support['index']:03d}.npz",allow_pickle=False) as mesh:
            geometry_sha=hashlib.sha256(mesh['vertices'].tobytes()+mesh['faces'].tobytes()).hexdigest()
            _material_bindings(support,mesh['vertices'],mesh['faces'])
        graph_ids=[identity for component in graph.get('components',[]) for identity in component['group_ids']]
        connected=bool(graph.get('status')=='passed' and graph.get('input_geometry_sha256')==geometry_sha and
            graph.get('groups')==len(groups) and sorted(graph_ids)==sorted(g['id'] for g in groups) and
            all(c.get('passed') and c.get('upper_contact_group_ids') and c.get('lower_contact_group_ids') for c in graph.get('components',[])) and
            len(graph.get('internal_connectivity',[]))==len(groups) and
            all(c.get('passed') and c.get('remaining_components')==1 for c in graph.get('internal_connectivity',[])))
        graphs.append(dict(region=support['index'],passed=connected,receipt=graph))
        components=skin.get('components',[])
        excluded=skin.get('unexposed_vertical_charts',[])
        exclusions_verified=True
        if excluded:
            from layer_schedule import calendar,no_exposure
            with np.load(store.path/'input-part.npz',allow_pickle=False) as p:
                planes=calendar(float(p['vertices'][:,2].max()),checkpoint['parameters']['layer_height_mm'])
            if skin.get('exposure_calendar',{}).get('sha256')!=hashlib.sha256(planes.tobytes()).hexdigest():
                exclusions_verified=False
            with np.load(store.path/store.report['regions'][support['index']]['envelope'],allow_pickle=False) as p:
                source_volume=trimesh.Trimesh(p['vertices'],p['faces'],process=False)
            for item in excluded:
                proof=no_exposure(source_volume,item['source_face_indices'],planes)
                exclusions_verified &= proof=={k:v for k,v in item.items() if k!='source_chart_index'}
        skin_ok=bool(skin.get('status')=='generated' and components and skin.get('generated_vertical_components')==len(components) and
            exclusions_verified and skin.get('explicitly_unexposed_vertical_components',0)==len(excluded) and
            skin.get('expected_vertical_components')==len(components)+len(excluded) and
            all(r.get('status')=='excluded_no_positive_section_on_actual_schedule' and r.get('original_envelope_unchanged') and
                all(c['positive_exact_triangle_sections']==0 for c in r['concerned_planes']) for r in excluded))
        for c in components:
            u=c['unfolding'];m=c['remapping'];f=c['infill']
            skin_ok &= (abs(u['source_vertical_area_mm2']-u['unfolded_domain_area_mm2'])<=u['numerical_area_tolerance_mm2'] and
                u['source_coordinate_roundtrip_max_mm']<=u['numerical_coordinate_tolerance_mm'] and
                abs(m['split_planar_area_mm2']-m['remapped_area_mm2'])<=m['numerical_area_tolerance_mm2'] and
                units[f"skin-{c['index']}"]['passed'] and
                complete_contacts(f['interface_contacts'],f['required_free_intervals'],f['generated_material_components'],connected))
            contact_rows.extend(dict(region=support['index'],support_surface_kind='skin',component=c['index'],**r) for r in f['interface_contacts'])
        axes=grid.get('axes',[]);grid_ok=bool(grid.get('status')=='passed' and len(axes)==2)
        for axis_index,axis in enumerate(axes):
            grid_ok &= axis['expected_planes']==axis['generated_planes']==len(axis['planes']) and bool(axis['planes'])
            for plane in axis['planes']:
                grid_ok &= (plane.get('passed') and units[f"grid-{axis_index}-{plane['order']}"]['passed'] and
                    complete_contacts(plane['contacts'],plane['required_free_intervals'],plane['generated_material_components'],connected))
                contact_rows.extend(dict(region=support['index'],support_surface_kind='grid',axis=plane['fixed_axis'],order=plane['order'],**r) for r in plane['contacts'])
        all_skin &= skin_ok;all_grid &= grid_ok
        skin_rows.append(dict(region=support['index'],passed=bool(skin_ok),receipt=skin))
        grid_rows.append(dict(region=support['index'],passed=bool(grid_ok),receipt=grid))
    contacts_ok=bool(exact_rows) and all(r['receipt']['passed'] for r in exact_rows) and bool(contact_rows) and all(g['passed'] for g in graphs) and all(r.get('passed') and
        (r['upper_contact_trace_mm']>0 or not r.get('upper_interface_required',True)) and
        (r['lower_contact_trace_mm']>0 or not r.get('lower_interface_required',True)) for r in contact_rows if r['kind']=='required_free_interval')
    envelopes_ok=store.report['status']=='passed'
    receipts=dict(
        envelopes=dict(passed=envelopes_ok,store_manifest_sha256=store.manifest_sha256,regions=store.report['regions']),
        regions=dict(passed=regions_ok,expected_regions=coverage['expected_regions'],generated_regions=coverage['generated_regions'],
            complete_region_omissions=coverage['expected_regions']-coverage['generated_regions'],regions=coverage['regions'],configured_area_exclusions=coverage['configured_area_exclusions']),
        skins=dict(passed=all_skin,regions=skin_rows),grids=dict(passed=all_grid,regions=grid_rows),
        contacts=dict(passed=contacts_ok,intervals=contact_rows,actual_material_connection_graphs=graphs),
        collisions=dict(passed=envelopes_ok and all_skin and all_grid,
            method='whole_generated_triangles_in_actual_free_sections_or_unfolded_vertical_sheets_with_declared_vertical_tooth_contact_band',
            whole_grid_triangle_domain_audit=all_grid,whole_skin_triangle_domain_and_coordinate_mapping_audit=all_skin,
            free_envelope_admission_sha256=store.manifest_sha256,
            vertical_tooth_contact_penetration_mm=checkpoint['parameters']['support_teeth_upper_penetration_mm'],
            envelope_coordinate_error_bounds=store.report['coordinate_error_bounds'],
            scope='Geometric part/support inclusion and contact domains; open support sheets have no claimed solid volume.'))
    admission={}
    for key in KEYS:
        receipt=receipts[key]
        receipt.update(admission_schema=SCHEMA,admission_source_sha256=source_sha)
        if key in ['skins','grids','contacts','collisions']:
            receipt.update(continuous_interval_exact_admissions=exact_rows,
                continuous_interval_exact_admissions_passed=bool(exact_rows) and all(r['receipt']['passed'] for r in exact_rows),
                legacy_overlay_predicates_used_as_authority=False)
        receipt['status']='passed' if receipt['passed'] else 'rejected';receipt['input_sha256']=checkpoint['input_sha256']
        path=output/f'admission-{key}.json';path.write_text(compact_dumps(receipt,indent=2,allow_nan=False)+'\n')
        admission[key]=dict(status=receipt['status'],receipt=path.name,receipt_sha256=sha(path))
    if sha(__file__)!=source_sha:raise ValueError('Admission source changed during sealing')
    store.verify()
    admitted=all(item['status']=='passed' for item in admission.values())
    checkpoint.update(admission=admission,manufacturing_preparation_admitted=admitted)
    (output/'support-stage.json').write_text(compact_dumps(checkpoint,indent=2,allow_nan=False)+'\n')
    return admission,admitted
