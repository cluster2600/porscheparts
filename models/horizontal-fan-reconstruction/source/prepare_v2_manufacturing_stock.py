#!/usr/bin/env python3
"""Editable machining-stock scenario; no laser recipe or process simulation."""
import argparse,hashlib,json,math,os,resource,time
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root,output):
    import build123d as cad
    start=time.monotonic();p=json.loads((root/'parameters/assembly-study-S1.json').read_text())
    v2=json.loads((root/'parameters/V2.json').read_text());s=p['sizing_scenario']
    rotor=cad.import_step(root/'V2-rotor.step');R=v2['diameter_mm']/2;bore=R*v2['bore_radius_ratio'];height=v2['diameter_mm']*.12
    radial=s['machining_stock_bore_radial_mm'];axial=s['machining_stock_hub_face_axial_mm']
    if not (0<radial<bore and 0<axial<2):raise ValueError('Invalid exploratory machining stock')
    def annulus(outer,inner,h,z):
        a=cad.Solid.make_cylinder(outer,h,cad.Plane(origin=(0,0,z)))
        b=cad.Solid.make_cylinder(inner,h+2,cad.Plane(origin=(0,0,z-1)))
        return a.cut(b)
    # Only these three stock zones are added; blade geometry remains unchanged.
    additions=[annulus(bore,bore-radial,height,-height),
               annulus(R*.24,bore-radial,axial,-height-axial),
               annulus(R*.20,bore-radial,axial,0)]
    blank=rotor.fuse(*additions)
    if not blank.is_valid or len(blank.solids())!=1 or blank.volume<=rotor.volume:raise ValueError('Connected positive stock blank required')
    output.mkdir(parents=True,exist_ok=False);step=output/'V2-stock-scenario.step';mesh=output/'V2-stock-scenario.stl'
    cad.export_step(blank,step);cad.export_stl(blank,mesh,tolerance=.12,angular_tolerance=.18)
    reimport=cad.import_step(step);error=abs(reimport.volume/blank.volume-1)
    if not reimport.is_valid or error>1e-7:raise ValueError('Stock STEP roundtrip')
    report={'status':'editable_stock_and_route_scenario_only','source_rotor_sha256':sha(root/'V2-rotor.step'),
            'parameters_sha256':sha(root/'parameters/assembly-study-S1.json'),'builder_sha256':sha(Path(__file__)),
            'build123d_version':cad.__version__,'blank_step_sha256':sha(step),'blank_stl_sha256':sha(mesh),
            'units':'mm','original_volume_mm3':rotor.volume,'stock_blank_volume_mm3':blank.volume,
            'added_stock_volume_mm3':blank.volume-rotor.volume,
            'nominal_mass_kg_at_assumed_density':rotor.volume*1e-9*s['density_kg_m3'],
            'stock_blank_mass_kg_at_assumed_density':blank.volume*1e-9*s['density_kg_m3'],
            'stock_zones':{'bore_radial_mm':radial,'upper_and_lower_hub_face_axial_mm':axial},
            'blank_bore_diameter_mm':2*(bore-radial),'assumed_finished_bore_diameter_mm':2*bore,
            'brep_valid':True,'solids':1,'step_roundtrip_relative_volume_error':error,
            'material_scenario':'AlSi10Mg candidate; density 2700 kg/m3 is approximate and process properties unqualified',
            'machine_scenarios':[{'id':'reference_250','workspace_mm':[250,250,300]},
                                 {'id':'BLT_S400_reference_400','workspace_mm':[400,300,400]},
                                 {'id':'BLT_S400_reference_450','workspace_mm':[450,300,400]}],
            'machine_serial_recipe_and_actual_available_volume_verified':False,
            'orientation_and_supports_finalized':False,'layer_thickness_scenario_mm':.05,
            'support_solids_or_machine_toolpath_generated':False,
            'thermal_history_residual_stress_distortion_or_porosity_simulated':False,
            'process_qualification_established':False,'manufacturing_authorized':False,'physical_validation_established':False,
            'elapsed_seconds':time.monotonic()-start,'peak_RSS_bytes_mac':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    (output/'stock-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','added_stock_volume_mm3','stock_blank_mass_kg_at_assumed_density','elapsed_seconds']}));return report


if __name__=='__main__':
    os.nice(15);cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('root',type=Path);cli.add_argument('output',type=Path)
    a=cli.parse_args();prepare(a.root,a.output)
