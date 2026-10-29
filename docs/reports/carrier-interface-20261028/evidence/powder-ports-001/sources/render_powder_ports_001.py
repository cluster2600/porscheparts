"""Render actual ported mesh sections and the constructed air-route geometry."""
import hashlib,json
from pathlib import Path
import numpy as np
import manifold3d as mf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch,Patch,Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
w=Path('work/carrier-interface-20261028');out=w/'powder-port-figures-001';assert not out.exists();out.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();report_path=w/'ported-qualification-001/assessment.json';report=json.loads(report_path.read_text());assert report['status']=='ported_digital_geometry_independently_checked';inputs={str(report_path):sha(report_path)}
def load(p):
 inputs[str(p)]=sha(p);z=np.load(p);return mf.Manifold(mf.Mesh64(z['vertices'],z['triangles']))
body=load(w/'ported-seams-002/candidate.npz');before=load(w/'full-reconstructed-p10-001/candidate.npz');assert sha(w/'ported-seams-002/candidate.npz')==report['candidate_sha256'];bg='#f4f1e9';dark='#203b3b';green='#286c68';blue='#4b79b2';orange='#d18442';observations=[]
def section_path(section):
 paths=[];area=0
 for polygon in section.to_polygons():
  p=np.asarray(polygon);area+=.5*float(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)));paths.append(PlotPath(np.vstack([p,p[0]]),[PlotPath.MOVETO]+[PlotPath.LINETO]*(len(p)-1)+[PlotPath.CLOSEPOLY]))
 assert paths and abs(area-section.area())/section.area()<1e-9
 return PlotPath.make_compound_path(*paths)
fig,axes=plt.subplots(2,1,figsize=(13,8),gridspec_kw={'height_ratios':[1,2]},layout='constrained',facecolor=bg)
for ax,trans,height,xlim,ylim,title in [(axes[0],None,0,(-302,302),(-40,40),'Complete carrier / XY section at Z = 0 mm'),(axes[1],[[0,1,0,0],[0,0,1,0],[1,0,0,0]],75.75,(22,40),(-10,12),'Region 1 / YZ section at X = 75.75 mm')]:
 current=body if trans is None else body.transform(trans);previous=before if trans is None else before.transform(trans);cs=current.slice(height);removed=previous.slice(height)-cs;ax.set_facecolor(bg);ax.add_patch(PathPatch(section_path(cs),facecolor=green,edgecolor=dark,lw=.4));ax.add_patch(PathPatch(section_path(removed),facecolor=blue,edgecolor=blue,lw=.2));ax.set(xlim=xlim,ylim=ylim,xlabel='X [mm]'if trans is None else'Y [mm]',ylabel='Y [mm]'if trans is None else'Z [mm]');ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title(title,loc='left',color=dark,fontsize=12);observations.append(dict(title=title,plane=height,retained_area_mm2=cs.area(),newly_removed_area_mm2=removed.area()))
axes[0].add_patch(Rectangle((66,22),18,16,fill=False,ec=blue,ls='--',lw=1));axes[1].legend(handles=[Patch(fc=green,label='Retained titanium'),Patch(fc=blue,label='Newly removed material / escape route'),Patch(fc=bg,ec='#888',label='Existing air or section background')],loc='upper left',frameon=False,fontsize=9)
fig.suptitle(f"993 CARRIER / EIGHT OPEN ROUTES / {report['nominal_mass_kg']:.6f} kg",fontsize=17,fontweight='bold',color=dark);fig.supxlabel('Sections of the actual exported mesh / no display simplification\nOne connected material shell; zero closed internal void shells. Complete-part mechanics and internal powder clearance remain pending.',fontsize=9,color=dark);fig.savefig(out/'ported-carrier-sections.png',dpi=180);plt.close(fig)
fig=plt.figure(figsize=(12,6),layout='constrained',facecolor=bg);routes=json.loads((w/'powder-port-routing-003/assessment.json').read_text())['selected'];inputs[str(w/'powder-port-routing-003/assessment.json')]=sha(w/'powder-port-routing-003/assessment.json');display=[]
for panel,rank in enumerate([0,3]):
 ax=fig.add_subplot(1,2,panel+1,projection='3d',facecolor=bg);all_points=[]
 for sign,color in [('positive',orange),('negative',green)]:
  p=w/f'meshlib-seed-p10-r{rank}-h0125-004/{sign}.npz';inputs[str(p)]=sha(p);z=np.load(p);points=z['vertices'];tri=points[z['triangles']];ax.add_collection3d(Poly3DCollection(tri,facecolor=color,edgecolor='none',alpha=.34,rasterized=True));all_points.append(points)
 for route in [r for r in routes if r['rank']==rank]:
  p=w/f"ported-carrier-001/tool-{route['network']}.npz";inputs[str(p)]=sha(p);z=np.load(p);points=z['vertices'];ax.add_collection3d(Poly3DCollection(points[z['triangles']],facecolor=blue,edgecolor='none',alpha=.68,rasterized=True));all_points.append(points);ax.plot(*np.array([route['start_mm'],route['end_mm']]).T,color=dark,lw=.7,ls='--')
 points=np.vstack(all_points);centre=(points.min(0)+points.max(0))/2;radius=max(np.ptp(points,axis=0))*.53;ax.set(xlim=(centre[0]-radius,centre[0]+radius),ylim=(centre[1]-radius,centre[1]+radius),zlim=(centre[2]-radius,centre[2]+radius));ax.set_box_aspect((1,1,1),zoom=1.4);ax.view_init(27,-55 if rank==0 else-125);ax.set_axis_off();ax.set_title(f'Region {rank+1} / two networks and two escape tools',loc='left',color=dark,fontsize=11);display.append(dict(rank=rank,triangles_rendered=sum(len(np.load(w/f'meshlib-seed-p10-r{rank}-h0125-004/{s}.npz')['triangles'])for s in ['positive','negative'])+760))
fig.legend(handles=[Patch(fc=orange,alpha=.5,label='Air network A'),Patch(fc=green,alpha=.5,label='Air network B'),Patch(fc=blue,alpha=.7,label='Constructed tapered port tools')],loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.5,.09),fontsize=9);fig.suptitle('POWDER ROUTES / ACTUAL CONSTRUCTION GEOMETRY',fontsize=16,fontweight='bold',color=dark);fig.supxlabel('Titanium hidden to expose the air geometry / all mesh triangles retained\nNominal Ø1.5 mm inlet, flare completed inside the parent body, nominal Ø3.0 mm exit shaft.\nThese views show route construction; they do not establish complete internal powder drainability.',fontsize=9,color=dark);fig.savefig(out/'powder-port-geometry.png',dpi=180);plt.close(fig)
(out/'figure-provenance.json').write_text(json.dumps(dict(input_sha256=inputs,source_sha256=sha(Path(__file__)),figures_sha256={p.name:sha(p)for p in out.glob('*.png')},section_observations=observations,air_views=display,manufacturing_authorized=False),indent=2)+'\n')
