"""Generate a prism region with combinatorial continuous sheets and exact bands."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import traceback
from types import SimpleNamespace

import numpy as np
import pyslm
import pyslm.support
import trimesh

SOURCE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from compact_json import dumps as compact_dumps
json=SimpleNamespace(loads=json.loads,dumps=compact_dumps)


def run(part_path,native_audit_path,roofs_path,source_index,parameters_path,output):
    from native_prism_case import load_case
    case=load_case(native_audit_path);case.verify();volume_path=case.final_npz
    if case.source_index!=source_index:raise ValueError('Native case belongs to a different overhang source')
    solid_sheets=continuous_interfaces=True
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    (output/'source').mkdir()
    names=['generate_prism_region_v4.py','continuous_prism_interfaces.py','exact_band_union_v2.py','continuous_combinatorial_interfaces.py','continuous_indexed_interfaces.py','indexed_combinatorial_interfaces.py','combinatorial_interfaces.py','exact_band_union_v3.py','compact_json.py','native_prism_case.py','interface_sources_prisms.py','interface_sources_prisms_v2.py','region_checkpoints.py','peripheral_skins.py','grid_intervals.py','exact_regions.py','prismatic_envelopes.py','material_connections.py','quantized_contacts.py','layer_schedule.py','zero_area_faces.py','interface_sources.py','solid_sheets.py','continuous_interfaces.py']
    identities={str(SOURCE/n):sha(SOURCE/n) for n in names}
    for name in names:shutil.copy2(SOURCE/name,output/'source'/name)
    contact_source=SOURCE.parent/'process-scanpath-audit-20261016/exact_contacts.py'
    identities[str(contact_source)]=sha(contact_source);shutil.copy2(contact_source,output/'source'/contact_source.name)
    both_source=SOURCE.parent/'process-scanpath-audit-20261016/exact_contacts_both.py'
    identities[str(both_source)]=sha(both_source);shutil.copy2(both_source,output/'source'/both_source.name)
    coverage_source=SOURCE.parent/'process-scanpath-audit-20261016/exact_zero_face_coverage.py'
    identities[str(coverage_source)]=sha(coverage_source);shutil.copy2(coverage_source,output/'source'/coverage_source.name)
    polygon_source=SOURCE.parent/'process-scanpath-audit-20261016/exact_polygon_coverage.py'
    identities[str(polygon_source)]=sha(polygon_source);shutil.copy2(polygon_source,output/'source'/polygon_source.name)
    holes_source=SOURCE.parent/'process-scanpath-audit-20261016/exact_intended_holes.py'
    identities[str(holes_source)]=sha(holes_source);shutil.copy2(holes_source,output/'source'/holes_source.name)
    band_source=SOURCE.parent/'process-scanpath-audit-20261016/exact_band_union.py'
    identities[str(band_source)]=sha(band_source);shutil.copy2(band_source,output/'source'/band_source.name)
    convex_source=SOURCE.parent/'process-scanpath-audit-20261016/exact_convex_union.py'
    identities[str(convex_source)]=sha(convex_source);shutil.copy2(convex_source,output/'source'/convex_source.name)
    halfplane_source=SOURCE.parent/'process-scanpath-audit-20261016/exact_convex_halfplanes.py'
    identities[str(halfplane_source)]=sha(halfplane_source);shutil.copy2(halfplane_source,output/'source'/halfplane_source.name)
    classifier=SOURCE.parent/'design-20261016/classify_mesh_contacts.py'
    identities[str(classifier)]=sha(classifier);shutil.copy2(classifier,output/'source'/classifier.name)
    snapshots={str(p):sha(p) for p in (output/'source').iterdir() if p.is_file()}
    # Import the immutable snapshot, so a later source edit cannot affect this run.
    sys.path.insert(0,str(output/'source'))
    import continuous_interfaces as continuous_module
    from continuous_indexed_interfaces import repair as prism_repair
    continuous_module.repair=prism_repair
    from peripheral_skins import geometry
    from exact_regions import GRID_PARAMETERS
    inputs={str(Path(p).resolve()):sha(p) for p in [part_path,volume_path,parameters_path,native_audit_path,roofs_path,case.original_raw_npz,case.schema_path]}
    parameters=json.loads(Path(parameters_path).read_text())['parameters']
    p=np.load(part_path,allow_pickle=False);v=np.load(volume_path,allow_pickle=False)
    part=pyslm.Part('carrier');part.setGeometry(trimesh.Trimesh(p['vertices'],p['faces'],process=False),fixGeometry=False,mergeVertices=False)
    sources=pyslm.support.utils.getOverhangMesh(part,parameters['overhang_angle_degrees'],True)
    generator=pyslm.support.GridBlockSupportGenerator()
    for attr,key in [('supportTeethHeight','support_teeth_height_mm'),('supportTeethTopLength','support_teeth_top_length_mm'),
                     ('supportTeethBottomLength','support_teeth_bottom_length_mm'),('supportTeethUpperPenetration','support_teeth_upper_penetration_mm'),
                     ('supportTeethBaseInterval','support_teeth_base_interval_mm'),('gridSpacing','support_grid_spacing_mm')]:
        setattr(generator,attr,parameters[key])
    generator.supportWallThickness=1.;generator.splineSimplificationFactor=None
    block=pyslm.support.GridBlockSupport(part,trimesh.Trimesh(v['vertices'],v['faces'],process=False),sources[source_index],True)
    from interface_sources_prisms_v2 import attach
    preparation=json.loads(Path(parameters_path).read_text());row=next(r for r in preparation['regions'] if r['source_index']==source_index)
    mask_path=Path(parameters_path).parent/row['mask']
    with np.load(case.original_raw_npz,allow_pickle=False) as raw:
        block.interfaceSourceReceipt=attach(block.supportVolume,v,raw,case.boolean_audit,roofs_path,mask_path,part_path,
            case.schema_path,case.final_to_original_raw_face)
    block.interfaceSourceReceipt.update(native_case_audit_sha256=sha(native_audit_path),
        native_case_reader_sha256=sha(SOURCE/'native_prism_case.py'))
    inputs[str(mask_path.resolve())]=sha(mask_path)
    case.verify()
    for name in GRID_PARAMETERS:setattr(block,name,getattr(generator,'_'+name))
    if continuous_interfaces and not solid_sheets:raise ValueError('Continuous interfaces require explicit full sheets')
    if solid_sheets:block.generateTrussGrid=False
    block.continuousFragmentedInterfaces=continuous_interfaces
    from layer_schedule import calendar
    block.exposureCalendar=calendar(float(part.geometry.bounds[1,2]),parameters['layer_height_mm'])
    from region_checkpoints import runtime_identity,block_identity,write_checkpoint
    runtime_before=runtime_identity();runtime_after=None;block_before=block_identity(block)
    started=time.monotonic()
    try:
        surface=geometry(block,diagnostic_contacts=True)
        # Preserve the old overlay measurements and declare the exact authority.
        block.skinCoverage['historical_support_strategy']=block.skinCoverage['support_strategy']
        block.skinCoverage['support_strategy']='continuous_domain_with_nonoverlapping_attested_edge_strips'
        for axis in block.gridCoverage['axes']:
            for plane in axis['planes']:
                plane['legacy_overlay_confinement_passed']=plane['whole_surface_outside_admitted_domain_area_mm2']==0
                plane['confinement_authority']='exact_intended_sweep_union'
        for component in block.skinCoverage['components']:
            infill=component['infill']
            infill['legacy_overlay_confinement_passed']=infill['outside_free_domain_and_contact_band_area_mm2']==0
            infill['confinement_authority']='exact_intended_sweep_union'
        np.savez_compressed(output/'support.npz',vertices=surface.vertices,faces=surface.faces,
            order=surface.face_attributes['order'],type=surface.face_attributes['type'])
        surface.export(output/'support.stl')
        report=dict(status='diagnostic_generated_contacts_unproven',surface_sha256=sha(output/'support.npz'),
            vertices=len(surface.vertices),faces=len(surface.faces),area_mm2=surface.area,
            peripheral_skin=block.skinCoverage,grid_coverage=block.gridCoverage)
        (output/'geometry-assessment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        from material_connections import connected_material
        graph=connected_material(surface.vertices,surface.faces,block.skinCoverage['support_surface_face_groups'])
        (output/'material-connections.json').write_text(json.dumps(graph,indent=2,allow_nan=False)+'\n')
        report['material_connections']=dict(status=graph['status'],receipt='material-connections.json',receipt_sha256=sha(output/'material-connections.json'))
        runtime_after=runtime_identity()
        if graph['status']=='passed':
            if not all(sha(p)==h for p,h in {**snapshots,**inputs}.items()):raise ValueError('Region sources or inputs changed before sealing')
            case.verify()
            sealed=write_checkpoint(output,block,graph,block_before,runtime_before,runtime_after,snapshots,source_index)
            sealed['additional_source_sha256']={name:sha(output/'source'/name) for name in ['generate_prism_region_v4.py','continuous_prism_interfaces.py','exact_band_union_v2.py','continuous_combinatorial_interfaces.py','continuous_indexed_interfaces.py','indexed_combinatorial_interfaces.py','combinatorial_interfaces.py','exact_band_union_v3.py','compact_json.py','native_prism_case.py','interface_sources_prisms.py','interface_sources_prisms_v2.py']}
            sealed['additional_source_sha256']['exact_band_union.py']=sha(output/'source/exact_band_union.py')
            sealed['additional_source_sha256']['exact_convex_union.py']=sha(output/'source/exact_convex_union.py')
            sealed['additional_source_sha256']['exact_convex_halfplanes.py']=sha(output/'source/exact_convex_halfplanes.py')
            sealed['runtime_hooks']=dict(continuous_interval_repair=dict(source='continuous_indexed_interfaces.py',sha256=sha(output/'source/continuous_indexed_interfaces.py'),frozen_repair_sha256=sha(output/'source/continuous_combinatorial_interfaces.py'),exact_source_line_index_sha256=sha(output/'source/indexed_combinatorial_interfaces.py'),intended_band_union_source_sha256=sha(output/'source/exact_band_union_v3.py')))
            sealed['native_case_audit_sha256']=sha(native_audit_path)
            (output/'region-checkpoint.json').write_text(json.dumps(sealed,indent=2,allow_nan=False)+'\n')
            report['region_checkpoint']=dict(receipt='region-checkpoint.json',receipt_sha256=sha(output/'region-checkpoint.json'),
                status='region_geometry_completed_no_global_admission')
    except Exception as error:
        report=dict(status='rejected',error_type=type(error).__name__,error=str(error),receipt=getattr(error,'receipt',None),
            traceback=traceback.format_exc())
    if runtime_after is None:runtime_after=runtime_identity()
    case.verify()
    report.update(source_index=source_index,seconds=time.monotonic()-started,source_sha256=identities,input_sha256=inputs,
        frozen_snapshot_sha256=snapshots,
        runtime_before=runtime_before,runtime_after=runtime_after,runtime_unchanged=runtime_before==runtime_after,
        original_source_files_unchanged=all(sha(p)==h for p,h in identities.items()),
        sources_and_inputs_unchanged=all(sha(p)==h for p,h in {**snapshots,**inputs}.items()))
    (output/'assessment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['part','native_audit','roofs','parameters','output']:parser.add_argument(name,type=Path)
    parser.add_argument('--source-index',type=int,required=True);args=parser.parse_args()
    report=run(args.part,args.native_audit,args.roofs,args.source_index,args.parameters,args.output)
    print(json.dumps({k:report[k] for k in ['status','seconds','source_index']}))
    sys.exit(0 if report.get('region_checkpoint') else 1)
