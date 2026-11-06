#!/usr/bin/env python3
"""Editable documentary point/plane-wire references, never registered body CAD."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from pxr import Gf, Sdf, Usd, UsdGeom, UsdUtils, Vt

OWNER = 'catalog/measurements/MEAS-OWNER-964-FRAME-20261105.json'
AMENDMENT = 'twins/964-chassis/body-contact-alternatives-20261106/mi-b-width-correction.json'
FLOOR = 'twins/964-chassis/dimensional-correction-20261106/scan-floor-audit.json'
PIN = {OWNER: 'ecc7ff9e64b90e19545019e2e1a2ea67c8df47f966ac325783306c6af1976b7c',
       AMENDMENT: '0e31ae106af5a321e14975f9e834a2b80d86b8db1ff99947d6144afc0e18f604',
       FLOOR: '13221b1f7c85f1a7416c8c6b706f04e48b311868d2274a34df0a04c5c568652f'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
pack = lambda rows, fmt: b''.join(struct.pack(fmt, *p) for p in rows)


def attr(prim, name, kind, value):
    prim.CreateAttribute(name, kind, custom=True).Set(value)


def new_stage(path, frame, description):
    stage = Usd.Stage.CreateNew(str(path)); root = UsdGeom.Xform.Define(stage, '/'+frame)
    stage.SetDefaultPrim(root.GetPrim()); UsdGeom.SetStageMetersPerUnit(stage, .001)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.GetRootLayer().documentation = description+' No inter-frame registration, physical geometry or engineering approval.'
    attr(root.GetPrim(), 'reference:frame', Sdf.ValueTypeNames.String, frame)
    attr(root.GetPrim(), 'reference:registrationAdmitted', Sdf.ValueTypeNames.Bool, False)
    return stage


def build(root, output):
    if output.exists(): raise FileExistsError('Use a fresh output directory')
    for name, expected in PIN.items():
        if sha(root/name) != expected: raise ValueError('Changed source: '+name)
    owner = json.loads((root/OWNER).read_text()); amendment = json.loads((root/AMENDMENT).read_text())
    floor = json.loads((root/FLOOR).read_text()); rows = []; checks = []; stages = {}
    descriptions = {'CH_parts_on': 'CH point5 X origin, rearward X, unsigned half-width expanded as plus/minus; printed height datum setup unknown. Millimetres interpreted; unit label absent. Parts on.',
                    'CH_parts_removed': 'CH point5 X origin, rearward X, unsigned half-width expanded as plus/minus; printed height datum setup unknown. Millimetres interpreted; unit label absent. Parts removed.',
                    'Mi_source': 'Mi F X origin, rearward X, printed centreline and datum line; millimetres by explicit wheelbase context. Contact states remain individually labelled. Plus/minus does not assign physical sides.'}
    output.mkdir(parents=True)
    for name, description in descriptions.items(): stages[name] = new_stage(output/(name+'.usda'), name, description)
    for entry in owner['declared_values']:
        detail = entry['details']
        if detail.get('kind') != 'source_local_coordinate_components': continue
        value_id = entry['value_id']; original = dict(detail['components']); effective = dict(original)
        frame = 'CH_'+detail['assembly_state'] if value_id.startswith('MNL-FD964-CH-') else 'Mi_source'
        overlay = None
        if value_id in ('MNL-FD964-MI-B-BOLT', 'MNL-FD964-MI-B-FRAME'):
            if detail['source_file_sha256'] != amendment['source_sha256']: raise ValueError('Mi B source mismatch')
            overlay = {'path': AMENDMENT, 'sha256': PIN[AMENDMENT], 'applied_to_width': False,
                       'scope': 'Bolt-head width only; removed-parts frame equivalence is not admitted.'}
            if value_id.endswith('-BOLT'):
                if detail['contact'] != 'bolt_head' or detail['coordinate_frame'] != 'Mi_F_origin_datum_line': raise ValueError('Mi B state mismatch')
                if amendment['source_only_half_width']*2 != amendment['combined_equal_opposed_span']: raise ValueError('Mi B convention mismatch')
                effective['half_width'] = amendment['source_only_half_width']; overlay['applied_to_width'] = True
        x = effective['x_relative_to_point5' if frame.startswith('CH_') else 'x_relative_to_F']; y = effective['half_width']; z = effective['height']
        points = [] if y is None else [[x,y,z],[x,-y,z]]
        row = {'value_id': value_id, 'source_id': entry['source_id'], 'frame': frame,
               'original_components': original, 'effective_components': effective, 'amendment': overlay,
               'source_definition': entry['description'], 'source_details': detail,
               'representation': 'projection_XZ_only_no_3D_location' if y is None else 'documentary_equal_side_pair',
               'points_mm': points, 'side_placeholders': [] if y is None else ['plus','minus'],
               'physical_contact_or_donor_registration_admitted': False}
        stage = stages[frame]; path = '/'+frame+'/'+value_id.replace('-','_')
        prim = UsdGeom.Scope.Define(stage, path).GetPrim() if y is None else UsdGeom.Points.Define(stage, path).GetPrim()
        attr(prim, 'reference:sourceValueId', Sdf.ValueTypeNames.String, value_id)
        attr(prim, 'reference:rowJson', Sdf.ValueTypeNames.String, json.dumps(row, sort_keys=True))
        if y is None:
            attr(prim, 'reference:projectionXZ', Sdf.ValueTypeNames.Double2, Gf.Vec2d(x,z))
        else:
            UsdGeom.Points(prim).CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in points]))
            attr(prim, 'reference:sidePlaceholders', Sdf.ValueTypeNames.StringArray, ['plus','minus'])
        rows.append(row)
    if len(rows) != 37 or len({r['value_id'] for r in rows}) != 37: raise ValueError('Coordinate-row coverage changed')
    plane = next(p for p in floor['patches'] if p['name']=='CombinedExteriorInspectionCrops')
    diagnostic = plane['plane_diagnostic']; n = diagnostic['normal_in_provisional_frame']; d = diagnostic['offset_d_in_n_dot_p_plus_d_equals_zero']
    scan = new_stage(output/'Scan_provisional.usda', 'Scan_provisional', 'Independent original scan provisional tyre/symmetry frame. Two unfilled fitted-plane crop-domain outlines; not physical panel perimeters or original interior floor.')
    wire = UsdGeom.BasisCurves.Define(scan, '/Scan_provisional/FittedPlaneCropDomains'); corners = []
    for box in plane['selection_bounds_provisional_frame_mm']:
        x0,x1,y0,y1,_,_ = box
        for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]: corners.append([x,y,-(n[0]*x+n[1]*y+d)/n[2]])
    wire.CreateTypeAttr('linear'); wire.CreateCurveVertexCountsAttr([5,5]); wire.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in corners]))
    attr(wire.GetPrim(), 'reference:exactCornersMm', Sdf.ValueTypeNames.Double3Array, Vt.Vec3dArray([Gf.Vec3d(*p) for p in corners]))
    attr(wire.GetPrim(), 'reference:planeNormal', Sdf.ValueTypeNames.Double3, Gf.Vec3d(*n)); attr(wire.GetPrim(), 'reference:planeD', Sdf.ValueTypeNames.Double, d)
    attr(wire.GetPrim(), 'reference:sourceAuditSha256', Sdf.ValueTypeNames.String, PIN[FLOOR]); stages['Scan_provisional'] = scan
    for frame, stage in stages.items():
        stage.GetRootLayer().Save(); reopened = Usd.Stage.Open(str(output/(frame+'.usda')))
        if not reopened or UsdGeom.GetStageMetersPerUnit(reopened)!=.001: raise ValueError('Stage/frame metadata failed')
        if any(p.GetTypeName() in ('Mesh','Sphere','Cube') or p.HasAttribute('xformOp:transform') for p in reopened.Traverse()): raise ValueError('Unexpected geometry/registration')
        for row in [r for r in rows if r['frame']==frame]:
            prim = reopened.GetPrimAtPath('/'+frame+'/'+row['value_id'].replace('-','_'))
            if json.loads(prim.GetAttribute('reference:rowJson').Get()) != row: raise ValueError('Source row readback mismatch')
            if prim.GetAttribute('reference:sourceValueId').Get()!=row['value_id']: raise ValueError('Source ID readback mismatch')
            if row['points_mm'] and pack(UsdGeom.Points(prim).GetPointsAttr().Get(),'<3f')!=pack(row['points_mm'],'<3f'): raise ValueError('Point bits changed')
            if not row['points_mm']:
                if prim.GetTypeName()!='Scope' or prim.HasAttribute('points'): raise ValueError('Unknown width became XYZ')
                projection=prim.GetAttribute('reference:projectionXZ').Get(); values=row['effective_components']
                if tuple(projection)!=(values['x_relative_to_F'],values['height']): raise ValueError('Projection readback changed')
        if frame=='Scan_provisional':
            prim = reopened.GetPrimAtPath('/Scan_provisional/FittedPlaneCropDomains')
            if pack(prim.GetAttribute('reference:exactCornersMm').Get(),'<3d')!=pack(corners,'<3d'): raise ValueError('Plane corner double bits changed')
            if pack(UsdGeom.BasisCurves(prim).GetPointsAttr().Get(),'<3f')!=pack(corners,'<3f'): raise ValueError('Wire point bits changed')
        validator = UsdUtils.ComplianceChecker(); validator.CheckCompliance(str(output/(frame+'.usda')))
        errors = list(validator.GetErrors()); failed = list(validator.GetFailedChecks())
        if errors or failed: raise ValueError('USD compliance failures: '+repr(errors+failed))
        checks.append({'frame':frame,'file':frame+'.usda','sha256':sha(output/(frame+'.usda')),'point_rows':sum(r['frame']==frame and bool(r['points_mm']) for r in rows),'projection_only_rows':sum(r['frame']==frame and not r['points_mm'] for r in rows),'USD_compliance_errors':errors,'USD_compliance_failed_checks':failed,'USD_compliance_warnings':list(validator.GetWarnings())})
    if any(sha(root/name)!=expected for name,expected in PIN.items()): raise ValueError('Source changed during build')
    result = {'python':sys.version,'OpenUSD_version':list(Usd.GetVersion()),'source_hashes_before_after_equal':True,'classification':'editable_source_reference_data_not_a_body_part_or_registered_coque','units':'mm_by_each_source_interpretation','source_sha256':PIN,'builder_sha256':sha(__file__),'rows':rows,'stages':checks,'coordinate_rows':37,'expanded_point_count':sum(len(r['points_mm']) for r in rows),'projection_only_rows':sum(not r['points_mm'] for r in rows),'scan_plane':{'source_patch':plane['name'],'normal':n,'d':d,'crop_domain_corners_mm':corners,'domain_is_not_physical_boundary':True},'all_source_row_values_IDs_and_point_bits_readback_equal':True,'frames_registered_or_assembled':False,'new_physical_geometry':False,'native_omniverse_or_SimReady_or_physics_claim':False,'physical_fit_strength_or_manufacturing_approval':False}
    (output/'source-reference.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'rows':37,'points':result['expanded_point_count'],'projection_only':result['projection_only_rows'],'stages':len(stages),'manifest_sha256':sha(output/'source-reference.json')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--root',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); build(args.root.resolve(),args.output.resolve())
