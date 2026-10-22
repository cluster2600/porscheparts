"""Inspect the actual worst original analysis facet and its bounded repaired neighbourhood."""
import json,signal
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
import numpy as np
import trimesh
from run_reconstruction import sha

signal.alarm(300)
root=Path.cwd();p=root/'work/935-surface-facet-repair-20261022';old=p/'diagnostic-inputs/reference.off';accepted=p/'accepted-005';proof=json.loads((accepted/'assessment.json').read_text())
assert sha(old)==proof['reference_OFF_sha256'] and sha(accepted/'candidate.npz')==proof['output_sha256']['candidate.npz'] and proof['complete_surface_bound_established']
reference=trimesh.load_mesh(old,process=False)
with np.load(accepted/'candidate.npz') as z:new_v=z['vertices'].astype(float);new_f=z['faces'].astype(np.int64)
surfaces=[(np.asarray(reference.vertices),np.asarray(reference.faces)),(new_v,new_f)];values=[]
for v,f in surfaces:
    t=v[f];normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);norm=np.linalg.norm(normal,axis=1);edge=np.linalg.norm(t[:,[1,2,0]]-t,axis=2);q=2*np.sqrt(3)*norm/(edge**2).sum(axis=1);values.append((t,normal,norm,edge,q))
assert [int((x[4]<.05).sum()) for x in values]==[189,46]
worst=int(values[0][4].argmin());triangle=values[0][0][worst];centre=triangle.mean(axis=0);pairs=[(0,1),(1,2),(2,0)];a,b=max(pairs,key=lambda pair:np.linalg.norm(triangle[pair[1]]-triangle[pair[0]]));e1=triangle[b]-triangle[a];e1/=np.linalg.norm(e1);normal=values[0][1][worst]/values[0][2][worst];e2=np.cross(normal,e1);basis=np.column_stack([e1,e2]);radius=float(np.linalg.norm(triangle[b]-triangle[a])*1.4);assert radius>0
fig,axes=plt.subplots(1,2,figsize=(14,8));fig.subplots_adjust(left=.065,right=.985,top=.80,bottom=.20,wspace=.18);local=[]
short_a,short_b=min(pairs,key=lambda pair:np.linalg.norm(triangle[pair[1]]-triangle[pair[0]]));zoom_centre=((triangle[short_a]+triangle[short_b])/2-centre)@basis;zoom_radius=float(np.linalg.norm(triangle[short_b]-triangle[short_a])*5)
for ax,(v,f),(t,n,norm,edge,q),title in zip(axes,surfaces,values,['Before: retained analysis reference','After: bounded local repair']):
    centroids=t.mean(axis=1)-centre;mask=(np.linalg.norm(centroids,axis=1)<radius)&(np.abs(centroids@normal)<radius/2)&((n@normal)/norm>.5);assert mask.any()
    projected=(t[mask]-centre)@basis;colors=np.where((q[mask]<.05)[:,None],np.array([[.83,.22,.22,1]]),np.array([[.84,.89,.92,1]]));ax.add_collection(PolyCollection(projected,facecolors=colors,edgecolors=['#d43838' if value<.05 else '#41586a' for value in q[mask]],linewidths=.6));ax.scatter([0],[0],marker='+',s=70,color='#151d29');ax.set(xlim=(-radius,radius),ylim=(-radius,radius),aspect='equal',xlabel='local tangent x [mm, assumed scale]',ylabel='local tangent y [mm, assumed scale]');count=int((q[mask]<.05).sum());ax.set_title(title+'\n%d poor faces in this clipped projection'%count);ax.grid(alpha=.12);local.append({'shown_faces':int(mask.sum()),'shown_poor_faces':count})
    mini=ax.inset_axes([.045,.06,.36,.31]);zoom=(projected-zoom_centre)*1000;mini.add_collection(PolyCollection(zoom,facecolors=colors,edgecolors=['#d43838' if value<.05 else '#41586a' for value in q[mask]],linewidths=.7));uv=zoom.reshape(-1,2);near=np.max(np.abs(uv),axis=1)<zoom_radius*1200;mini.scatter(uv[near,0],uv[near,1],s=12,color='#222222');mini.set(xlim=(-zoom_radius*1000,zoom_radius*1000),ylim=(-zoom_radius*1000,zoom_radius*1000),aspect='equal');mini.set_title('Short-edge zoom [µm, assumed]',fontsize=8);mini.tick_params(labelsize=7);mini.grid(alpha=.15)

axes[1].legend(handles=[Patch(facecolor='#d43838',label='quality < 0.05'),Patch(facecolor='#d6e3eb',label='quality ≥ 0.05')],loc='upper right')
fig.suptitle('935 rotor: repair the analysis tessellation while preserving the surface bound\nGlobal poor triangles: 189 → 46; topology and untouched regions retained',fontsize=15)
fig.text(.5,.01,'Local tangent projection, not a datum or a flow/stress field.\nComplete bidirectional checks retain the 0.0225 source-unit bound and separate 0.0025 numeric reserve.\nScale, CFD acceptance and manufacturing remain unqualified.',ha='center',fontsize=10)
image=p/'935-local-facet-repair-002.png';assert not image.exists();fig.savefig(image,dpi=150);plt.close(fig)
r={'source_sha256':sha(__file__),'image_sha256':sha(image),'accepted_assessment_sha256':sha(accepted/'assessment.json'),'reference_worst_face_zero_based':worst,'display_kind':'actual surface triangles projected into an inspection-only tangent plane','clipped_patch':local,'before_global_poor_faces':189,'after_global_poor_faces':46,'original_minimum_quality':float(values[0][4].min()),'candidate_minimum_quality':float(values[1][4].min()),'original_minimum_edge_native_units':float(values[0][3].min()),'candidate_minimum_edge_native_units':float(values[1][3].min()),'scale_verified':False,'CFD_accepted':False,'manufacturing_authorized':False}
with (p/'visual-receipt-002.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r),flush=True)
