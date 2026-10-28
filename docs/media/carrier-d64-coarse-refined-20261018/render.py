"""Four actual same-d64 coarse/refined fields; no new solver or convergence claim."""
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time


def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):
    d=hashlib.sha256()
    with Path(path).open('rb')as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):d.update(block)
    return d.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):
    with Path(path).open('x')as f:json.dump(value,f,ensure_ascii=False,allow_nan=False,indent=2);f.write('\n')
def fresh(path):
    path=Path(path)
    require(not path.exists()and not any(p.is_symlink()for p in [path,*path.parents]),'Fresh nonsymlink output required')
    return path

def maxima_record(global_vm,boundary_vm,global_u,peaks):
    require(all(math.isfinite(v)and v>=0 for v in [global_vm,boundary_vm,global_u])and boundary_vm<=global_vm,'Invalid or confused field maxima')
    require(peaks and all(p['VM_MPa']==global_vm for p in peaks),'All reported global ties must be kept')
    return dict(global_IP_VM_MPa=global_vm,displayed_boundary_element_VM_max_MPa=boundary_vm,all_nodes_Umax_mm=global_u,all_global_IP_ties=peaks)

def literal_functions(root,provenance):
    current=Path(__file__).read_text();tree=ast.parse(current)
    for path,names in provenance.items():
        original=(root/path).read_text();old=ast.parse(original)
        for name in names:
            a=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
            b=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name==name)
            require(ast.get_source_segment(current,a)==ast.get_source_segment(original,b),'Original function changed: '+name)

def validate_case(row,docs,hashes,root_case):
    whole,a,native,record,peaks,energy,loads=[docs[k]for k in ['terminal','assessment','native_receipt','record','peaks','energy','loads']]
    role=row['role'];term=whole['cases'][role];expected={'rigid':'combined-rigid-static','spring':'combined-spring-1000-static'}
    require(role in expected and row['case']==expected[role]and a['case_name']==row['case']==record['name']==peaks['case']==energy['case'],'Wrong closed case identity')
    statuses={'coarse':'closed_actual_RC0_two_new_rib_static_and_independent_energy_cases','saved_refined':'closed_actual_RC0_two_d64_saved_refined_static_and_independent_energy_cases'}
    require(whole['status']==statuses[row['mesh_variant']]and term['actual_tool_returncode']==term['actual_container_returncode']==term['attach_cli_returncode']==0 and term['owned_container_removed']and term['all_current_pins_equal'],'Case not actually closed')
    require(a['status']=='actual_linear_static_and_independent_energy_completed'and a['sources_unchanged']and a['plan_unchanged']and a['all_global_maxima_included']and a['candidate_qualified']is False and a['candidate_version']=='stock-outward-C2-rib-width-v1'and a['old_complete7_law_inherited']is False,'Assessment scope differs')
    require(term['assessment_sha256']==hashes[row['assessment']]and term['native_receipt_sha256']==hashes[row['native_receipt']],'Whole actual report SHA join differs')
    require(root_case['all_global_peak_ties']==term['all_global_peak_ties']==peaks,'Whole ROOT/owner/global peak objects differ')
    if row['mesh_variant']=='coarse':
        require(root_case['VM_max_MPa']==record['integration_point_VM_max_MPa']and root_case['U_max_mm']==record['displacement_max_mm'],'Coarse ROOT result differs')
    else:
        require(row['mesh_variant']=='saved_refined'and root_case['actual_native_result']==term['actual_native_result']==record and root_case['whole_same_d64_coarse_comparisons']==a['comparisons_to_same_d64_coarse'],'Whole refined ROOT result/comparisons differ')
        require(a['original_generated_volume_refusal_preserved']and a['refined_mesh_distinct_serialized_reference']and whole['original_generated_volume_refusal_preserved'],'Original generated-volume refusal lost')
    require(native['actual_container_exit_code']==native['attach_cli_returncode']==0 and native['container_removed']and native['input_hashes_unchanged'],'Native container not closed')
    require(a['native_result']==record and a['prepared_actual_load_supports']==loads and a['energy_audit_sha256']==hashes[row['energy']]and a['global_peaks_sha256']==hashes[row['peaks']],'Whole result/load/audits differ')
    parent=Path(row['terminal']).parent
    for key in ['record','field','deck','mesh_inp','mesh_npz','mesh_meta','loads','energy','peaks']:
        path=row[key];entry=term['whole_outputs'][str(Path(path).relative_to(parent))]
        require(entry['sha256']==hashes[path],'Actual whole output differs: '+key)
    require(record['mesh_sha256']==hashes[row['mesh_inp']]and record['input_sha256']==hashes[row['deck']],'Mesh/deck not same case')
    require(energy['energy_closure_pass']and energy['tolerance']==1e-4 and energy['relative_energy_closure_error']<=1e-4,'Original energy gate failed')
    require(peaks['no_peak_excluded']and peaks['maximum_ties']==len(peaks['all_global_maximum_ties'])and peaks['maximum_VM_MPa']==record['integration_point_VM_max_MPa'],'Global IP ties lost')
    require(loads['target_force_N']==[0,0,-4000]and loads['target_moment_Nmm']==[0,850000,0]and loads['unchanged_original_distribute_unrounded_resultant_assertions_reached'],'Actual loads differ')
    require(loads['actual_eye_node_counts']==[2278,2274]and loads['serialized_CLOAD_entries']==6336,'Actual rosters differ')
    if role=='rigid':require(loads['rigid_constrained_DOFs']==13656 and loads['SPRING1_elements']==0 and loads['springs']==[],'Rigid support differs')
    else:
        require(loads['rigid_constrained_DOFs']==0 and loads['SPRING1_elements']==13656 and len(loads['springs'])==6,'Spring support differs')
        require({(s['eye'],s['DOF'])for s in loads['springs']}=={(i,j)for i in range(2)for j in range(1,4)}and all(s['summed_card_stiffness_N_mm']==s['declared_total_per_eye_axis_N_mm']==1000 for s in loads['springs']),'K1000 must remain total per eye/axis')
    return dict(row,record_data=record,peak_data=peaks,energy_data=energy,load_data=loads)

def verify(plan_path,expected,rendering=False):
    plan_path=Path(plan_path);require(sha(plan_path)==expected,'Plan hash differs');plan=read(plan_path)
    require(plan['schema']=='actual-d64-four-case-field-comparison-plan-1'and plan['actual_workers']==0 and plan['deformation_amplification']==1,'Wrong four-case scope')
    if rendering:require(plan['launch_ready']is True and plan['root_GO_sha256']is not None and sha(plan['root_GO'])==plan['root_GO_sha256'],'NON-ARMED: no array extraction/render before root review')
    root=Path(plan['source_root']);hashes=plan['files_sha256'];require(all(hashes.get(name)==h for name,h in plan['runtime_sha256'].items()),'Runtime binding conflicts')
    require(all(sha(root/name)==h for name,h in hashes.items()),'Input/source/runtime hash differs')
    require(hashes[str(Path(__file__).relative_to(root))]==sha(__file__),'Renderer not pinned');literal_functions(root,plan['literal_functions'])
    expected_roots={'coarse':('c64f9d0ab71cfce7ddb4d000e73ff53019e44d05c1f994ac98960dc4fc64a1eb','root-new-rib-two-static-terminal-review-1','closed_actual_RC0_two_d64_static_cases_full_original_energy_and_peaks_PASS'),
        'saved_refined':('7da132106b7bc0a8bb01640126b1c20e8849dfa5b2e8fbd878ac23dd55f3bc10','root-d64-saved-refined-two-static-terminal-review-1','closed_actual_RC0_two_d64_saved_refined_static_and_independent_energy_cases')}
    reviews={}
    for variant,context in plan['closed_contexts'].items():
        review=read(root/context['root_review']);digest,schema,status=expected_roots[variant]
        require(sha(root/context['root_review'])==context['root_review_sha256']==hashes[context['root_review']]==digest and review['schema']==schema and review['status']==status,'Actual ROOT identity/scope differs')
        require(hashes[context['combined_terminal']]==context['combined_terminal_sha256']==review['owner_terminal_sha256'],'Whole actual owner not joined')
        require(review['candidate_BREP_sha256']==plan['actual_BREP_sha256']and review['candidate_qualified']is False,'Candidate identity/scope differs');reviews[variant]=review
    require(set(reviews)=={'coarse','saved_refined'},'Both actual mesh contexts required')
    order=[('rigid','coarse'),('rigid','saved_refined'),('spring','coarse'),('spring','saved_refined')]
    require([(r['role'],r['mesh_variant'])for r in plan['cases']]==order,'Four actual cases in exact order required');rows=[]
    for row in plan['cases']:
        require(row['terminal']==plan['closed_contexts'][row['mesh_variant']]['combined_terminal'],'Foreign case terminal')
        docs={key:read(root/row[key])for key in ['terminal','assessment','native_receipt','record','peaks','energy','loads']}
        rows.append(validate_case(row,docs,hashes,reviews[row['mesh_variant']]['cases'][row['role']]))
    for variant in reviews:
        group=[r for r in rows if r['mesh_variant']==variant]
        require(len({hashes[r['mesh_inp']]for r in group})==len({hashes[r['mesh_npz']]for r in group})==1,'Common actual mesh per variant required')
    require(len({hashes[r['mesh_inp']]for r in rows})==2,'Two distinct actual meshes required')
    for role in ['rigid','spring']:
        group=[r for r in rows if r['role']==role]
        require(hashes[group[0]['loads']]==hashes[group[1]['loads']]and group[0]['load_data']==group[1]['load_data'],'Complete same-d64 load/support records differ')
    require(all(r['peak_data']['CAD_source']['sha256']==plan['actual_BREP_sha256']=='d64a7faf8455735e05198661be823ead7037c23b58d36522e1cca60056aea624'for r in rows),'Actual same CAD differs')
    diagnostic=read(root/plan['mesh_diagnostic_ROOT'])
    require(sha(root/plan['mesh_diagnostic_ROOT'])==plan['mesh_diagnostic_ROOT_sha256']=='065b64a2234fd2d2e4f1c807923078d56cf4096212892f55f67eca07a71aa811'and diagnostic['h2_qualified_under_distinct_serialized_reference']and diagnostic['original_generated_volume_guard_passed']is False,'Distinct actual mesh diagnostic/refusal differs')
    require(sha(plan_path)==expected,'Plan changed during preflight');return plan,rows

def boundary_values(faces, connectivity, element_ids, vm):
    values = {}
    unique, reverse = np.unique(element_ids, return_inverse=True)
    peaks = np.full(len(unique), -np.inf)
    np.maximum.at(peaks, reverse, vm)
    assert set(unique) == set(connectivity)
    wanted = {tuple(sorted(face)) for face in faces}
    for element, peak in zip(unique, peaks):
        nodes = connectivity[int(element)]
        for indices in ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)):
            key = tuple(sorted(nodes[index] for index in indices))
            if key in wanted:
                if key in values:
                    raise ValueError('Declared surface face is internal to two elements')
                values[key] = peak
    result = np.asarray([values[tuple(sorted(face))] for face in faces])
    assert np.isfinite(result).all()
    return result

def camera_basis(azimuth_deg=8, elevation_deg=22):
    azimuth, elevation = np.radians([azimuth_deg, elevation_deg])
    horizontal = np.array([np.cos(azimuth), np.sin(azimuth), 0.])
    vertical = np.array([-np.sin(azimuth) * np.sin(elevation),
                         np.cos(azimuth) * np.sin(elevation), np.cos(elevation)])
    return np.vstack((horizontal, vertical, np.cross(horizontal, vertical)))

def project(points, basis):
    coordinates = np.asarray(points) @ basis.T
    return coordinates[:, :2], coordinates[:, 2]

def elements(path):
    result = {}; active = False
    for line in path.read_text().splitlines():
        if line.startswith('*'):
            active = line.upper().startswith('*ELEMENT')
        elif active and line.strip():
            row = [int(v) for v in line.split(',') if v.strip()]
            assert len(row) == 11
            result[row[0]] = row[1:]
    return result

def render(plan_path,expected,output):
    started=time.monotonic();plan,rows=verify(plan_path,expected,True);root=Path(plan['source_root']);output=fresh(output)
    os.environ['MPLBACKEND']='Agg'
    global np
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import colors
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Rectangle
    import matplotlib.backends.backend_pdf,matplotlib.backends.backend_svg
    import PIL
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':9.5,'text.color':'#183347','axes.labelcolor':'#536D7D',
        'svg.fonttype':'none','svg.hashsalt':'carrier-d64-coarse-refined-fields-001','pdf.fonttype':42,'path.simplify':False})
    basis=camera_basis();cases=[];all_bounds=[]
    for row in rows:
        with np.load(root/row['mesh_npz'],allow_pickle=False)as mesh,np.load(root/row['field'],allow_pickle=False)as field:
            tags=mesh['tags'];xyz=mesh['xyz'];faces=mesh['faces'];u=field['displacement'];vm=field['VM'];eids=field['element_ids']
            require(tags.dtype.kind in 'iu'and xyz.dtype==np.float64 and faces.dtype.kind in 'iu'and np.all(np.diff(tags)>0),'Actual sorted node tags and float64 positions required')
            require(np.array_equal(tags,field['tags'])and np.array_equal(xyz,field['xyz'])and u.shape==xyz.shape and np.isfinite(u).all()and np.isfinite(vm).all(),'Actual field/mesh identity differs')
            require(len(tags)==row['peak_data']['nodes']and len(vm)==4*row['peak_data']['C3D10_elements'],'Full four-IP field required')
            connectivity=elements(root/row['mesh_inp']);ids=np.searchsorted(tags,faces);require(np.array_equal(tags[ids],faces),'Actual surface tags missing')
            unique,counts=np.unique(eids,return_counts=True);require(np.all(counts==4)and len(unique)==len(connectivity),'Exactly four IPs per actual T10 required')
            amplitude=np.linalg.norm(u,axis=1);require(float(vm.max())==row['record_data']['integration_point_VM_max_MPa']and float(amplitude.max())==row['record_data']['displacement_max_mm'],'Global maxima differ')
            peak_rows=np.flatnonzero(vm==vm.max()).tolist();peaks=row['peak_data']['all_global_maximum_ties']
            require(peak_rows==[p['DAT_row_zero_based']for p in peaks]and all(int(eids[i])==p['element_id']and i%4+1==p['IP_one_based']for i,p in zip(peak_rows,peaks)),'Not all global IP rows retained')
            stress=boundary_values(faces,connectivity,eids,vm);corners=amplitude[ids].max(1)
            summary=maxima_record(float(vm.max()),float(stress.max()),float(amplitude.max()),peaks)
            for points in [xyz,xyz+u]:
                projection,_=project(points,basis);all_bounds.append([projection.min(0),projection.max(0)])
            cases.append(dict(row=row,tags=tags,xyz=xyz,faces=faces,ids=ids,u=u,stress=stress,amplitude=amplitude,corner_u=corners,summary=summary))
    vm_scale=max(c['summary']['global_IP_VM_MPa']for c in cases);u_scale=max(c['summary']['all_nodes_Umax_mm']for c in cases)
    lower=np.min(np.asarray(all_bounds)[:,0,:],0)-[9,6];upper=np.max(np.asarray(all_bounds)[:,1,:],0)+[9,6]
    fig,axes=plt.subplots(2,4,figsize=(24,12.4),facecolor='#F8FAFC');fig.subplots_adjust(left=.055,right=.88,top=.78,bottom=.26,wspace=.14,hspace=.17)
    fig.text(.055,.955,'993 TURBO · SAME d64 CAD · FOUR CLOSED LINEAR CASES',fontsize=11,color='#536D7D',weight='bold')
    fig.text(.055,.918,'Coarse versus refined: stress and displacement',fontsize=23,weight='bold')
    fig.text(.055,.887,'Fz = −4 000 N · My = +850 000 N·mm · common camera, mm axes and field scales',fontsize=10.5)
    fig.text(.055,.86,'Coarse: 85 767 T10 / 159 612 nodes · refined: 87 256 T10 / 161 826 nodes · true deformation ×1 · BREP '+rows[0]['peak_data']['CAD_source']['sha256'][:12]+'…',fontsize=10,color='#087E8B')
    fig.text(.055,.834,'Rigid: 4 552 nodes fixed in XYZ. K1000: 1 000 N/mm TOTAL per eye and axis, distributed over 2 278 / 2 274 nodes.',fontsize=9.4)
    norms=[colors.Normalize(0,vm_scale),colors.Normalize(0,u_scale)];cmap=plt.get_cmap('viridis');checks=[];first_peak_labels=[]
    # Each display-only crop follows this actual case peak, including the measured migration across X.
    zoom=plan['display_zoom_XY_mm']
    for col,c in enumerate(cases):
        row=c['row'];xyz=c['xyz'];ids=c['ids'];rest,_=project(xyz,basis);zoom_bounds=np.asarray(zoom[row['case_key']])
        for r in range(2):
            ax=axes[r,col];points=xyz if r==0 else xyz+c['u'];values=c['stress']if r==0 else c['corner_u']
            xy,depth=project(points,basis);order=np.argsort(depth[ids].mean(1),kind='stable')
            if r:ax.add_collection(PolyCollection(rest[ids],facecolors='#E2E7EC',edgecolors='none',rasterized=True))
            ax.add_collection(PolyCollection(xy[ids][order],facecolors=cmap(norms[r](values[order])),edgecolors='none',rasterized=True))
            title=row['display_label']+' — '+('von Mises'if r==0 else'actual displacement ×1')
            ax.set(xlim=(lower[0],upper[0]),ylim=(lower[1],upper[1]),xlabel='Projected U (mm)',ylabel='Projected V (mm)',title=title)
            ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.12);ax.set_axisbelow(True);ax.tick_params(labelsize=8);ax.spines[['top','right']].set_visible(False)
            if r==0:
                for peak in c['summary']['all_global_IP_ties']:
                    marker,_=project([peak['reference_undeformed_IP_xyz_mm']],basis)
                    ax.scatter(*marker[0],s=100,marker='o',facecolors='none',edgecolors='#D47732',linewidths=1.5,zorder=5)
                    annotation=ax.annotate('Global IP peak',marker[0],xytext=(0.70,0.80) if col==0 else (12,-26),ha='right' if col==0 else 'left',textcoords='axes fraction' if col==0 else 'offset points',fontsize=8,color='#9A491E',arrowprops=dict(arrowstyle='-',color='#D47732'))
                    if col==0:first_peak_labels.append((ax,annotation))
                inset=fig.add_axes([.12+.212*col,.475,.10,.075]);top=np.argsort(xyz[ids][:,:,2].mean(1),kind='stable');inset.add_collection(PolyCollection(xyz[ids][top,:,:2],facecolors=cmap(norms[0](c['stress'][top])),edgecolors='none',rasterized=True))
                inset.set(xlim=zoom_bounds[:,0],ylim=zoom_bounds[:,1],xlabel='X (mm)',ylabel='Y (mm)');inset.set_aspect('equal');inset.tick_params(labelsize=6);inset.set_title('Peak-region XY · shared MPa scale',fontsize=6.7)
                for peak in c['summary']['all_global_IP_ties']:inset.scatter(*peak['reference_undeformed_IP_xyz_mm'][:2],s=40,facecolors='none',edgecolors='#D47732',linewidths=1.2,zorder=5)
            else:
                maxima=np.flatnonzero(c['amplitude']==c['amplitude'].max())
                p,_=project((xyz+c['u'])[maxima],basis);ax.scatter(p[:,0],p[:,1],s=35,marker='x',color='#D47732',zorder=5)
                c['summary']['all_global_U_nodes']=[dict(node_id=int(c['tags'][i]),reference_xyz_mm=xyz[i].tolist(),deformed_xyz_mm=(xyz[i]+c['u'][i]).tolist(),U_mm=float(c['amplitude'][i]))for i in maxima]
            checks.append(dict(case=row['case'],field='VM'if r==0 else'U',all_boundary_faces_submitted=len(ids),displayed_face_values=len(values),color_scale=[0,float(norms[r].vmax)],
                xlim=lower[[0]].tolist()+upper[[0]].tolist(),ylim=lower[[1]].tolist()+upper[[1]].tolist(),orthographic=True,deformation_amplification=1,decimation=False))
        c['summary']['reference_surface_faces']=len(ids);c['summary']['all_IP_rows']=4*row['peak_data']['C3D10_elements']
    for r,label in enumerate(['von Mises (MPa)','Actual |u| (mm)']):
        bar=fig.colorbar(plt.cm.ScalarMappable(norm=norms[r],cmap=cmap),cax=fig.add_axes([.91,.587 if r==0 else .323,.014,.155]));bar.set_label(label)
    cellrows=[]
    for c in cases:
        for peak in c['summary']['all_global_IP_ties']:
            p=peak['reference_undeformed_IP_xyz_mm'];cellrows.append([c['row']['display_label'],f"{peak['VM_MPa']:.3f}",f"{c['summary']['displayed_boundary_element_VM_max_MPa']:.3f}",f"{c['summary']['all_nodes_Umax_mm']:.6f}",str(peak['element_id'])+'/'+str(peak['IP_one_based']),', '.join(f'{v:.5f}'for v in p)])
    table_ax=fig.add_axes([.055,.178,.895,.085]);table_ax.axis('off')
    table=table_ax.table(cellText=cellrows,colLabels=['Case','Global IP peak (MPa)','Boundary max (MPa)','All-node |u| (mm)','Element / IP','Reference IP XYZ (mm)'],loc='center',cellLoc='center',colWidths=[.17,.13,.14,.14,.12,.30]);table.auto_set_font_size(False);table.set_fontsize(8.6);table.scale(1,1.5)
    for (r,_),cell in table.get_celld().items():cell.set_edgecolor('#DAE2E8');cell.set_facecolor('#E8F2F3'if r==0 else'white')
    fig.text(.055,.141,'Stress colours: maximum of 4 IPs in each boundary-adjacent element, without nodal extrapolation. Orange circles: every global IP peak.',fontsize=9,color='#536D7D')
    fig.text(.055,.117,'Linear C3D10 corner facets; actual corner displacement ×1. Grey: reference shape. Crosses: every all-node maximum of |u|.',fontsize=9,color='#536D7D')
    fig.text(.055,.093,'Displacement colours use the largest of each facet’s 3 corner values; the global maximum also includes midside nodes.',fontsize=9,color='#536D7D')
    fig.text(.055,.061,'Same d64 BREP, two actual meshes. Assumed linear loads/material; no strength allowable or stress convergence established.',fontsize=9,color='#536D7D')
    fig.text(.055,.037,'Original generated-volume refusal retained; distinct serialized-reference/H2 checks passed. Orthographic view 8° / 22°.',fontsize=9,color='#536D7D')
    # Display-only validation at the existing PNG export resolution; no field criterion.
    fig.set_dpi(180);fig.canvas.draw();layout_renderer=fig.canvas.get_renderer();first_label_layout=[]
    for axis,annotation in first_peak_labels:
        box=annotation.get_window_extent(layout_renderer);axes_box=axis.get_window_extent(layout_renderer)
        inside=axes_box.x0<=box.x0<=box.x1<=axes_box.x1 and axes_box.y0<=box.y0<=box.y1<=axes_box.y1
        require(inside,'First global-peak callout leaves its own axes')
        first_label_layout.append(dict(textcoords='axes fraction',xytext=[0.70,0.80],ha='right',PNG_DPI=180,text_and_arrow_bbox_pixels=list(box.extents),axes_bbox_pixels=list(axes_box.extents),inside_own_axes=bool(inside)))
    require(len(first_label_layout)==len(cases[0]['summary']['all_global_IP_ties']),'First-case callout check incomplete')
    loaded={str(Path(m.__file__).resolve())for n,m in list(sys.modules.items())if n.split('.')[0]in ['numpy','matplotlib','PIL']and getattr(m,'__file__',None)and Path(m.__file__).is_file()}
    runtime=plan['runtime_sha256'];require(loaded<=set(runtime),'An imported scientific runtime file is outside the attested runtime')
    verify(plan_path,expected,True);fresh(output).mkdir()
    for ext in ['png','svg','pdf']:
        metadata={'Date':None,'Creator':'Actual same-d64 coarse/refined finite-element fields'}if ext=='svg'else({'CreationDate':None,'ModDate':None,'Creator':'Actual same-d64 coarse/refined finite-element fields'}if ext=='pdf'else{'Software':'Actual same-d64 coarse/refined finite-element fields'})
        fig.savefig(output/('carrier-d64-coarse-refined-comparison.'+ext),dpi=180,metadata=metadata)
    plt.close(fig);verify(plan_path,expected,True)
    loaded_after={str(Path(m.__file__).resolve())for n,m in list(sys.modules.items())if n.split('.')[0]in ['numpy','matplotlib','PIL']and getattr(m,'__file__',None)and Path(m.__file__).is_file()}
    require(loaded_after<=set(runtime),'A post-export runtime file is outside the219 pinned files')
    write(output/'render-receipt.json',dict(status='actual_closed_coarse_refined_diagnostic_fields_rendered_no_new_FEA',plan_sha256=expected,source_sha256=sha(__file__),
        data_sources_sha256=plan['files_sha256'],runtime_sha256=runtime,runtime_imported_files=sorted(loaded_after),checks=checks,camera_basis_U_V_depth=basis.tolist(),
        global_maxima=[c['summary']for c in cases],first_column_callout_layout=first_label_layout,all_faces_used=True,common_color_scales=True,all_global_IP_peaks_retained=True,FEA_started=False,
        all_axes_common_mm=True,display_only_zoom_XY_mm=zoom,geometry_modified=False,stress_convergence_established=False,strength_allowable=None,h2_qualified_under_distinct_serialized_reference=True,original_run_h2_qualified=False,original_generated_volume_refusal_preserved=True,
        wall_seconds=time.monotonic()-started,CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,cwd=os.getcwd(),outputs_sha256={p.name:sha(p)for p in sorted(output.iterdir())}))

if __name__=='__main__':
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150s actual four-case field figure budget')))
    signal.setitimer(signal.ITIMER_REAL,150);resource.setrlimit(resource.RLIMIT_CPU,(140,141))
    mode,plan,expected=sys.argv[1:4]
    if mode=='preflight':
        p,rows=verify(plan,expected);print(json.dumps(dict(status='closed_case_bindings_checked_no_arrays_or_render',launch_ready=p['launch_ready'],cases=[r['case']for r in rows],pins=len(p['files_sha256'])),sort_keys=True))
    elif mode=='render':os.chdir('/');render(plan,expected,sys.argv[4])
    else:raise SystemExit('usage: figure.py preflight PLAN SHA | render ARMED_PLAN SHA FRESH_OUTPUT')
