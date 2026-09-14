#!/usr/bin/env python3
"""Read-only C0-knot and real-seat ownership diagnosis of native gas domain 05.

An ArgumentAnalyzer C0 finding is retained, not equated to invalid BRep or a
leak. This does not waive mesh quality checks or qualify STEP/manufacturing.
"""
import argparse
import json
import math
from pathlib import Path
import resource
import sys
import time

import diagnose_gas_boolean as diagnostic

EXPECTED_DOMAIN='3f20f4c56a3f4bfd5c7f580302dfa08e160ebb13abc3c5217a98312cc48653f3'
OCCT_CONTINUITY_SOURCE='https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_9_3/src/BOPAlgo/BOPAlgo_ArgumentAnalyzer.cxx'


def diagnostic_mesh_attempt_allowed(report):
    """Narrow recorded C0 exception for a mesh ATTEMPT, not mesh acceptance."""
    native=report['native_check'];bop=report['original_native_BOP']
    entities=report['C0_entities'];ownership=report['ambiguous_face_ownership']
    return bool(native['BRep_valid_exact_method'] and native['topology_counts']['solid']==1
        and not bop['has_errors'] and bop['faults'] and set(bop['faults'])=={'BOPAlgo_GeomAbs_C0'}
        and entities and all(e['shape_kind']=='TopAbs_EDGE' and e['status']=='BOPAlgo_GeomAbs_C0'
            and e['curve']['C0_internal_knots'] and all(k['position_jump_native_numeric']==0.
                and k['tangent_angle_degrees'] is not None for k in e['curve']['C0_internal_knots']) for e in entities)
        and len(ownership)==4 and all(row['ownership_evidence_pass'] for row in ownership)
        and report['classified_boundary_assignment_complete'] and report['all_inputs_unchanged'])


def bspline_knots(curve, first, last):
    """One-sided local polynomial/rational evaluations, not finite differences."""
    from OCP.gp import gp_Pnt,gp_Vec
    from OCP.GeomAdaptor import GeomAdaptor_Curve
    from OCP.GCPnts import GCPnts_AbscissaPoint
    if not math.isfinite(first+last) or first>=last:
        raise ValueError('finite_increasing_trim_required')
    rows=[];degree=curve.Degree()
    for i in range(2,curve.NbKnots()):
        u=curve.Knot(i);multiplicity=curve.Multiplicity(i)
        if not first<u<last or multiplicity<degree:continue
        if multiplicity>degree:
            raise ValueError('discontinuous_curve_not_supported')
        pl,pr,vl,vr=gp_Pnt(),gp_Pnt(),gp_Vec(),gp_Vec()
        curve.LocalD1(u,i-1,i,pl,vl);curve.LocalD1(u,i,i+1,pr,vr)
        rows.append({'knot_index':i,'parameter':u,'multiplicity':multiplicity,
            'position_private':[pl.X(),pl.Y(),pl.Z()],
            'position_jump_native_numeric':pl.Distance(pr),
            'left_derivative_norm':vl.Magnitude(),'right_derivative_norm':vr.Magnitude(),
            'derivative_jump_norm':vl.Subtracted(vr).Magnitude(),
            'tangent_angle_degrees':math.degrees(vl.Angle(vr)) if min(vl.Magnitude(),vr.Magnitude())>0 else None})
    knots=[first]+[row['parameter'] for row in rows]+[last];spans=[]
    for a,b in zip(knots,knots[1:]):
        segment=curve.Copy();segment.Segment(a,b)
        poles=[segment.Pole(i) for i in range(1,segment.NbPoles()+1)]
        weights=[segment.Weight(i) for i in range(1,segment.NbPoles()+1)]
        if any(w<=0 or not math.isfinite(w) for w in weights):
            raise ValueError('positive_finite_weights_required_for_convex_pole_bounds')
        xyz=[[p.X(),p.Y(),p.Z()] for p in poles]
        bounds=[min(p[i] for p in xyz) for i in range(3)]+[max(p[i] for p in xyz) for i in range(3)]
        spans.append({'parameters':[a,b],
            'arc_length_numeric_quadrature_not_bound':GCPnts_AbscissaPoint.Length_s(GeomAdaptor_Curve(segment),a,b),
            'control_pole_bbox_private':bounds,
            'control_pole_box_diagonal_upper_bound_numeric':math.dist(bounds[:3],bounds[3:]),
            'positive_weights':True})
    return {'degree':degree,'trim':[first,last],'C0_internal_knots':rows,'spans':spans,
        'numerical_kernel_evaluation_not_physical_metrology':True,
        'curve_repaired_or_replaced':False}


def run(args):
    import OCP
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    from OCP.TopAbs import TopAbs_EDGE,TopAbs_FACE,TopAbs_REVERSED
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Curve,BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Cut
    started=time.monotonic();boundaries=diagnostic.boundaries;inspection=boundaries.inspection
    paths={'domain':args.run_dir/'domain.brep','builder_report':args.run_dir/'gas-domain-report.json',
        'classified_report':args.run_dir/'gas-domain-report-classified-v2.json',
        'module':args.module,'build':args.build,'registration':args.registration,
        'source':Path(__file__),'diagnostic_source':Path(diagnostic.__file__),
        'boundary_source':Path(boundaries.__file__)}
    hashes={k:inspection.digest(p) for k,p in paths.items()}
    builder=json.loads(paths['builder_report'].read_text())
    classified=json.loads(paths['classified_report'].read_text())
    if hashes['domain']!=EXPECTED_DOMAIN or hashes['domain']!=builder['exports']['domain_brep']['sha256']:
        raise ValueError('exact_domain05_provenance_required')
    if any(hashes[k]!=inspection.EXPECTED[k] for k in ('module','build','registration')):
        raise ValueError('exact_module_build_registration_required')
    if (classified['exports']!=builder['exports'] or
            [(r['id'],r['sha256']) for r in classified['boundary_faces']]!=[(r['id'],r['sha256']) for r in builder['boundary_faces']]):
        raise ValueError('classified_receipt_must_bind_identical_native_geometry_and_faces')
    if args.output.exists() or args.output.is_symlink():raise FileExistsError(args.output)
    args.output.mkdir(parents=True,mode=0o700)
    report={'schema':'m64-native-gas-domain-advisories/v1','status':'running','inputs_sha256':hashes,
        'OCP_version':OCP.__version__,'units':'scan_units_under_unverified_1_unit_per_mm_hypothesis',
        'OCCT_ArgumentAnalyzer_continuity_source':OCCT_CONTINUITY_SOURCE,
        'C0_semantics':'underlying_curve_or_surface_continuity_not_dihedral_angle_between_faces',
        'geometry_modified':False,'tolerance_modified':False,'CFD_executed':False,
        'mesh_executed':False,'manufacturing_authorized':False,
        'allow_diagnostic_meshing':False,'BOP_no_faults':False,
        'classified_boundary_assignment_complete':classified['gates']['boundary_assignment_complete'],
        'original_native_BOP':builder['native_BOP'],'original_STEP_BOP':builder['STEP_BOP']}
    def save(label):
        report['elapsed_seconds']=time.monotonic()-started
        diagnostic.local.ports.save(args.output/(label+'.json'),report)
    save('preregistration')
    cad=inspection.design.CAD()
    try:
        domain=diagnostic.local.read_native(paths['domain'])
        report['native_check'],indexed=diagnostic.inspect_native(cad,domain)
        analyzer=BOPAlgo_ArgumentAnalyzer();analyzer.SetShape1(domain)
        analyzer.ContinuityMode=True;analyzer.Perform();report['C0_entities']=[]
        for result in analyzer.GetCheckResult():
            for shape in result.GetFaultyShapes1():
                row={'status':str(result.GetCheckStatus()).split('.')[-1],'shape_kind':str(shape.ShapeType()).split('.')[-1]}
                if shape.ShapeType()!=TopAbs_EDGE:
                    row['edge_only_diagnostic_supported']=False;report['C0_entities'].append(row);continue
                edge=TopoDS.Edge_s(shape);row['edge_id']=indexed['edge'].FindIndex(edge)
                row['edge_location_identity']=edge.Location().IsIdentity()
                if not row['edge_location_identity']:
                    raise ValueError('non_identity_edge_location_requires_explicit_world_transform')
                curve=BRepAdaptor_Curve(edge);base=curve.Curve().Curve()
                row['curve_type']=str(curve.GetType()).split('.')[-1]
                if not hasattr(base,'NbKnots'):raise ValueError('non_bspline_C0_edge_requires_separate_diagnostic')
                row['curve']=bspline_knots(base,curve.FirstParameter(),curve.LastParameter())
                row['adjacent_faces']=[]
                for i in range(1,indexed['face'].Extent()+1):
                    if cad.indexed(indexed['face'].FindKey(i),TopAbs_EDGE).Contains(edge):
                        stored=builder['boundary_faces'][i-1]
                        row['adjacent_faces'].append({'face_id':i,'role':stored['role'],'source_match':stored['source_match']})
                report['C0_entities'].append(row)
        save('continuity-checkpoint')
        registration=json.loads(paths['registration'].read_text())
        if registration['registration']!={'scale_scan_units_per_mm_hypothesis':1.,'rotation_Z_deg_hypothesis':-90.,'translation_Z_hypothesis':3.}:
            raise ValueError('fixed_one_time_registration_required')
        module=cad.read_step(paths['module']);solids=cad.indexed(module,cad.TopAbs_SOLID)
        ids={r['name']:r['imported_module_solid_id'] for r in registration['components_imported_from_exact_STEP']}
        report['ambiguous_face_ownership']=[]
        for stored in builder['boundary_faces']:
            if stored['role']!='ambiguous':continue
            if {r['role'] for r in stored['source_match']}!={'walls_seat','walls_chamber'}:
                raise ValueError('unexpected_physical_ownership_conflict')
            seat_matches=[r for r in stored['source_match'] if r['role']=='walls_seat']
            if len(seat_matches)!=1:raise ValueError('unique_real_seat_face_required')
            name,face_id=seat_matches[0]['source'].rsplit('_face_',1)
            seat=boundaries.registered(cad,solids.FindKey(ids[name]))
            seat_face=TopoDS.Face_s(cad.indexed(seat,TopAbs_FACE).FindKey(int(face_id)))
            gas_face=TopoDS.Face_s(indexed['face'].FindKey(stored['id']))
            surface=BRepAdaptor_Surface(gas_face,False);ss=BRepAdaptor_Surface(seat_face,False)
            if surface.GetType()!=GeomAbs_Plane or ss.GetType()!=GeomAbs_Plane:
                raise ValueError('only_reported_coplanar_seat_lands_expected')
            ng=surface.Plane().Axis().Direction();ns=ss.Plane().Axis().Direction()
            if gas_face.Orientation()==TopAbs_REVERSED:ng.Reverse()
            if seat_face.Orientation()==TopAbs_REVERSED:ns.Reverse()
            common=boundaries.native_audit.boolean(BRepAlgoAPI_Common,gas_face,seat_face)
            residual=boundaries.native_audit.boolean(BRepAlgoAPI_Cut,gas_face,seat_face)
            row={'face_id':stored['id'],'actual_component':name,'actual_component_face_id':int(face_id),
                'source_face_sha256':stored['sha256'],'gas_face_area':cad.area(gas_face),
                'common_area':cad.area(common),'gas_minus_seat_face_remaining_faces':cad.indexed(residual,TopAbs_FACE).Extent(),
                'gas_minus_seat_face_remaining_edges':cad.indexed(residual,TopAbs_EDGE).Extent(),
                'outward_normal_dot':ng.Dot(ns),'original_matches_retained':stored['source_match'],
                'recommended_physical_role':'walls_seat','chamber_tool_is_not_a_material':True}
            row['ownership_evidence_pass']=bool(row['gas_minus_seat_face_remaining_faces']==0
                and row['gas_minus_seat_face_remaining_edges']==0
                and abs(row['common_area']-row['gas_face_area'])<=max(1e-8,1e-7*row['gas_face_area'])
                and row['outward_normal_dot']<-1+1e-12
                and classified['boundary_faces'][stored['id']-1]['role']=='walls_seat')
            report['ambiguous_face_ownership'].append(row);save('ownership-face-%04d-checkpoint'%stored['id'])
        report['status']='read_only_advisory_diagnosis_complete'
        report['mesh_pilot_scope']='continuous_C0_boundary_may_be_meshed; retain knots and verify resulting boundary and volume mesh; no universal_C1_requirement'
        report['mesh_pilot_actual_admissibility']='pending_native_mesher_and_independent_mesh_quality_checks'
        report['STEP_not_promoted']=True
    except Exception as exc:
        report['status']='partial_advisory_diagnosis';report['error']=type(exc).__name__+': '+str(exc)
    report['all_inputs_unchanged']=all(inspection.digest(p)==hashes[k] for k,p in paths.items())
    if report['status']=='read_only_advisory_diagnosis_complete':
        report['allow_diagnostic_meshing']=diagnostic_mesh_attempt_allowed(report)
    report['mesh_attempt_conditions']=[
        'Use exact native domain SHA, not STEP with distinct p-curve findings.',
        'Keep all C0 internal knot locations and parameter spans in private mesh evidence.',
        'Verify knot representation, surface conformity, topology and volume-cell quality on resulting mesh.',
        'Preserve inlet/outlet, real walls and separately named idealized fixture seals.',
        'No automatic CFD execution, performance, thermal, mechanical or manufacturing qualification.']
    report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
    save('report')
    print(json.dumps({'status':report['status'],'elapsed_seconds':report['elapsed_seconds'],'error':report.get('error')}))
    return 0 if report['status']=='read_only_advisory_diagnosis_complete' else 3


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run-dir','module','build','registration','output'):parser.add_argument('--'+name,type=Path,required=True)
    resource.setrlimit(resource.RLIMIT_CPU,(300,305))
    raise SystemExit(run(parser.parse_args()))
