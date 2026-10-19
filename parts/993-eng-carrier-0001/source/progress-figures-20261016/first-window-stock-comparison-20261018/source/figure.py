"""Compare the two closed actual STL files; no CAD, audit, mesh or mechanical computation."""
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import struct
import sys
import time


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def fresh(path):
    path = Path(path)
    require(not path.exists() and not any(p.is_symlink() for p in [path, *path.parents]), 'Fresh nonsymlink output required')
    return path


def read_binary(path):
    data = Path(path).read_bytes()
    if len(data) < 84:
        raise ValueError('Truncated binary STL')
    count = struct.unpack('<I', data[80:84])[0]
    if not count or len(data) != 84 + 50 * count:
        raise ValueError('Nonempty exact-length binary STL required')
    import numpy as np
    records = np.frombuffer(data, dtype=np.dtype([('normal', '<f4', 3), ('points', '<f4', (3, 3)), ('attribute', '<u2')]), offset=84)
    points = records['points'].reshape(-1, 3).astype(np.float64)
    if not np.isfinite(points).all():
        raise ValueError('Finite STL coordinates required')
    vertices, inverse = np.unique(points, axis=0, return_inverse=True)
    return vertices, inverse.reshape(-1, 3).astype(np.int64)


def display_boxes(ledgers):
    require(set(ledgers) == {'base-without-ribs', 'outer-window-stock'}, 'Both complete branch ledgers required')
    rows = [row for branch in ledgers.values() for row in branch['rows']]
    require(len(rows) == 12, 'All twelve actual branch rows required')
    changed = [r for r in rows if r['scale'] == .9 and r['window_index'] == 0]
    require(len(changed) == 2 and [r['X_side'] for r in changed] == [-1, 1], 'The mirrored first main windows are required')
    require(all(r['inset_mm'] == 2.8 for r in changed) and all(r['inset_mm'] == 1.5 for r in rows if r not in changed), 'Only the two declared inset branches may change')
    boxes = []
    for row in changed:
        points = [[row['X_side'] * p[0], p[1]] for p in row['scaled_triangle_points_mm']]
        require(len(points) == 3 and all(math.isfinite(v) for p in points for v in p), 'Finite actual source profile required')
        boxes.append(dict(X_side=row['X_side'], XY_mm=[[min(p[a] for p in points) for a in range(2)], [max(p[a] for p in points) for a in range(2)]]))
    require(boxes[0]['XY_mm'][0][0] == -boxes[1]['XY_mm'][1][0]
            and boxes[0]['XY_mm'][1][0] == -boxes[1]['XY_mm'][0][0]
            and [p[1] for p in boxes[0]['XY_mm']] == [p[1] for p in boxes[1]['XY_mm']], 'Common mirrored source framing differs')
    return boxes


def select_data(records):
    og, omo, ng, nn, delivery = [records[k] for k in ['old_generation', 'old_mass', 'stock_generation', 'stock_native', 'delivery']]
    ogr, ogo = og; omr, omo = omo; ngr, ngo = ng; nnr, nno = nn; dr, do = delivery
    require(ogr['new_STL_sha256'] == ogo['STL_sha256'] == '8d0b09b705e17ae2a8a57588ae44879790c97ef31fbd7ec44995536971442a6d', 'Original 07b STL differs')
    require(ogr['new_STL_triangles'] == ogo['triangles'] == 637850 and ogr['new_STL_bytes'] == ogo['STL_bytes'] == 31892584, 'Whole original surface roster differs')
    require(ogo['master_BREP_sha256'] == '07b354e3716b4e856010e271f7a36aa7f6fe05a4ee4ce36eb0959af84e92409e', 'Original native master differs')
    require(ogo['actual_outer_returncode'] == ogo['actual_child_returncode'] == 0 and ogo['fresh_owned_group_absent'] is True, 'Original generation is not closed')
    require(omr['mass_kg'] == omo['mass_kg'] == 1.2623644100871174 and omo['actual_tool_and_child_returncode'] == 0, 'Original native mass differs')
    require(ngr['schema'] == 'root-first-window-stock-surface-terminal-review-1' and ngr['status'] == 'closed_actual_RC0_dedicated_stock_surface_export_only', 'Fresh stock surface ROOT differs')
    require(ngo['schema'] == 'owned-first-window-stock-surface-terminal-1' and ngo['status'] == 'closed_actual_RC0_surface_generated_not_yet_audited', 'Fresh stock owner scope differs')
    require(ngr['STL_sha256'] == ngo['STL_sha256'] == '433c85bfbffb53b443fa1a9f478fdffb1bae38e1f1960833ad3a30dc8581db77'
            and ngr['triangles'] == ngo['triangles'] == 582946 and ngr['STL_bytes'] == ngo['STL_bytes'] == 29147384, 'Fresh stock complete STL differs')
    require(ngo['actual_outer_returncode'] == ngo['actual_child_returncode'] == 0 and ngo['direct_child_reaped'] and ngo['owned_group_empty'], 'Fresh stock surface not closed')
    require(nnr['schema'] == 'root-first-window-stock-native-terminal-review-1' and nnr['candidate_BREP_sha256'] == '42da92ccbcf08783e69edba68bbeb56d3963746538d48682a3e495310a88e776', 'Stock native master differs')
    require(nnr['status'] == 'closed_actual_RC0_saved_stock_local_geometry_and_same_Solid_volume_only' and nno['actual_child_returncode'] == 0 and nno['direct_child_reaped'] and nno['owned_group_empty'], 'Stock local native evidence not closed')
    require(ngr['CAD_source'] == ngo['CAD_source'] and ngr['CAD_source']['format'] == 'brep'
            and ngr['CAD_source']['sha256'] == nnr['candidate_BREP_sha256'], 'Stock generation used a different native master')
    require(ngr['stock_native_owner_sha256'] == nnr['owner_terminal_sha256'] and ngr['stock_native_assessment_sha256'] == nnr['assessment_sha256'], 'Stock native/surface lineage differs')
    require(nnr['measurements']['mass_kg'] == 1.2678353778376648 and nnr['candidate_qualified'] is False
            and nnr['old_complete7_law_inherited'] is False and nnr['current07b_subset_required'] is False, 'Do not transfer the old blend or results')
    require(dr['schema'] == 'root-first-window-stock-geometry-copy-terminal-review-1'
            and dr['status'] == 'closed_actual_RC0_exact139_durable_stock_geometry_source_files_no_native_replay'
            and do['archive_sha256'] == '730c240cd6dfbed3f0fec607b6325674990e4a27e696d4df686bdee9df0333ce', 'Actual stock delivery closure differs')
    old = dict(label='Previous 07b design', BREP_sha256=ogo['master_BREP_sha256'], STL_sha256=ogo['STL_sha256'], STL_triangles=ogo['triangles'], STL_bytes=ogo['STL_bytes'], native_mass_kg=omo['mass_kg'], first_main_window_inset_mm=1.5)
    stock = dict(label='Stock-only first-window trial', BREP_sha256=nnr['candidate_BREP_sha256'], STL_sha256=ngo['STL_sha256'], STL_triangles=ngo['triangles'], STL_bytes=ngo['STL_bytes'], native_mass_kg=nnr['measurements']['mass_kg'], first_main_window_inset_mm=2.8)
    return dict(schema='closed-two-STL-first-window-comparison-data-1', cases=[old, stock], display_boxes=display_boxes(nnr['all12_actual_source_window_branch_rows']),
                native_mass_difference_g=(stock['native_mass_kg']-old['native_mass_kg'])*1000, mass_ceiling_kg=1.3,
                inset_is_cut_profile_parameter_not_wall_thickness=True, stock_also_discards_old07b_blend=True,
                old_FEA_transferred=False, current_stock_FEA_shown=False, geometry_or_interface_qualification_granted=False)


def verify(plan_path, expected, rendering=False, hash_STL=True):
    require(sha(plan_path) == expected, 'Plan hash differs')
    plan = read(plan_path); root = Path(plan['source_root'])
    require(plan['schema'] == 'stock-two-actual-STL-comparison-figure-plan-1' and plan['bounds'] == dict(outer=180, inner=150, CPU=[140,141], threads=1, workers=0), 'Figure scope or budget differs')
    require(plan['overview_camera_degrees'] == [30.0,0.0] and plan['detail_axes'] == [0,1]
            and plan['detail_view_from_positive_Z'] is True and plan['native_calls'] == 0, 'Actual-coordinate display contract differs')
    if rendering:
        require(plan['launch_ready'] is True and plan['root_GO'] is not None and sha(root/plan['root_GO']) == plan['root_GO_sha256'], 'NOT ARMED: ROOT render GO required')
    data = read(root/plan['data'])
    for name, digest in plan['files_sha256'].items():
        if name in plan['STLs'] and not hash_STL:
            require((root/name).stat().st_size == data['cases'][plan['STLs'].index(name)]['STL_bytes'], 'Closed surface byte length differs')
        else:
            require(sha(root/name) == digest, 'Frozen source/input/runtime differs: ' + name)
    require(len(plan['runtime_sha256']) == 5259 and all(plan['files_sha256'].get(n) == h for n,h in plan['runtime_sha256'].items()), 'Unchanged Figure30 runtime required')
    require((root/plan['raster_original']).read_bytes() == (root/plan['raster_copy']).read_bytes(), 'Original raster helper changed')
    old = (root/plan['figure_original']).read_text(); current = Path(__file__).read_text()
    for name in ['require','sha','read','write','fresh','read_binary']:
        def segment(text):return ast.get_source_segment(text,next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name))
        require(segment(old) == segment(current), 'Original loader/IO helper changed: ' + name)
    records = {}
    for role, context in plan['closed_context'].items():
        review,owner = read(root/context['ROOT']),read(root/context['owner'])
        require(review['owner_terminal_sha256'] == sha(root/context['owner']), 'Whole ROOT/owner join differs: ' + role)
        records[role] = [review,owner]
    require(records['old_generation'][1]['addition_ROOT_sha256'] == sha(root/plan['closed_context']['old_mass']['ROOT']), 'Original mass/generation join differs')
    require(records['stock_generation'][1]['stock_native_ROOT_sha256'] == sha(root/plan['closed_context']['stock_native']['ROOT']), 'Stock native/generation join differs')
    require(data == select_data(records), 'Whole closed display data differs')
    require(read(root/plan['nominal_study'])['geometry']['window_edge_inset_mm'] == 1.5, 'Historical nominal inset differs')
    require([plan['files_sha256'][n]for n in plan['STLs']] == [r['STL_sha256']for r in data['cases']], 'Actual two STL authorities differ')
    require(not any(n.split('.')[0] in ['OCP','build123d','gmsh','trimesh'] for n in sys.modules), 'Native geometry module imported')
    return plan,data


def render(plan_path, expected, output):
    started=time.monotonic();plan,data=verify(plan_path,expected,rendering=True)
    root=Path(plan['source_root']);require(Path(output)==root/plan['output_directory'],'Declared output differs')
    output=fresh(output);output.mkdir()
    write(output/'render-started.json',dict(status='MARKER_BEFORE_IMAGE_AUTHORING',plan_sha256=expected,source_sha256=sha(__file__),STLs=plan['STLs'],formats=['png','svg','pdf'],native_calls=0))
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    import vispy
    meshes=[read_binary(root/n)for n in plan['STLs']]
    require([len(f)for v,f in meshes]==[r['STL_triangles']for r in data['cases']],'Both complete triangle rosters required')
    # Both overview fits receive the same union of actual vertices. Other-case
    # vertices are unused by the current faces and introduce no rendered geometry.
    framing=np.concatenate([v for v,f in meshes]);common_box=np.array([framing.min(0),framing.max(0)])
    spec=importlib.util.spec_from_file_location('_literal_actual_surface_raster',root/plan['raster_copy'])
    raster=importlib.util.module_from_spec(spec);spec.loader.exec_module(raster)
    pictures=[];triangles=[];colors=[]
    for i,(vertices,faces)in enumerate(meshes):
        tri=vertices[faces];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);lengths=np.linalg.norm(normal,axis=1)
        light=np.array([.25,-.5,.8]);light/=np.linalg.norm(light)
        illumination=np.divide(normal@light,lengths,out=np.zeros(len(faces)),where=lengths!=0)
        color=np.tile(matplotlib.colors.to_rgba('#5e91af'),(len(faces),1));color[:,:3]*=(.35+.65*np.maximum(0.,illumination))[:,None]
        framed=np.concatenate([vertices,meshes[1-i][0]])
        pictures.append(raster.raster(framed,faces,color,30.,0.,bounds=common_box));triangles.append(tri);colors.append(color)
    require(pictures[0].shape==pictures[1].shape,'Common framing returned different pixel crops; no independent rescaling allowed')
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','svg.hashsalt':'first-window-stock-comparison-001','pdf.fonttype':42,'path.simplify':False})
    fig=plt.figure(figsize=(15,12),facecolor='#f5f7f9')
    fig.text(.045,.965,'993 TURBO CARRIER · FIRST-WINDOW DESIGN TRIAL',fontsize=12,weight='bold',color='#536d7d')
    fig.text(.045,.925,'A wider inset, compared in the same coordinates',fontsize=23,weight='bold',color='#183347')
    fig.text(.045,.892,'Cut-profile inset 1.5 → 2.8 mm on the two first main windows; this is not a wall-thickness measurement.',fontsize=10.5,color='#536d7d')
    selected_rows=[]
    for i,case in enumerate(data['cases']):
        left=.045+i*.495
        ax=fig.add_axes([left,.66,.43,.19]);ax.imshow(pictures[i]);ax.axis('off')
        ax.set_title(case['label']+'  |  '+f"{case['native_mass_kg']:.6f} kg",loc='left',fontsize=12,weight='bold',color='#183347',pad=9)
        for j,roi in enumerate(data['display_boxes']):
            box=np.array(roi['XY_mm']);tri=triangles[i]
            selected=((tri[:,:,[0,1]].max(1)>=box[0])&(tri[:,:,[0,1]].min(1)<=box[1])).all(1)
            require(selected.any(),'Actual source-profile display crop is empty')
            order=np.argsort(tri[selected,:,2].mean(1),kind='stable')
            ax=fig.add_axes([left+.035,.39-j*.27,.36,.21])
            ax.add_collection(PolyCollection(tri[selected][:,:,[0,1]][order],facecolors=colors[i][selected][order],edgecolors='#425f72',linewidths=.12,rasterized=True))
            ax.set(xlim=box[:,0],ylim=box[:,1],xlabel='X (mm)',ylabel='Y (mm)');ax.set_aspect('equal');ax.set_facecolor('white')
            ax.set_title(('Left'if roi['X_side']==-1 else'Right')+' first window · common XY crop',loc='left',fontsize=10.5,weight='bold',color='#183347',pad=6)
            selected_rows.append(dict(case=i,X_side=roi['X_side'],selected_triangles=int(selected.sum()),XY_mm=roi['XY_mm']))
    fig.text(.045,.075,f"Native CAD mass change: +{data['native_mass_difference_g']:.2f} g  |  Declared ceiling: 1.30 kg  |  Density: 4,420 kg/m³",fontsize=11,weight='bold',color='#183347')
    fig.text(.045,.047,'Stock-only design: the old 07b blend is not carried over. Actual complete STL views; close-ups are display crops.',fontsize=9.5,color='#536d7d')
    fig.text(.045,.022,'No old FEA is transferred. This image establishes no interface, strength, convergence or manufacturing qualification.',fontsize=9.2,color='#984823')
    verify(plan_path,expected,rendering=True)
    for suffix in ['png','svg','pdf']:
        metadata={'Date':None,'Creator':'Actual first-window stock comparison'}if suffix=='svg'else({'CreationDate':None,'ModDate':None,'Creator':'Actual first-window stock comparison'}if suffix=='pdf'else{'Software':'Actual first-window stock comparison'})
        path=output/('carrier-first-window-stock-comparison.'+suffix);fig.savefig(path,dpi=180,metadata=metadata)
        if suffix=='png':write(output/'PNG-ready.json',dict(status='PNG_WRITTEN_BEFORE_VECTOR_EXPORTS',sha256=sha(path)))
    plt.close(fig);verify(plan_path,expected,rendering=True)
    runtime={str((root/n).resolve()):h for n,h in plan['runtime_sha256'].items()}
    loaded={str(Path(m.__file__).resolve())for m in list(sys.modules.values())if getattr(m,'__file__',None)and Path(m.__file__).is_file()and'site-packages'in str(Path(m.__file__).resolve())}
    write(output/'runtime-origin-diagnostic.json',dict(runtime_imported_files=sorted(loaded),outside_runtime_imported_files=sorted(loaded-set(runtime)),declared_runtime_file_count=len(runtime)))
    require(loaded<=set(runtime),'Plot import outside the unchanged runtime')
    write(output/'render-receipt.json',dict(schema='actual-two-STL-first-window-stock-comparison-render-1',status='display_only_six_panels_complete_STLs_common_framing',plan_sha256=expected,source_sha256=sha(__file__),cases=data['cases'],display_boxes=data['display_boxes'],common_framing_bounds_mm=common_box.tolist(),overview_pixel_shapes=[list(p.shape)for p in pictures],all_faces_retained_in_overviews=True,framing_vertices_are_only_actual_vertices_from_both_inputs=True,closeups=selected_rows,closeup_view='positive_Z_XY_painter_sorted',native_mass_difference_g=data['native_mass_difference_g'],runtime_imported_files=sorted(loaded),runtime=dict(numpy=np.__version__,matplotlib=matplotlib.__version__,vispy=vispy.__version__),geometry_modified=False,native_calls=0,old_FEA_transferred=False,engineering_qualification_transferred=False,wall_seconds=time.monotonic()-started,exports_sha256={p.name:sha(p)for p in sorted(output.iterdir())}))


if __name__=='__main__':
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
    mode,plan_path,expected=sys.argv[1:4]
    if mode=='preflight':
        plan,data=verify(plan_path,expected,hash_STL=False)
        print(json.dumps(dict(status='SOURCE_ONLY_NO_STL_BODY_OR_SCIENTIFIC_IMPORT',pins=len(plan['files_sha256']),runtime_files=len(plan['runtime_sha256']),complete_STL_triangles=[c['STL_triangles']for c in data['cases']])))
    elif mode=='render':
        signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150-second comparison figure budget')))
        signal.setitimer(signal.ITIMER_REAL,150);resource.setrlimit(resource.RLIMIT_CPU,(140,141));os.chdir('/')
        render(plan_path,expected,sys.argv[4])
    else:raise SystemExit('Usage: figure.py preflight PLAN SHA | render ARMED_PLAN SHA FRESH_OUTPUT')
