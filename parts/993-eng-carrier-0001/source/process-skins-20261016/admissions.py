"""Seal six separate geometry admissions; generation alone cannot pass them."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh

KEYS=('envelopes','regions','skins','grids','contacts','collisions')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def complete_contacts(rows,expected_intervals,expected_components,connected=False):
    intervals=[r for r in rows if r.get('kind')=='required_free_interval']
    components=[r for r in rows if r.get('kind')=='generated_material_component']
    return (expected_intervals>0 and expected_components>0 and
        [r['domain_index'] for r in intervals]==list(range(expected_intervals)) and
        [r['component_index'] for r in components]==list(range(expected_components)) and
        all(r.get('passed') and (r['upper_contact_trace_mm']>0 or not r.get('upper_interface_required',True)) and
            (r['lower_contact_trace_mm']>0 or not r.get('lower_interface_required',True)) for r in intervals) and
        (connected or all(r.get('passed') and r['upper_contact_trace_mm']>0 and r['lower_contact_trace_mm']>0 for r in components)))

def seal(output,checkpoint,store):
    output=Path(output);store.verify();supports=checkpoint['supports'];coverage=json.loads((output/'region-coverage.json').read_text())
    regions_ok=bool(coverage.get('region_projection_admission_passed') and coverage['expected_regions']==coverage['generated_regions']==len(supports)==store.report['expected_regions'])
    skin_rows=[];grid_rows=[];contact_rows=[];graphs=[]
    all_skin=all_grid=bool(supports) and len(supports)==store.report['expected_regions']
    for support in supports:
        skin=support.get('peripheral_skin') or {};grid=support.get('grid_coverage') or {}
        graph=skin.get('material_connection_graph') or {};groups=skin.get('support_surface_face_groups',[])
        with np.load(output/f"support-{support['index']:03d}.npz",allow_pickle=False) as mesh:
            geometry_sha=hashlib.sha256(mesh['vertices'].tobytes()+mesh['faces'].tobytes()).hexdigest()
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
                f['outside_free_domain_and_contact_band_area_mm2']==0 and
                complete_contacts(f['interface_contacts'],f['required_free_intervals'],f['generated_material_components'],connected))
            contact_rows.extend(dict(region=support['index'],support_surface_kind='skin',component=c['index'],**r) for r in f['interface_contacts'])
        axes=grid.get('axes',[]);grid_ok=bool(grid.get('status')=='passed' and len(axes)==2)
        for axis in axes:
            grid_ok &= axis['expected_planes']==axis['generated_planes']==len(axis['planes']) and bool(axis['planes'])
            for plane in axis['planes']:
                grid_ok &= (plane.get('passed') and plane['whole_surface_outside_admitted_domain_area_mm2']==0 and
                    complete_contacts(plane['contacts'],plane['required_free_intervals'],plane['generated_material_components'],connected))
                contact_rows.extend(dict(region=support['index'],support_surface_kind='grid',axis=plane['fixed_axis'],order=plane['order'],**r) for r in plane['contacts'])
        all_skin &= skin_ok;all_grid &= grid_ok
        skin_rows.append(dict(region=support['index'],passed=bool(skin_ok),receipt=skin))
        grid_rows.append(dict(region=support['index'],passed=bool(grid_ok),receipt=grid))
    contacts_ok=bool(contact_rows) and all(g['passed'] for g in graphs) and all(r.get('passed') and
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
        receipt=receipts[key];receipt['status']='passed' if receipt['passed'] else 'rejected';receipt['input_sha256']=checkpoint['input_sha256']
        path=output/f'admission-{key}.json';path.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
        admission[key]=dict(status=receipt['status'],receipt=path.name,receipt_sha256=sha(path))
    admitted=all(item['status']=='passed' for item in admission.values())
    checkpoint.update(admission=admission,manufacturing_preparation_admitted=admitted)
    (output/'support-stage.json').write_text(json.dumps(checkpoint,indent=2,allow_nan=False)+'\n')
    return admission,admitted
