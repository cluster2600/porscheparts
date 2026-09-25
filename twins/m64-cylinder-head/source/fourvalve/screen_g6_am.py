#!/usr/bin/env python3
"""Real-layer geometric AM screen, reusing F50 slices; no melt-pool or print authorization."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def run(native, output):
    import trimesh
    path = ROOT/'scripts/run_metal_am_geometry_screen.py'
    spec = importlib.util.spec_from_file_location('metal_screen',path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    kernel = module.load_kernel()
    machine_path = ROOT/'catalog/manufacturing/machines/eos-m290.json'
    machine = json.loads(machine_path.read_text());module.validate_machine(machine)
    kernel.machine_fit = lambda extents: module.machine_fit(machine,extents)
    kernel.LAYER_MM, kernel.SUPPORT_RASTER_MM = .06, .5
    audit = json.loads((native/'audit.json').read_text())
    output.mkdir(parents=True,exist_ok=False)
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    results = {}
    for name, voids in audit['closed_void_checks'].items():
        master, surface = native/(name+'.step'), native/(name+'.stl')
        for f in (master,surface):
            if sha(f)!=audit['files_sha256'][f.name]:raise ValueError('native artifact hash mismatch')
        mesh = trimesh.load_mesh(surface,process=True)
        if not isinstance(mesh,trimesh.Trimesh) or not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('analysis mesh must be watertight with consistent winding')
        if len(mesh.split(only_watertight=False))!=1:raise ValueError('analysis mesh must be one component')
        orientations = kernel.orientation_screen(mesh)
        fitting = [r for r in orientations if r['bare_part_nominal_fit']]
        if not fitting:raise ValueError('no orientation fits machine envelope')
        chosen = min(fitting,key=lambda r:r['downward_projected_area_mm2'])['orientation']
        print(json.dumps({'component':name,'orientation':chosen,'stage':'slicing'}),flush=True)
        rows,slicing = kernel.slice_build(mesh,chosen)
        module.write_rows(output/(name+'-layers.csv'),rows)
        thickness = kernel.thickness_screen(mesh,2000)
        results[name] = {'master_sha256':sha(master),'surface_sha256':sha(surface),'triangles':len(mesh.faces),
                         'mesh_volume_mm3':float(mesh.volume), 'orientations':orientations,
                         'full_build_slicing':slicing,'thickness_screen':thickness,'closed_void_check':voids,
                         'minimum_wall_certified':False,'supports_designed_and_removable':False,
                         'machining_allowance_embodied':False,'manufacturing_authorized':False}
        print(json.dumps({'component':name,'layers':len(rows),'thin_fraction':thickness['sample_fraction_below_1p5_mm']}),flush=True)
    result={'classification':'native_CAD_connected_void_and_actual_layer_slicing_not_LPBF_process_simulation',
            'manufacturing_authorized':False,'material_qualified':False,'additivefoam_executed':False,
            'machine_candidate':machine,'layer_thickness_mm':.06,'material_candidate_not_selected':'Aheadd_CP1',
            'components':results,'native_audit_sha256':sha(native/'audit.json'),
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),path,module.KERNEL_PATH,machine_path)},
            'powder_note':'No voxel fill used: it can erase the closed cavity before testing. BRep void components do not prove powder evacuation or internal support removability.',
            'remaining_process_gates':['hot material and machine calibration','support topology and removal access','residual stress and distortion','machining stock, tolerances and CT/coupons']}
    (output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.native,args.output)
