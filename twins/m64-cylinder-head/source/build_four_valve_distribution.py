#!/usr/bin/env python3
"""Build an independent, explicitly provisional four-valve design assembly.

No scan, F53 geometry or certified engine interfaces are read. Coordinates and
lengths belong to this new millimetre design frame, not to uncertified scan units.
Native stages are bounded separately; no springs or cylinder-head body are made.
"""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import resource


SWINDON = 'https://swindonpowertrain.com/wp-content/uploads/2025/10/M64-24V-Cylinder-Head-Kit-Product-Sheet-0923.pdf'
MAHLE = 'https://www.mahle-aftermarket.com/media/homepage/facelift/media-center/product-catalogs/mahle_valve_train_components_catalog_2025_screen_v002.pdf'


@dataclass(frozen=True)
class Parameters:
    bore_mm: float = 100.
    intake_diameter_mm: float = 40.
    exhaust_diameter_mm: float = 33.
    intake_max_lift_mm: float = 11.5
    exhaust_max_lift_mm: float = 9.6
    bank_inclination_deg: float = 8.
    intake_x_mm: float = -19.5
    exhaust_x_mm: float = 22.
    pair_half_spacing_mm: float = 22.5
    seat_envelope_minimum_gap_design_mm: float = 1.5
    seat_angle_from_transverse_plane_deg: float = 45.
    seat_contact_radial_width_mm: float = 1.
    valve_margin_radial_mm: float = .5
    valve_head_axial_margin_mm: float = 1.5
    seat_outer_radial_allowance_mm: float = 1.5
    seat_axial_thickness_mm: float = 5.5
    stem_diameter_mm: float = 6.
    intake_guide_diametral_clearance_mm: float = .03
    exhaust_guide_diametral_clearance_mm: float = .04
    guide_outer_diameter_mm: float = 11.
    guide_start_above_gauge_mm: float = 20.
    guide_length_mm: float = 35.
    stem_tip_above_gauge_mm: float = 82.
    conical_neck_start_radius_mm: float = 6.
    conical_neck_start_z_mm: float = 5.
    cylindrical_stem_start_z_mm: float = 9.

    def validate(self):
        for name, value in asdict(self).items():
            if not math.isfinite(value): raise ValueError(f'nonfinite {name}')
        if not 0 <= self.bank_inclination_deg < 35: raise ValueError('inclination out of design range')
        if not self.intake_x_mm < 0 < self.exhaust_x_mm: raise ValueError('banks must straddle axis')
        if not 20 < self.seat_angle_from_transverse_plane_deg < 70: raise ValueError('invalid seat angle')
        for name, value in asdict(self).items():
            if name not in ('intake_x_mm', 'bank_inclination_deg') and value <= 0:
                raise ValueError(f'nonpositive {name}')
        if self.guide_outer_diameter_mm <= self.stem_diameter_mm + max(self.intake_guide_diametral_clearance_mm, self.exhaust_guide_diametral_clearance_mm):
            raise ValueError('guide wall not positive')
        if self.stem_tip_above_gauge_mm - max(self.intake_max_lift_mm, self.exhaust_max_lift_mm) <= self.guide_start_above_gauge_mm + self.guide_length_mm:
            raise ValueError('stem loses full guide engagement at selected maximum lift')
        for diameter in (self.intake_diameter_mm, self.exhaust_diameter_mm):
            radius = diameter/2
            if radius - self.valve_margin_radial_mm - self.seat_contact_radial_width_mm <= self.conical_neck_start_radius_mm:
                raise ValueError('seat band encroaches on neck')
        return self


def valve_specs(p):
    return [{'name': f'{kind}_{index+1}', 'kind': kind, 'center': [x, sign*p.pair_half_spacing_mm, 0.],
             'axis_angle_deg': math.copysign(p.bank_inclination_deg, x), 'diameter_mm': diameter,
             'max_lift_mm': lift, 'guide_diametral_clearance_mm': clearance}
            for kind, x, diameter, lift, clearance in (
                ('intake', p.intake_x_mm, p.intake_diameter_mm, p.intake_max_lift_mm, p.intake_guide_diametral_clearance_mm),
                ('exhaust', p.exhaust_x_mm, p.exhaust_diameter_mm, p.exhaust_max_lift_mm, p.exhaust_guide_diametral_clearance_mm))
            for index, sign in enumerate((-1, 1))]


def lift_states(p):
    states = [{'name': 'closed', 'intake_mm': 0., 'exhaust_mm': 0.}]
    states += [{'name': f'simultaneous_{int(100*fraction)}pct', 'intake_mm': fraction*p.intake_max_lift_mm,
                'exhaust_mm': fraction*p.exhaust_max_lift_mm} for fraction in (.25, .5, .75, 1.)]
    return states + [{'name': 'intake_only_max', 'intake_mm': p.intake_max_lift_mm, 'exhaust_mm': 0.},
                     {'name': 'exhaust_only_max', 'intake_mm': 0., 'exhaust_mm': p.exhaust_max_lift_mm}]


def profiles(p, spec):
    r = spec['diameter_mm']/2; slope = math.tan(math.radians(p.seat_angle_from_transverse_plane_deg))
    contact_outer = r-p.valve_margin_radial_mm
    contact_inner = contact_outer-p.seat_contact_radial_width_mm
    zlo, zhi = (r-contact_outer)*slope, (r-contact_inner)*slope
    valve = [(0.,-p.valve_head_axial_margin_mm), (r,-p.valve_head_axial_margin_mm), (r,0.),
             (contact_inner,zhi), (p.conical_neck_start_radius_mm,p.conical_neck_start_z_mm),
             (p.stem_diameter_mm/2,p.cylindrical_stem_start_z_mm),
             (p.stem_diameter_mm/2,p.stem_tip_above_gauge_mm), (0.,p.stem_tip_above_gauge_mm)]
    # Continuing the seat cone inward avoids an unsupported knife edge; only
    # [contact_inner, contact_outer] is coincident with the valve seating band.
    throat = contact_inner-.7
    seat = [(contact_outer,zlo), (r+p.seat_outer_radial_allowance_mm,zlo),
            (r+p.seat_outer_radial_allowance_mm,zlo+p.seat_axial_thickness_mm),
            (throat,zlo+p.seat_axial_thickness_mm), (throat,(r-throat)*slope), (contact_inner,zhi)]
    gi = (p.stem_diameter_mm+spec['guide_diametral_clearance_mm'])/2
    go = p.guide_outer_diameter_mm/2; z = p.guide_start_above_gauge_mm
    guide = [(gi,z), (go,z), (go,z+p.guide_length_mm), (gi,z+p.guide_length_mm)]
    return {'valve': valve, 'seat': seat, 'guide': guide}, (contact_inner,contact_outer)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class CAD:
    def __init__(self):
        from OCP.BRep import BRep_Builder
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol, BRepPrimAPI_MakeCylinder
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Section
        from OCP.BRepGProp import BRepGProp
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepExtrema import BRepExtrema_DistShapeShape
        from OCP.GProp import GProp_GProps
        from OCP.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Ax2, gp_Trsf, gp_Vec, gp_Pln
        from OCP.TopoDS import TopoDS_Compound, TopoDS
        from OCP.TopAbs import TopAbs_SOLID, TopAbs_EDGE, TopAbs_FACE
        from OCP.TopExp import TopExp
        from OCP.TopTools import TopTools_IndexedMapOfShape
        self.__dict__.update({name:value for name,value in locals().items() if name not in ('self','__class__')})

    def valid(self, shape):
        analyzer=self.BRepCheck_Analyzer(shape,True);analyzer.SetExactMethod(True)
        return analyzer.IsValid()

    def indexed(self, shape, kind):
        m=self.TopTools_IndexedMapOfShape();self.TopExp.MapShapes_s(shape,kind,m);return m

    def volume(self, shape):
        props=self.GProp_GProps();self.BRepGProp.VolumeProperties_s(shape,props);return abs(props.Mass())

    def area(self, shape):
        props=self.GProp_GProps();self.BRepGProp.SurfaceProperties_s(shape,props);return props.Mass()

    def revolve(self, profile):
        polygon=self.BRepBuilderAPI_MakePolygon()
        for r,z in profile: polygon.Add(self.gp_Pnt(r,0.,z))
        polygon.Close();face=self.BRepBuilderAPI_MakeFace(polygon.Wire()).Face()
        maker=self.BRepPrimAPI_MakeRevol(face,self.gp_Ax1(self.gp_Pnt(0,0,0),self.gp_Dir(0,0,1)),2*math.pi,True)
        shape=maker.Shape()
        if not self.valid(shape) or self.indexed(shape,self.TopAbs_SOLID).Extent()!=1: raise ValueError('invalid revolved component')
        return shape

    def pose(self, shape, spec, lift=0.):
        angle=math.radians(spec['axis_angle_deg']);transform=self.gp_Trsf()
        transform.SetRotation(self.gp_Ax1(self.gp_Pnt(0,0,0),self.gp_Dir(0,1,0)),angle)
        x,y,z=spec['center'];transform.SetTranslationPart(self.gp_Vec(x-lift*math.sin(angle),y,z-lift*math.cos(angle)))
        return self.BRepBuilderAPI_Transform(shape,transform,True).Shape()

    def compound(self, shapes):
        compound=self.TopoDS_Compound();builder=self.BRep_Builder();builder.MakeCompound(compound)
        for shape in shapes: builder.Add(compound,shape)
        return compound

    def operation(self, operation, first, second):
        job=operation(first,second)
        if not job.IsDone(): raise RuntimeError('Boolean operation did not complete')
        return job.Shape()

    def distance(self, first, second):
        job=self.BRepExtrema_DistShapeShape(first,second)
        if not job.IsDone(): raise RuntimeError('distance did not complete')
        return job.Value()

    def write_step(self, path, parts):
        from OCP.TDocStd import TDocStd_Document
        from OCP.TCollection import TCollection_ExtendedString
        from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
        from OCP.TDataStd import TDataStd_Name
        from OCP.STEPCAFControl import STEPCAFControl_Writer
        from OCP.STEPControl import STEPControl_AsIs
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.Quantity import Quantity_Color,Quantity_TOC_RGB
        from OCP.TopLoc import TopLoc_Location
        doc=TDocStd_Document(TCollection_ExtendedString('four_valve_design'))
        shapes=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main());colors=XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
        root=shapes.NewShape();TDataStd_Name.Set_s(root,TCollection_ExtendedString('M64_candidate_distribution_NOT_RELEASED'))
        palette={'valve':(.66,.73,.80),'seat':(.83,.56,.18),'guide':(.18,.58,.53)}
        for part in parts:
            label=shapes.AddShape(part['shape'],False);TDataStd_Name.Set_s(label,TCollection_ExtendedString(part['name']))
            colors.SetColor(label,Quantity_Color(*palette.get(part['role'],(.4,.4,.4)),Quantity_TOC_RGB),XCAFDoc_ColorType.XCAFDoc_ColorGen)
            shapes.AddComponent(root,label,TopLoc_Location())
        shapes.UpdateAssemblies();writer=STEPCAFControl_Writer();writer.SetNameMode(True);writer.SetColorMode(True)
        if not writer.Transfer(doc,STEPControl_AsIs) or writer.Write(str(path))!=IFSelect_RetDone:
            raise RuntimeError('STEP assembly export failed')

    def read_step(self,path):
        from OCP.STEPControl import STEPControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        reader=STEPControl_Reader()
        if reader.ReadFile(str(path))!=IFSelect_RetDone: raise RuntimeError('STEP import failed')
        reader.TransferRoots();return reader.OneShape()


def construct(cad,p,state):
    parts=[]
    for spec in valve_specs(p):
        shapes,_=profiles(p,spec)
        for role,profile in shapes.items():
            lift=state[spec['kind']+'_mm'] if role=='valve' else 0.
            parts.append({'name':spec['name']+'_'+role,'role':role,'spec':spec,
                          'shape':cad.pose(cad.revolve(profile),spec,lift)})
    return parts


def initial_report(p):
    return {'schema':'m64-independent-four-valve-design/v1','length_unit':'mm_design_frame_not_scan',
            'parameters':asdict(p),'parameter_sources':{'diameters_and_maximum_lifts':SWINDON,
            'guide_clearance_design_reference':MAHLE,
            'guide_reference_scope':'generic_6_to_7_mm_stems; source_does_not_explicitly_define_radial_or_diametral',
            'guide_clearances':'explicit_cold_diametral_design_choices_not_automatically_derived_from_MAHLE_or_validated_for_M64_4V_turbo',
            'all_other_dimensions':'explicit_exploratory_design_choices_not_Porsche_interfaces'},
            'bore_scope':'provisional_100_mm_working_bore_not_fitment_contract',
            'coordinate_frame':'bore_axis_Z; seat_gauges_Z0; positive_Z_toward_stem; positive_lift_toward_chamber_negative_axis',
            'axis_definition':'stems_splay_outwards_in_X; included_bank_angle_twice_inclination',
            'scope':{'source_scan_read_or_modified':False,'F53_read_or_modified':False,
                     'M64_fitment_validated':False,'piston_clearance_tested':False,'cams_or_timing_selected':False,
                     'springs_selected_or_modeled':False,'thermal_validation':False,'fatigue_validation':False,
                     'materials_selected':False,'LPBF_simulated':False,'manufacturing_authorized':False,
                     'neck_blends_and_stem_tip_lock_details_complete':False},'parts':[]}


def build_stage(cad,p,out):
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True);report=initial_report(p)
    states=lift_states(p)
    for state in (states[0],states[4]):
        parts=construct(cad,p,state);path=out/(state['name']+'.step');cad.write_step(path,parts)
        reread=cad.read_step(path);record={'sha256':sha(path),'brep_valid_after_import':cad.valid(reread),
                 'solid_count_after_import':cad.indexed(reread,cad.TopAbs_SOLID).Extent()}
        if not record['brep_valid_after_import'] or record['solid_count_after_import']!=12: raise ValueError('assembly roundtrip invalid')
        report[state['name']+'_step']=record
        if state['name']=='closed':
            for part in parts:
                report['parts'].append({'name':part['name'],'role':part['role'],'volume_mm3':cad.volume(part['shape']),
                                       'brep_valid':cad.valid(part['shape'])})
    report['status']='assembly_built_collision_audit_pending'
    (out/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'part_count':len(report['parts'])}),flush=True)


def audit_stage(cad,p,out):
    build=json.loads((out/'build-report.json').read_text())
    if build['parameters']!=asdict(p) or sha(out/'closed.step')!=build['closed_step']['sha256']: raise ValueError('build provenance mismatch')
    if (out/'audit-report.json').exists(): raise FileExistsError(out/'audit-report.json')
    report={'schema':'m64-independent-four-valve-audit/v1','build_report_sha256':sha(out/'build-report.json'),
            'implementation_source_sha256':sha(Path(__file__)),
            'length_unit':'mm_design_frame_not_scan','states':[],'contacts_closed':[],
            'geometric_overlap_volume_limit_mm3':1e-7,'clearance_values_are_not_mechanical_allowables':True,
            'tests_are_selected_configurations_not_continuous_cam_law':True,'manufacturing_authorized':False}
    def save(): (out/'audit-report.json').write_text(json.dumps(report,indent=2)+'\n')
    closed=construct(cad,p,lift_states(p)[0]);seats=[part for part in closed if part['role']=='seat'];guides=[part for part in closed if part['role']=='guide']
    report['seat_seat_minimum_surface_gap_mm']=min(cad.distance(a['shape'],b['shape']) for a,b in itertools.combinations(seats,2))
    report['seat_guide_neighbor_minimum_surface_gap_mm']=min(cad.distance(a['shape'],b['shape']) for a in seats for b in guides if a['spec']['name']!=b['spec']['name'])
    # Full seat outer cylinders are conservative envelopes, not only the annular
    # pieces. Their separation quantifies geometric space available for a bridge.
    envelopes=[]
    for spec in valve_specs(p):
        profile,_=profiles(p,spec);zlo=profile['seat'][0][1];radius=spec['diameter_mm']/2+p.seat_outer_radial_allowance_mm
        cylinder=cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,0,zlo),cad.gp_Dir(0,0,1)),radius,p.seat_axial_thickness_mm).Shape()
        envelopes.append(cad.pose(cylinder,spec))
    report['seat_envelope_minimum_gap_mm']=min(cad.distance(a,b) for a,b in itertools.combinations(envelopes,2))
    report['seat_envelope_maximum_overlap_mm3']=max(cad.volume(cad.operation(cad.BRepAlgoAPI_Common,a,b)) for a,b in itertools.combinations(envelopes,2))
    for spec in valve_specs(p):
        valve=next(x for x in closed if x['name']==spec['name']+'_valve')['shape'];seat=next(x for x in closed if x['name']==spec['name']+'_seat')['shape']
        # The shared 45-degree band is generated from the same radial/axial
        # coordinates. Native point-to-solid checks also verify its placement.
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
        _,(inner,outer)=profiles(p,spec);errors=[];angle=math.radians(spec['axis_angle_deg']);r=spec['diameter_mm']/2
        for fraction in (0.,.5,1.):
            rr=inner+fraction*(outer-inner);z=(r-rr)*math.tan(math.radians(p.seat_angle_from_transverse_plane_deg))
            for index in range(12):
                phi=2*math.pi*index/12;x,y=rr*math.cos(phi),rr*math.sin(phi)
                point=cad.gp_Pnt(spec['center'][0]+x*math.cos(angle)+z*math.sin(angle),spec['center'][1]+y,-x*math.sin(angle)+z*math.cos(angle))
                vertex=BRepBuilderAPI_MakeVertex(point).Vertex();errors.extend((cad.distance(vertex,valve),cad.distance(vertex,seat)))
        report['contacts_closed'].append({'valve':spec['name'],'maximum_72_native_contact_point_errors_mm':max(errors),
              'solid_overlap_mm3':cad.volume(cad.operation(cad.BRepAlgoAPI_Common,valve,seat)),
              'nominal_contact_band_area_mm2':math.pi*(inner+outer)*p.seat_contact_radial_width_mm/math.cos(math.radians(p.seat_angle_from_transverse_plane_deg)),
              'contact_pressure_or_leakage_solved':False})
    bore=cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,0,-50),cad.gp_Dir(0,0,1)),p.bore_mm/2,180.).Shape()
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    faces=cad.indexed(bore,cad.TopAbs_FACE)
    side=next(cad.TopoDS.Face_s(faces.FindKey(i)) for i in range(1,faces.Extent()+1) if BRepAdaptor_Surface(cad.TopoDS.Face_s(faces.FindKey(i))).GetType()==GeomAbs_Cylinder)
    for state in lift_states(p):
        print(json.dumps({'auditing_state':state['name']}),flush=True);parts=construct(cad,p,state);valves=[x for x in parts if x['role']=='valve'];fixed=[x for x in parts if x['role']!='valve']
        pairs=[]
        for a,b in itertools.combinations(valves,2):
            pairs.append({'first':a['name'],'second':b['name'],'gap_mm':cad.distance(a['shape'],b['shape']),
                          'overlap_mm3':cad.volume(cad.operation(cad.BRepAlgoAPI_Common,a['shape'],b['shape']))})
        moving_fixed=[]
        for valve in valves:
            for part in fixed:
                moving_fixed.append({'first':valve['name'],'second':part['name'],
                          'gap_mm':cad.distance(valve['shape'],part['shape']),
                          'overlap_mm3':cad.volume(cad.operation(cad.BRepAlgoAPI_Common,valve['shape'],part['shape']))})
        bore_records=[{'valve':v['name'],'outside_volume_mm3':cad.volume(cad.operation(cad.BRepAlgoAPI_Cut,v['shape'],bore)),
                       'gap_to_bore_cylinder_mm':cad.distance(v['shape'],side)} for v in valves]
        guide_gaps=[row['gap_mm'] for row in moving_fixed if row['first'].removesuffix('_valve')==row['second'].removesuffix('_guide')]
        report['states'].append({'state':state,'valve_pairs':pairs,'moving_fixed_pairs':moving_fixed,'bore':bore_records,
                   'minimum_own_guide_radial_gap_mm':min(guide_gaps),'minimum_valve_pair_gap_mm':min(row['gap_mm'] for row in pairs),
                   'minimum_valve_bore_gap_mm':min(row['gap_to_bore_cylinder_mm'] for row in bore_records)})
        save()
    failed=[]
    if report['seat_envelope_minimum_gap_mm']<p.seat_envelope_minimum_gap_design_mm-1e-7: failed.append('seat_envelopes_below_design_gap')
    if report['seat_envelope_maximum_overlap_mm3']>1e-7: failed.append('seat_envelopes_overlap')
    if any(row['maximum_72_native_contact_point_errors_mm']>1e-7 or row['solid_overlap_mm3']>1e-7 for row in report['contacts_closed']): failed.append('closed_contact_mismatch')
    for row in report['states']:
        if any(pair['overlap_mm3']>1e-7 for pair in row['valve_pairs']+row['moving_fixed_pairs']): failed.append(row['state']['name']+'_solid_collision')
        if any(pair['gap_mm']<=1e-7 for pair in row['valve_pairs']): failed.append(row['state']['name']+'_valves_touch')
        if row['minimum_own_guide_radial_gap_mm']<=1e-7: failed.append(row['state']['name']+'_guide_clearance_missing')
        for pair in row['moving_fixed_pairs']:
            is_own_seat=pair['first'].removesuffix('_valve')==pair['second'].removesuffix('_seat')
            if not is_own_seat and pair['gap_mm']<=1e-7: failed.append(row['state']['name']+'_unintended_fixed_contact')
        if any(v['outside_volume_mm3']>1e-7 or v['gap_to_bore_cylinder_mm']<=1e-7 for v in row['bore']): failed.append(row['state']['name']+'_bore_collision')
    report['failed_checks']=failed;report['status']='selected_geometric_checks_passed_not_engine_validation' if not failed else 'rejected_selected_geometry'
    save();print(json.dumps({'status':report['status'],'failed_checks':failed,'seat_envelope_gap_mm':report['seat_envelope_minimum_gap_mm']}),flush=True)


def sections_stage(cad,p,out):
    report=json.loads((out/'build-report.json').read_text())
    if report['parameters']!=asdict(p): raise ValueError('section parameter provenance mismatch')
    target=out/'sections-report.json'
    if target.exists(): raise FileExistsError(target)
    results={}
    for name in ('closed','simultaneous_100pct'):
        step=out/(name+'.step')
        if sha(step)!=report[name+'_step']['sha256']: raise ValueError('section STEP provenance mismatch')
        shape=cad.read_step(step)
        section=cad.BRepAlgoAPI_Section(shape,cad.gp_Pln(cad.gp_Pnt(0,p.pair_half_spacing_mm,0),cad.gp_Dir(0,1,0)),False)
        section.Build()
        if not section.IsDone(): raise RuntimeError('STEP assembly section failed')
        output=out/(name+'-section.step')
        if output.exists(): raise FileExistsError(output)
        cad.write_step(output,[{'name':name+'_native_section','role':'section','shape':section.Shape()}])
        actual=cad.read_step(output)
        results[name]={'source_STEP_sha256':sha(step),'section_STEP_sha256':sha(output),
                       'section_edge_count_after_import':cad.indexed(actual,cad.TopAbs_EDGE).Extent(),
                       'BRepCheck_after_import':cad.valid(actual)}
    target.write_text(json.dumps({'schema':'m64-four-valve-native-STEP-sections/v1',
        'plane_design_frame_mm':{'origin':[0,p.pair_half_spacing_mm,0],'normal':[0,1,0]},
        'sections':results,'manufacturing_authorized':False},indent=2)+'\n')
    print(json.dumps(results),flush=True)


def integrity_stage(cad,p,out):
    report=json.loads((out/'build-report.json').read_text());target=out/'exact-integrity-report.json'
    if target.exists(): raise FileExistsError(target)
    if report['parameters']!=asdict(p): raise ValueError('integrity parameter mismatch')
    records={}
    for name in ('closed','simultaneous_100pct'):
        path=out/(name+'.step')
        if sha(path)!=report[name+'_step']['sha256']: raise ValueError('integrity STEP mismatch')
        shape=cad.read_step(path);solids=cad.indexed(shape,cad.TopAbs_SOLID)
        record={'STEP_sha256':sha(path),'BRepCheck_exact_method':cad.valid(shape),
                'solid_count':solids.Extent(),'all_solids_BRepCheck_exact_method':all(cad.valid(solids.FindKey(i)) for i in range(1,solids.Extent()+1)),
                'STEP_millimetre_unit_present':'SI_UNIT(.MILLI.,.METRE.)' in path.read_text()}
        records[name]=record
        if not all(record[k] for k in ('BRepCheck_exact_method','all_solids_BRepCheck_exact_method','STEP_millimetre_unit_present')) or record['solid_count']!=12:
            raise ValueError('exact assembly integrity rejected')
    target.write_text(json.dumps({'schema':'m64-four-valve-exact-STEP-integrity/v1','artifacts':records,
        'new_geometry_constructed':False,'manufacturing_authorized':False},indent=2)+'\n')
    print(json.dumps(records),flush=True)


def render_stage(cad,p,out):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.colors import to_rgb
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import trimesh
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    image=out/'four-valve-design-assembly-and-sections.png'
    if image.exists(): raise FileExistsError(image)
    report=json.loads((out/'build-report.json').read_text());audit=json.loads((out/'audit-report.json').read_text())
    if sha(out/'closed.step')!=report['closed_step']['sha256'] or report['parameters']!=asdict(p): raise ValueError('STEP/render provenance mismatch')
    # Read the actual written STEP for the overall view. Separate component STEP
    # geometries are obtained by its solid ordering; the geometric checks below
    # also retain the original explicit component names.
    actual=cad.read_step(out/'closed.step');solids=cad.indexed(actual,cad.TopAbs_SOLID)
    parts=construct(cad,p,lift_states(p)[0]);palette={'valve':'#7892a7','seat':'#d39025','guide':'#27998c'}
    fig=plt.figure(figsize=(16,10));gs=fig.add_gridspec(2,3,width_ratios=(1.05,1,1),height_ratios=(1,1))
    ax=fig.add_subplot(gs[:,0],projection='3d');all_bounds=[]
    # STEP solids retain component order, but assign colour by analytic volume
    # only if its match is unique by role; fail rather than mislabel otherwise.
    for i in range(1,solids.Extent()+1):
        shape=solids.FindKey(i);volume=cad.volume(shape);roles={part['role'] for part in parts if abs(cad.volume(part['shape'])-volume)<1e-6}
        if len(roles)!=1: raise ValueError('STEP role attribution ambiguous')
        role=roles.pop();meshpath=out/f'design-render-solid-{i}.stl'
        BRepMesh_IncrementalMesh(shape,.12,False,.25,False)
        if not StlAPI_Writer().Write(shape,str(meshpath)): raise RuntimeError('tessellation export failed')
        mesh=trimesh.load_mesh(meshpath);all_bounds.extend(mesh.bounds)
        light=np.array([.3,-.4,.85]);light/=np.linalg.norm(light)
        brightness=.4+.6*np.clip(mesh.face_normals@light,0,1)
        colors=brightness[:,None]*np.array(to_rgb(palette[role]))[None,:]
        ax.add_collection3d(Poly3DCollection(mesh.triangles,facecolors=colors,edgecolors='none',linewidths=0,antialiased=False,alpha=1))
    bounds=np.array(all_bounds);span=np.ptp(bounds,axis=0)
    ax.set_xlim(bounds[:,0].min()-4,bounds[:,0].max()+4);ax.set_ylim(bounds[:,1].min()-4,bounds[:,1].max()+4);ax.set_zlim(-7,86)
    ax.set_box_aspect((span[0]+8,span[1]+8,93));ax.view_init(27,-57);ax.set_proj_type('ortho');ax.set_axis_off()
    ax.set_title('STEP réel : 12 solides\n4 soupapes, 4 sièges, 4 guides',fontsize=13)
    for axis_index,state in enumerate((lift_states(p)[0],lift_states(p)[4])):
        view=fig.add_subplot(gs[0,1+axis_index]);items=construct(cad,p,state)
        for part in items:
            if part['spec']['center'][1]<0: continue
            section=cad.BRepAlgoAPI_Section(part['shape'],cad.gp_Pln(cad.gp_Pnt(0,p.pair_half_spacing_mm,0),cad.gp_Dir(0,1,0)),False);section.Build()
            if not section.IsDone(): raise RuntimeError('section failed')
            edges=cad.indexed(section.Shape(),cad.TopAbs_EDGE)
            for i in range(1,edges.Extent()+1):
                curve=BRepAdaptor_Curve(cad.TopoDS.Edge_s(edges.FindKey(i)))
                pts=[curve.Value(float(t)) for t in np.linspace(curve.FirstParameter(),curve.LastParameter(),61)]
                view.plot([q.X() for q in pts],[q.Z() for q in pts],color=palette[part['role']],lw=1.4)
        bore_section_x=math.sqrt((p.bore_mm/2)**2-p.pair_half_spacing_mm**2)
        view.set_aspect('equal');view.set_xlim(-53,53);view.set_ylim(-20,85);view.axvline(-bore_section_x,color='#888888',ls='--');view.axvline(bore_section_x,color='#888888',ls='--')
        view.set_xlabel('X du module (mm)');view.set_ylabel('Z du module (mm)');view.grid(alpha=.15)
        view.set_title(('Coupe CAO fermée','Coupe CAO : levées 11,5 / 9,6 mm')[axis_index],fontsize=12)
    detail=fig.add_subplot(gs[1,1]);spec=valve_specs(p)[0];shapes,band=profiles(p,spec)
    # True native meridian sections, projected back to the valve's local axis.
    for role in ('valve','seat','guide'):
        shape=cad.revolve(shapes[role]);section=cad.BRepAlgoAPI_Section(shape,cad.gp_Pln(cad.gp_Pnt(0,0,0),cad.gp_Dir(0,1,0)),False);section.Build()
        edges=cad.indexed(section.Shape(),cad.TopAbs_EDGE)
        for i in range(1,edges.Extent()+1):
            curve=BRepAdaptor_Curve(cad.TopoDS.Edge_s(edges.FindKey(i)));pts=[curve.Value(float(t)) for t in np.linspace(curve.FirstParameter(),curve.LastParameter(),61)]
            detail.plot([q.X() for q in pts],[q.Z() for q in pts],color=palette[role],lw=2)
    detail.set_xlim(15.5,22.5);detail.set_ylim(-2.2,6.8);detail.set_aspect('equal');detail.grid(alpha=.2)
    detail.set_xlabel('Rayon local (mm)');detail.set_ylabel('Z local (mm)');detail.set_title('Portée conique correspondante 45°',fontsize=12)
    detail.annotate('Bande en contact\nlargeur radiale 1 mm',xy=(19.,1.),xytext=(16.,4.5),arrowprops={'arrowstyle':'->'},fontsize=10)
    text=fig.add_subplot(gs[1,2]);text.set_axis_off()
    minimum=min(s['minimum_valve_pair_gap_mm'] for s in audit['states']);boremin=min(s['minimum_valve_bore_gap_mm'] for s in audit['states'])
    lines=['REPÈRE DE CONCEPTION INDÉPENDANT',f'Alésage de travail : {p.bore_mm:g} mm',f'Axes : ±{p.bank_inclination_deg:g}° ; tiges vers extérieur',
           'Ouverture : vers chambre / piston',f'Jeux guide/tige diamétraux : {p.intake_guide_diametral_clearance_mm:.3f} / {p.exhaust_guide_diametral_clearance_mm:.3f} mm',
           '',f'Écart siège-siège : {audit["seat_envelope_minimum_gap_mm"]:.3f} mm',f'Écart soupape-soupape minimal testé : {minimum:.3f} mm',
           f'Écart soupape/alésage minimal testé : {boremin:.3f} mm','7 configurations ; pas une loi de came','','Ressorts, arbres, piston et corps absents.','Pas de validation thermique ou mécanique.','Pas d’intégration M64 ni autorisation de fabrication.']
    text.text(0,.98,'\n'.join(lines),va='top',fontsize=10.5,linespacing=1.55)
    fig.legend(handles=[Line2D([0],[0],color=c,lw=4,label=l) for l,c in [('Soupape',palette['valve']),('Siège',palette['seat']),('Guide',palette['guide'])]],loc='lower center',ncol=3)
    fig.suptitle('Distribution 4 soupapes — sous-assemblage CAO non libéré',fontsize=19,weight='bold')
    fig.text(.5,.065,'Aucun scan ni contour de culasse remplacé. Couleurs = composants, pas résultats thermiques.',ha='center',fontsize=11,color='#7e3326')
    fig.subplots_adjust(top=.90,bottom=.16,wspace=.32,hspace=.38);fig.savefig(image,dpi=150,bbox_inches='tight');plt.close(fig)
    (out/'render-report.json').write_text(json.dumps({'image_sha256':sha(image),'closed_STEP_sha256':sha(out/'closed.step'),
        'audit_report_sha256':sha(out/'audit-report.json'),'actual_STEP_rendered':True,'native_CAD_sections':True,'generative_image':False},indent=2)+'\n')
    print(json.dumps({'image':str(image),'sha256':sha(image)}),flush=True)


def compare_stage(baseline,out):
    if baseline is None: raise ValueError('--baseline required for comparison')
    target=out/'placement-comparison.json'
    if target.exists(): raise FileExistsError(target)
    builds=[json.loads((folder/'build-report.json').read_text()) for folder in (baseline,out)]
    audits=[json.loads((folder/'audit-report.json').read_text()) for folder in (baseline,out)]
    for folder,build,audit in zip((baseline,out),builds,audits):
        if sha(folder/'build-report.json')!=audit['build_report_sha256'] or sha(folder/'closed.step')!=build['closed_step']['sha256']:
            raise ValueError('comparison input provenance mismatch')
    a,b=builds[0]['parameters'],builds[1]['parameters'];changed={key for key in a if a[key]!=b[key]}
    if changed-{'intake_x_mm','exhaust_x_mm','seat_envelope_minimum_gap_design_mm'}:
        raise ValueError('comparison is not a pure assembly translation')
    delta=b['intake_x_mm']-a['intake_x_mm']
    if abs(delta-(b['exhaust_x_mm']-a['exhaust_x_mm']))>1e-12: raise ValueError('unequal bank translations')
    rows=[];individual=[];max_pair_delta=0.
    for old,new in zip(audits[0]['states'],audits[1]['states']):
        if old['state']!=new['state']: raise ValueError('different selected lift states')
        old_min,new_min=old['minimum_valve_bore_gap_mm'],new['minimum_valve_bore_gap_mm']
        rows.append({'state':old['state']['name'],'baseline_bore_min_mm':old_min,'candidate_bore_min_mm':new_min,
                     'delta_bore_min_mm':new_min-old_min,'decreased_beyond_numerical_tolerance':new_min<old_min-1e-7})
        for first,second in zip(old['valve_pairs'],new['valve_pairs']):
            if (first['first'],first['second'])!=(second['first'],second['second']): raise ValueError('pair mismatch')
            max_pair_delta=max(max_pair_delta,abs(first['gap_mm']-second['gap_mm']))
        for first,second in zip(old['bore'],new['bore']):
            if first['valve']!=second['valve']: raise ValueError('valve mismatch')
            individual.append({'state':old['state']['name'],'valve':first['valve'],
                               'baseline_mm':first['gap_to_bore_cylinder_mm'],'candidate_mm':second['gap_to_bore_cylinder_mm'],
                               'delta_mm':second['gap_to_bore_cylinder_mm']-first['gap_to_bore_cylinder_mm']})
    minima=[min(row['minimum_valve_bore_gap_mm'] for row in audit['states']) for audit in audits]
    result={'schema':'m64-four-valve-placement-comparison/v1','translation_X_mm':delta,'diameters_or_component_profiles_changed':False,
            'baseline_closed_STEP_sha256':builds[0]['closed_step']['sha256'],'candidate_closed_STEP_sha256':builds[1]['closed_step']['sha256'],
            'baseline_audit_sha256':sha(baseline/'audit-report.json'),'candidate_audit_sha256':sha(out/'audit-report.json'),
            'baseline_worst_case_bore_gap_mm':minima[0],'candidate_worst_case_bore_gap_mm':minima[1],
            'worst_case_improvement_mm':minima[1]-minima[0],
            'maximum_valve_pair_gap_absolute_delta_mm':max_pair_delta,
            'baseline_seat_envelope_gap_mm':audits[0]['seat_envelope_minimum_gap_mm'],
            'candidate_seat_envelope_gap_mm':audits[1]['seat_envelope_minimum_gap_mm'],
            'state_comparison':rows,'individual_valve_bore_comparison':individual,
            'all_selected_geometric_checks_passed':not audits[0]['failed_checks'] and not audits[1]['failed_checks'],
            'worst_case_global_improved':minima[1]>minima[0]+1e-7,
            'no_regression_in_each_state_minimum':not any(row['decreased_beyond_numerical_tolerance'] for row in rows),
            'selection_basis':'improved_global_worst_case_only_not_Pareto_dominance',
            'M64_fitment_validated':False,'manufacturing_authorized':False}
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('worst_case_improvement_mm','maximum_valve_pair_gap_absolute_delta_mm','no_regression_in_each_state_minimum')}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',choices=('build','audit','sections','render','compare','integrity'),required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--parameters',type=Path);parser.add_argument('--baseline',type=Path)
    args=parser.parse_args();os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2]);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    p=Parameters(**json.loads(args.parameters.read_text())) if args.parameters else Parameters();p.validate()
    if args.stage=='compare': compare_stage(args.baseline,args.output);return
    {'build':build_stage,'audit':audit_stage,'sections':sections_stage,'render':render_stage,'integrity':integrity_stage}[args.stage](CAD(),p,args.output)


if __name__=='__main__':main()
