"""Actual d64/24af STL preview; unchanged full-triangle raster and section helpers."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import struct
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def reused(path, name, namespace):
    node = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


def verify(plan, hash_inputs=True):
    assert plan['bounds'] == dict(outer=180, inner=150, CPU=[140,141], threads=1, workers=0)
    assert plan['triangle_counts'] == [597720,598372] and plan['camera_degrees'] == [30.,0.]
    assert plan['STL_sha256'] == ['17d7de30d5d6e2ef51fee4c1dac9da66ad618bcfeda4cf61fe90e084a807d7b2',
                                'b4026f66dc77b8022e82c358553e8e93ce0cbc2ea0fd31da19ac39a9f891a803']
    assert plan['masses_kg'] == [1.2747979975709924,1.2759916739532025]
    assert plan['section_X_mm'] == 83.39717404347466 and plan['detail_YZ_mm'] == [[-18.,10.],[-12.,17.]]
    assert [plan['files_sha256'][p] for p in plan['STLs']] == plan['STL_sha256']
    for path, digest in plan['files_sha256'].items():
        if hash_inputs or path not in plan['STLs']:
            assert sha(path) == digest, path
    for path, digest in plan['runtime_sha256'].items():
        if hash_inputs:
            assert sha(path) == digest, path
    old, new = [read(path) for path in plan['body_ROOTs']]
    assert [old['measured_mass_kg'],new['measured_mass_kg']] == plan['masses_kg']
    assert [old['candidate_BREP_sha256'],new['candidate_BREP_sha256']] == plan['BREP_sha256']
    generation, owner = read(plan['new_generation_ROOT']), read(plan['new_generation_owner'])
    assert generation['schema'] == 'root-new-rib-dedicated-surface-terminal-review-1'
    assert generation['status'] == 'closed_actual_RC0_new_rib_surface_generated_audits_pending'
    assert owner['status'] == 'closed_actual_RC0_surface_generated_not_yet_audited'
    assert generation['owner_terminal_sha256'] == sha(plan['new_generation_owner'])
    assert generation['CAD_source'] == owner['CAD_source'] and generation['CAD_source']['sha256'] == plan['BREP_sha256'][1]
    assert generation['STL_sha256'] == owner['STL_sha256'] == plan['STL_sha256'][1]
    assert generation['triangles'] == owner['triangles'] == plan['triangle_counts'][1]
    assert owner['actual_outer_returncode'] == owner['actual_child_returncode'] == 0
    construction = read(plan['new_construction_ROOT'])
    assert sha(plan['new_construction_ROOT']) == '1b19ca5c20fcedfd3afc272aa37254aed32a40f09ec4060933cfc1ec352df1e5'
    assert sha(plan['new_observer_ROOT']) == '40a69b368f8e6612c59480a3e8d143c7bbde4d0dc7b6a67e85cbf48a096143cd'
    reference = read(plan['new_observer_ROOT'])
    assert reference['candidate_BREP_sha256'] == plan['BREP_sha256'][1]
    assert reference['reference_FE_BREP_sha256'] != plan['BREP_sha256'][1]
    assert reference['reference_case_peak']['reference_undeformed_IP_xyz_mm'][0] == plan['section_X_mm']
    assert reference['query_stress_inferred'] is False
    assert construction['candidate_sha256'] == plan['BREP_sha256'][1]
    assert plan['BREP_sha256'] == ['d64a7faf8455735e05198661be823ead7037c23b58d36522e1cca60056aea624','24af058467fd82a9f0c1d391bf947d427dffd311371cf8f73dafa492d204f4fd']
    assert plan['launch_ready'] is (not plan['root_GO'] is None)
    if plan['launch_ready']:
        assert sha(ROOT/plan['root_GO']) == plan['root_GO_sha256']
    assert not any(n.split('.')[0] in ['OCP','build123d','gmsh','trimesh'] for n in sys.modules)


def main():
    started = time.monotonic(); planpath = HERE/'plan.json'; plan_sha = sha(planpath); plan = read(planpath)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('150 s actual-STL display limit')))
    signal.alarm(150); resource.setrlimit(resource.RLIMIT_CPU, (140,141))
    assert os.getpriority(os.PRIO_PROCESS,0) == 10
    assert all(os.environ.get(k) == '1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'])
    output = HERE/'output-001'
    assert not output.exists() and not any(p.is_symlink() for p in [output,*output.parents])
    verify(plan)
    assert plan['launch_ready'] is True
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    reader = reused(Path(plan['read_binary_source']),'read_binary',dict(Path=Path,struct=struct))
    section = reused(Path(plan['section_source']),'section_segments',{})
    spec = importlib.util.spec_from_file_location('_unchanged_complete_STL_raster',plan['raster_source'])
    raster = importlib.util.module_from_spec(spec); spec.loader.exec_module(raster)
    meshes = [reader(path) for path in plan['STLs']]
    assert [len(f) for v,f in meshes] == plan['triangle_counts']
    framing = np.concatenate([v for v,f in meshes]); box = np.array([framing.min(0),framing.max(0)])
    pictures, sections, section_records = [], [], []
    for i,(vertices,faces) in enumerate(meshes):
        tri = vertices[faces]
        normal = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); norm = np.linalg.norm(normal,axis=1)
        light = np.array([.25,-.5,.8]); light /= np.linalg.norm(light)
        shade = np.divide(normal@light,norm,out=np.zeros(len(faces)),where=norm!=0)
        colors = np.tile(matplotlib.colors.to_rgba('#5e91af'),(len(faces),1))
        colors[:,:3] *= (.35+.65*np.maximum(0.,shade))[:,None]
        pictures.append(raster.raster(np.concatenate([vertices,meshes[1-i][0]]),faces,colors,30.,0.,bounds=box))
        crossing = (tri[:,:,0].min(1)<=plan['section_X_mm']) & (tri[:,:,0].max(1)>=plan['section_X_mm'])
        segments,coplanar = section(tri[crossing],plan['section_X_mm'])
        assert len(segments)>0 and coplanar==0
        sections.append(segments[:,:,1:])
        section_records.append(dict(all_crossing_triangles=int(crossing.sum()),all_section_segments=len(segments),
                                    coplanar_triangles=coplanar,whole_profile_sha256=hashlib.sha256(segments.tobytes()).hexdigest()))
    assert pictures[0].shape == pictures[1].shape
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none',
                               'svg.hashsalt':'corner-slide-actual-surface-comparison-001','path.simplify':False})
    fig = plt.figure(figsize=(14,9),facecolor='#f5f7f9')
    fig.text(.055,.95,'993 TURBO CARRIER | ACTUAL STL PREVIEW',size=12,weight='bold',color='#536d7d')
    fig.text(.055,.895,'Reinforcing the window root',size=24,weight='bold',color='#183347')
    fig.text(.055,.85,'Before d64 → corner-slide candidate 24af | complete meshes, common camera, scale and section plane.',color='#536d7d')
    for i,label in enumerate(['Before: outward-C2 rib (d64)','After: shifted window root (24af)']):
        left=.055+i*.49
        ax=fig.add_axes([left,.61,.42,.17]); ax.imshow(pictures[i]); ax.axis('off')
        ax.set_title(label+' | '+f"{plan['masses_kg'][i]:.6f} kg",loc='left',size=12,weight='bold',pad=10)
        ax=fig.add_axes([left+.07,.23,.29,.29])
        ax.add_collection(LineCollection(sections[i],colors='#345a70' if i==0 else '#ba6337',linewidths=1.3))
        ax.set(xlim=(-18,-12),ylim=(10,17),xlabel='Y (mm)',ylabel='Z (mm)',aspect='equal')
        ax.set_title('Window root: STL section at X = 83.397 mm',loc='left',size=10,weight='bold',pad=10)
        ax.grid(alpha=.18)
    fig.text(.055,.16,'Same prior-R1 reference X plane; all intersecting facets retained. Display crop only; no stress overlay.',color='#536d7d')
    fig.text(.055,.105,'Mass 1.275992 kg / 1.30 kg cap | added 1.194 g over d64 | remaining allowance 24.01 g',size=12,weight='bold',color='#183347')
    fig.text(.055,.055,'Editable corner shift: 1.5 mm in X along AB | actual STL geometry; new-candidate audits and mechanics pending.',color='#536d7d',size=10)
    output.mkdir()
    for suffix in ['png','svg']:
        fig.savefig(output/('carrier-corner-slide-actual-surfaces.'+suffix),dpi=180,facecolor=fig.get_facecolor())
    plt.close(fig)
    loaded={str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None)
            and Path(m.__file__).is_file() and 'site-packages' in str(Path(m.__file__).resolve())}
    assert loaded <= set(plan['runtime_sha256']), sorted(loaded-set(plan['runtime_sha256']))
    verify(plan); assert sha(planpath)==plan_sha
    report=dict(schema='d64-and-corner-slide-complete-STL-preview-1',status='complete_actual_display_only',language='English',
                plan_sha256=plan_sha,inputs_sha256=plan['files_sha256'],runtime_sha256=plan['runtime_sha256'],
                loaded_runtime_files=sorted(loaded),whole_triangle_counts=plan['triangle_counts'],
                common_camera_degrees=plan['camera_degrees'],common_bounds_mm=box.tolist(),
                section_X_mm=plan['section_X_mm'],detail_YZ_mm=plan['detail_YZ_mm'],complete_sections=section_records,
                native_masses_kg=plan['masses_kg'],old_chord_or_FEA_transferred=False,geometry_modified=False,
                engineering_qualification=False,new_surface_audits='pending',wall_seconds=time.monotonic()-started,
                outputs={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(output.iterdir())})
    with (output/'receipt.json').open('x') as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=report['status'],outputs=report['outputs'],sections=section_records)))


if __name__ == '__main__':
    main()
