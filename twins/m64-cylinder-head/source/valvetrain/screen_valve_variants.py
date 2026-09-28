#!/usr/bin/env python3
"""Native valve variants and inertial sensitivity, not a hot valve qualification.

Keep the existing external design profile. Empty stem bores are computational
candidates for supplier discussion, NOT LPBF instructions for sealed cavities.
"""
import argparse
import copy
from dataclasses import replace
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import valvetrain as vt

SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE))
import build_four_valve_distribution as design
sys.path.insert(0,str(SOURCE/'wholebody'))
from render_v5_v2 import sha, save
import build_extended_valve_assembly_v2 as extension

TI_SOURCE='https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf'
MATERIALS={
    'steel_reference': dict(density_kg_m3=7850., density_status='inherited_handbook_assumption_not_selected_valve_grade',
        conductivity_W_mK=None, hot_allowables_available=False),
    'timetal_6_4_reference': dict(density_kg_m3=4420., density_status='TIMET_datasheet_22C_wrought_not_LPBF',
        conductivity_W_mK=6.6, conductivity_temperature_C=20., conductivity_state='mill_annealed',
        source=TI_SOURCE, hot_allowables_available=False),
}


def bore_properties(outer, inner, length):
    if (not all(math.isfinite(x) for x in (outer,inner,length))
            or not 0 <= inner < outer or length <= 0):
        raise ValueError('finite_positive_annulus_required')
    return dict(removed_volume_mm3=math.pi*inner**2/4*length,
        remaining_area_mm2=math.pi*(outer**2-inner**2)/4,
        axial_area_ratio=1-(inner/outer)**2,
        bending_inertia_ratio=1-(inner/outer)**4, radial_wall_mm=(outer-inner)/2)


def run(args):
    import OCP
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRep import BRep_Builder
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if args.output.exists() or OCP.__version__ != '7.9.3.1':
        raise ValueError('fresh_output_and_exact_OCP_runtime_required')
    paths=[Path(__file__),Path(vt.__file__),Path(design.__file__),Path(extension.__file__),SOURCE/'four-valve-distribution-v2.parameters.json']
    pins={p:sha(p) for p in paths}
    parameters=design.Parameters(**json.loads(paths[-1].read_text()))
    parameters=replace(parameters,stem_tip_above_gauge_mm=args.stem_tip)
    parameters.validate()
    params=vt.default_parameters();cad=design.CAD();started=time.monotonic()
    args.output.mkdir(mode=0o700)
    rows=[];geometries=[]
    fig,axes=plt.subplots(1,2,figsize=(11,5))
    for bank in ('intake','exhaust'):
        spec=next(v for v in design.valve_specs(parameters) if v['kind']==bank)
        profile=design.profiles(parameters,spec)[0]['valve']
        solid=cad.revolve(profile);original_volume=cad.volume(solid)
        if args.stem_tip==extension.NEW_TIP:
            base=replace(parameters,stem_tip_above_gauge_mm=extension.ORIGINAL_TIP)
            base_volume=cad.volume(cad.revolve(design.profiles(base,spec)[0]['valve']))
            if not math.isclose(original_volume-base_volume,extension.ADDED_VOLUME,abs_tol=1e-7):
                raise ValueError('native_extension_volume_mismatch')
        for bore in (0.,3.,4.):
            section=bore_properties(parameters.stem_diameter_mm,bore,60.)
            candidate=solid
            if bore:
                tool=cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,0,15),cad.gp_Dir(0,0,1)),bore/2,60).Shape()
                cut=cad.BRepAlgoAPI_Cut(solid,tool);cut.SetNonDestructive(True);cut.Build()
                if not cut.IsDone(): raise ValueError('bore_boolean_failed')
                candidate=cut.Shape()
            volume=cad.volume(candidate)
            if (not cad.valid(candidate) or cad.indexed(candidate,cad.TopAbs_SOLID).Extent()!=1
                    or not math.isclose(original_volume-volume,section['removed_volume_mm3'],abs_tol=1e-7)):
                raise ValueError('native_bore_volume_or_solid_gate_failed')
            target=args.output/f'{bank}-bore-{bore:g}-private.brep'
            if not BRepTools.Write_s(candidate,str(target)): raise ValueError('native_write_failed')
            reread=TopoDS_Shape()
            if not BRepTools.Read_s(reread,str(target),BRep_Builder()) or not cad.valid(reread):
                raise ValueError('native_readback_failed')
            if not math.isclose(cad.volume(reread),volume,abs_tol=1e-7): raise ValueError('volume_readback_failed')
            geometries.append(dict(bank=bank,bore_mm=bore,volume_mm3=volume,artifact=target.name,
                                   sha256=sha(target),native_valid=True,volume_roundtrip=True,section=section))
            for material,card in MATERIALS.items():
                vp=copy.deepcopy(params[bank]);mass=volume*1e-9*card['density_kg_m3']
                vp['valve_mass_kg']=vt.P(mass,'kg','repository_design_candidate','Native design volume times the explicitly scoped reference density.')
                sp=vt.spring_properties(vp,params['engine']);effective=vt.effective_mass(vp,sp)
                law=vt.CamLaw.from_params(vp,hot=True)
                dynamic=[]
                for steps in (3600,7200,14400):
                    value=vt.simulate_sdof(law,vp,sp,effective,6500.,cycles=3,steps_per_cycle=steps)
                    dynamic.append(dict(steps_per_cycle=steps,**{k:value[k] for k in ('max_separation_mm','max_bounce_mm','contact_loss_fraction_of_open')}))
                if not all(math.isfinite(v) for r in dynamic for v in r.values()): raise ValueError('nonfinite_dynamics')
                rows.append(dict(bank=bank,bore_mm=bore,material=material,mass_kg=mass,effective_mass_kg=effective,
                    spring_coil_bind_clearance_mm=sp['coil_bind_clearance_m']*1000,
                    spring_coil_bind_screen_pass=sp['coil_bind_ok'],
                    inertial_margin_6500rpm=vt.spring_margin(law,sp,effective,6500.)['min_margin'],
                    simplified_dynamic_6500rpm=dynamic,
                    pressure_force_N_per_bar=math.pi*(spec['diameter_mm']*.001)**2/4*1e5,
                    axial_stem_conductance_W_K=(card['conductivity_W_mK']*section['remaining_area_mm2']*1e-6/.060
                        if card['conductivity_W_mK'] is not None else None),
                    conductance_scope='60mm cylindrical segment only; no gas, guide, seat, head spreading or cavity convection'))
        ax=axes[0 if bank=='intake' else 1]
        x,z=np.array(profile).T
        ax.plot(np.r_[x,x[0]],np.r_[z,z[0]],color='#344e63',label='Retained meridian')
        for bore,color in ((3.,'#d7892c'),(4.,'#bb483c')):
            ax.plot([0,bore/2,bore/2,0,0],[15,15,75,75,15],color=color,label=f'Empty bore {bore:g} mm')
        ax.set_aspect('equal');ax.set_title(bank);ax.set_xlabel('Design radius (mm)');ax.set_ylabel('Design axial position (mm)')
        ax.legend(fontsize=8,loc='upper left',bbox_to_anchor=(1.03,1.))
    fig.suptitle('Valve design meridians — comparative candidates, not manufacturing drawings')
    fig.text(.5,.015,'No keeper grooves, closing weld, supplier route, hot strength or sodium cooling qualified.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,.93));fig.savefig(args.output/'valve-sections.png',dpi=150);plt.close(fig)
    result=dict(schema='m64-valve-variant-screen/v1',status='completed_sensitivity_only',
        source_sha256=pins[paths[0]],dependency_sha256={p.name:s for p,s in pins.items()},
        geometry_basis='Existing V2 provisional profile; selected tip extends only the cylindrical stem; not an installed supplier valve',
        selected_stem_tip_mm=args.stem_tip,
        analytic_mass_added_vs_original_g={k:extension.ADDED_VOLUME*c['density_kg_m3']*1e-6
            if args.stem_tip==extension.NEW_TIP else 0. for k,c in MATERIALS.items()},
        geometry_frame='design_mm_not_calibrated_scan',case_count=len(rows),materials=MATERIALS,
        bores=dict(diameters_mm=[0,3,4],start_mm=15,end_mm=75,fill='empty',closure_process_qualified=False),
        geometries=geometries,results=rows,dynamics_parameters=params,
        gas_pressure_loads_in_dynamics=False,temperature_field_solved=False,
        fatigue_or_creep_solved=False,sodium_shaker_cooling_solved=False,
        periodicity_certified=False,engine_rpm_selected=False,real_cam_profile_used=False,
        spring_contact_damping_calibrated=False,manufacturing_authorized=False,
        hollow_valves_authorized_for_LPBF=False,head_geometry_modified=False,
        inputs_unchanged=all(sha(p)==s for p,s in pins.items()),elapsed_seconds=time.monotonic()-started)
    save(args.output/'report.json',result)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for bank,marker in (('intake','o'),('exhaust','s')):
        for material,color in (('steel_reference','#344e63'),('timetal_6_4_reference','#d7892c')):
            subset=[r for r in rows if r['bank']==bank and r['material']==material]
            label=bank+' / '+('steel ref.' if material=='steel_reference' else 'Ti-6Al-4V ref.')
            for ax,key in zip(axes,('mass','separation')):
                values=[r['mass_kg']*1000 if key=='mass' else r['simplified_dynamic_6500rpm'][-1]['max_separation_mm'] for r in subset]
                ax.plot([r['bore_mm'] for r in subset],values,marker=marker,color=color,label=label)
                ax.set_xlabel('Empty bore diameter (mm)');ax.grid(alpha=.2)
    axes[0].set_ylabel('Native design mass (g)');axes[1].set_ylabel('Model maximum separation (mm)')
    axes[0].legend(fontsize=8)
    fig.suptitle(f'Valve sensitivity only — provisional V2 profile, tip {args.stem_tip:g} mm, assumed 6500 rpm')
    fig.text(.5,.02,'No gas pressure, hot strength, sodium cooling, real cam or physical validation. No installed-assembly qualification.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,.95));fig.savefig(args.output/'variant-comparison.png',dpi=150);plt.close(fig)
    print(json.dumps({k:result[k] for k in ('status','case_count','elapsed_seconds','inputs_unchanged')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--stem-tip',type=float,choices=(extension.ORIGINAL_TIP,extension.NEW_TIP),default=extension.ORIGINAL_TIP)
    run(parser.parse_args())
